# Browser initiative: brow.sh + Arachnidium at `browser.0xbf.ch`

Status: plan, not built. Every fact below is verified against upstream sources
(2026-11-18). Nothing here is deployed yet.

## Goal

A public route `browser.0xbf.ch`. A visitor gives it a URL. The service
fetches that page, squeezes it through a data-optimizing proxy, and returns an
extremely lightweight text rendering. Use it on a metered or slow connection,
from any device, with no client install.

## Findings

### browsh v1.8.3 (browsh-org/browsh, LGPL-2.1)

- Three parts: a Go CLI (`browsh`), headless Firefox, and a webextension
  injected over a remote debugging connection. Firefox does the real browsing.
- `--http-server-mode` turns browsh into an HTTP service. Config block
  `[http-server] port = 4333, bind = "0.0.0.0"` in
  `${XDG_CONFIG_HOME}/browsh/config.toml`. One request = one page fetch
  through Firefox = one lightweight HTML/text response. Upstream claims
  ~3 MB pages become ~15 KB, 100+ requests become 2.
- The HTTP mode is **not interactive**: no clicks, no scrolling, no frames.
  The interactive TTY client would need ttyd (devil pattern); out of scope for
  v1.
- Built-in abuse controls in the same config block: `rate-limit`
  (ulule/limiter syntax, e.g. `"10-M"` = 10 requests per minute per client),
  `blocked-domains`, `blocked-user-agents` (both regex lists), plus
  `--startup-url` and `--time-limit`.
- Base image `browsh/browsh:latest` is **amd64 only**. rbpi is out; this lands
  on rzbl. Image carries Firefox; total ~230 MB before Arachnidium.
- Maintenance: last release Jan 2026, slow-moving. Pin the image digest.

### Arachnidium (p2r3/Arachnidium, MIT)

- A mitmproxy addon that optimizes every HTTP(S) response in flight:
  images to WebP or AVIF (quality from `defaults.json`, default 20),
  html/css/js/svg minification, response recompression with
  brotli/gzip/zstd at max levels, redirect and error bodies emptied.
- Also: a speculative cache (pre-fetches links found in minified HTML),
  an ad blocklist (hagezi `pro-onlydomains`, downloaded at start), and
  saved-bytes counters.
- Shape: python (uv, `main.py` + `addon.py`) plus a local Bun service
  (`bun-api`, listens on `localhost:3000`) that does the actual
  html/css/js/svg minification. The addon posts to it per response.
- Upstream ships x64 portable builds only, and `main.py` hardcodes
  `--mode wireguard:wg-keys.json` (the desktop use case: a phone VPN).
  For us it must run with `--mode regular` (a plain HTTP proxy) patched at
  startup. Mitmproxy supports regular proxy mode fully; the addon code is
  mode-agnostic (`request`/`response` hooks work the same).
- `addon.py load()` also generates a WireGuard config: it calls `api.ipify.org`
  and reads `wg-keys.json`. That must be patched out or stubbed.
- Maintenance: the author states he will not maintain it long term. Pin a
  commit, vendor patches, expect to take it over. MIT licensed.

### Integration

Browsh's Firefox is pointed at the Arachnidium mitmproxy as its HTTP(S)
upstream proxy (Firefox `user.js` proxy prefs in browsh's profile).
The mitmproxy CA is imported into the same profile's NSS cert store
(`certutil`, libnss3-tools) so HTTPS interception succeeds. Then every page
browsh renders has already been compressed. The two data-saving tricks
compound: Arachnidium cuts what Firefox downloads, browsh cuts what the
visitor downloads.

## Architecture

```
visitor ──HTTPS──>Traefik (browser.0xbf.ch, websecure)
                     │
                     ▼
                Service browser :4333
                     │
                     ▼
        browsh --http-server-mode ── GET /https://example.com
                     │
                     ▼
        headless Firefox ── via proxy (user.js) ──> mitmproxy (Arachnidium addon)
                                                        │  bun-api :3000 (minify)
                                                        ▼
                                                   the public internet
```

One pod, one network namespace, one node (rzbl). No PVC: profile and
caches are ephemeral (`emptyDir`). Every pod restart is a clean profile.

## Image plan (own repo, `bfeitknecht/browser`)

House pattern: the repo holds the container, infra holds the Deployment.

```
browser/
├── Dockerfile        FROM browsh/browsh:<pinned digest>
│                     + python 3.13, uv sync (Arachnidium deps, pinned commit)
│                     + bun-api deps baked in
│                     + libnss3-tools (certutil)
├── patches/          Arachnidium patches (see below), applied in build
├── entrypoint.sh     start bun-api, then mitmdump (regular mode, :8080),
│                     import CA into browsh profile, then browsh --http-server-mode
├── user.js.in        Firefox proxy prefs rendered at start (proxy 127.0.0.1:8080)
├── defaults.json     Arachnidium config: ENABLE_GUI false, quality, blocklist
└── config.toml       browsh config: http-server bind/port, rate-limit,
                      blocked-domains, footer/hints
```

Arachnidium patches (kept as `.patch` files against the pinned commit):

1. Run via `mitmdump -s addon.py --mode regular@127.0.0.1:8080` instead of
   `main.py` (skips the wireguard mode and the GUI).
2. In `load()`: drop the WireGuard config generation (ipify call,
   `wg-keys.json`) and cache the ad blocklist in the image (no jsdelivr fetch
   on every start).
3. `defaults.json`: `ENABLE_GUI: false` (headless; tkinter never starts).

CI: the reusable `publish-image.yaml` from infra, same as apex/glob/exhib.
Multi-arch: amd64 only for v1 (Firefox in the browsh image is x64). If arm64
is wanted later, browsh must be built from its Dockerfile for arm; tracked as
a separate task, not a blocker.

## Infra plan (`applications/browser/`, ns `browser`)

- `namespace.yaml`, `deployment.yaml`, `service.yaml` (port `4333`),
  `httproute.yaml`, `kustomization.yaml`.
- Deployment: tier-2 shape like apex: image
  `ghcr.io/bfeitknecht/browser:latest`, `imagePullPolicy: Always`,
  Keel annotations. Node pinned to rzbl (amd64, heavy Firefox).
  Limits: `cpu 2`, `memory 1.5Gi`. `readOnlyRootFilesystem` with
  `emptyDir` mounts for `/tmp` and the Firefox profile (mirrors glob).
- HTTPRoute: hostname `browser.0xbf.ch` on `websecure` (public; LE wildcard
  covers it, no cert change, ddns wildcard covers DNS).
- Egress CiliumNetworkPolicy `browser-egress`: allow DNS (udp 53 to
  kube-dns), and tcp 80/443 to the world. Nothing else. The proxy must not
  become a source for anything but web traffic.
- Traefik middleware: `rate-limit` (e.g. 10 req / minute / client IP) as a
  second layer under browsh's own limiter.
- Gatus: a `public` group check for `browser.0xbf.ch`.
- Atlas: new SERVICE row, HOSTS entry, DONE line at rollout; AGENTS.md gets
  the tree line, a component note, and the tier list mention.

## Security and abuse

- Threat: an open fetch-the-web proxy. Misuse vectors: bandwidth drain,
  fetching from our IP (masking), heavy compute per request.
- Layered caps: browsh `rate-limit`, Traefik rate-limit middleware, pod
  resource limits, single replica. Non-interactive HTTP mode removes the
  click-through surface (no links are followed except via explicit requests).
- Arachnidium's blocklist drops ad/tracker domains before Firefox sees them.
- Open decision (below): keep it unauthenticated (like browsh's own public
  instance, survives on rate limits) or put authentik forward auth in front.
  Recommendation: start public with rate limits; the route is easy to bolt
  behind forward auth later. It is a purpose hostname, so a later software
  swap keeps the URL.

## Rollout checklist

1. Build the `browser` repo image; smoke-test locally:
   `just image && docker run -p 4333:4333 ghcr.io/bfeitknecht/browser:dev`,
   then `curl "http://localhost:4333/https://example.com"`.
   Compare response size with and without the proxy hop for a heavy page.
2. Infra PR: `applications/browser/` + gatus + atlas + AGENTS in one change.
3. `just check && just fmt -lint`, then `just release X.Y.Z`.
4. Watch Keel pick up the image; watch the Gatus check go green.
5. Verify from LTE or a throttled connection; record the measured savings.

## Open decisions

- Public with rate limits (recommended) vs authentik forward auth on day one.
- Tier 2 Keel flow (recommended, house pattern) vs tier 1 pinned digest.
- Arachnidium quality setting: default 20 is aggressive; owners may prefer
  50-60 for a public service. Tunable in `defaults.json`, no image rebuild.
- Later: interactive TTY mode through ttyd (devil pattern) if the text-only
  fetch form is not enough.
