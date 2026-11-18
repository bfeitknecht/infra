# Browser initiative: brow.sh + Arachnidium

Status: plan, not built. Facts verified against upstream sources 2026-11-18.
Nothing here is deployed yet.

## Goal

A real, interactive browser that works on a metered or bad connection, from
any device, with nothing installed. Two fronts on one pod:

1. `ssh -p 2224 browser.0xbf.ch` (name any user) opens the browsh TUI in the
   terminal. Interactive: click links, scroll, tabs, history, mouse, forms.
   Only text frames travel the WAN link. SSH compresses them further.
2. `https://browser.0xbf.ch` opens the same TUI in a web page (ttyd,
   xterm.js). Interactive in a browser tab. The devil `ghostty-web` pattern,
   without the VM.

All upstream traffic goes through Arachnidium, so even the Firefox behind
browsh downloads less. Rejected: browsh `--http-server-mode`. That mode only
answers one-shot fetches; it is not a browser.

## Findings

### browsh v1.8.3 (browsh-org/browsh, LGPL-2.1)

- A real browser: a Go TUI fronting headless Firefox plus a webextension
  injected over a remote debugging connection. Pages render as text via the
  half-block trick; JS, CSS and HTML5 all work.
- Frame data is small; upstream claims a heavy page becomes a few KB of text.
  The TTY client is the mature one (the HTTP _fetch_ mode is the crippled one;
  dropped).
- Keys and mouse work; TUI can watch video as text frames at a set rate
  (`small_pixel_frame_rate`).
- One browsh process = one Firefox instance. This drives the session limits
  below.
- Base `browsh/browsh` image is amd64 only, with Firefox bundled (~230 MB).
  So the pod lands on rzbl, not rbpi.
- Browsh also speaks MoSH ("use MoSH to further reduce bandwidth and survive
  roaming"). SSH only for v1; MoSH needs a UDP range and could come later.

### Arachnidium (p2r3/Arachnidium, MIT)

- A mitmproxy addon optimizing every HTTP(S) response: images to WebP/AVIF
  (quality in `defaults.json`, default 20), html/css/js/svg minification,
  recompression at max levels (brotli, gzip, zstd), redirect and error
  bodies emptied, speculative prefetch of minified links, hagezi ad
  blocklist.
- Shape: python (uv) + a local Bun service (`bun-api`, `localhost:3000`)
  that does the actual minification. The addon posts each response to it.
- Upstream ships x64 portable builds only and hardcodes
  `--mode wireguard:wg-keys.json` (the phone-VPN use case), plus an
  `api.ipify.org` call and a `wg-keys.json` read at load. Patches needed.
- The author does not intend to maintain it long term. Pin the commit,
  vendor the patches, expect ownership. MIT.

## Architecture

```
            phone / laptop on LTE
             │                └──────────────┐
             │ ssh -p 2224 (text frames)    │ https (websocket, text frames)
             ▼                              ▼
   router: WAN 2224 ──► rbpi        Traefik (browser.0xbf.ch, websecure)
             │ hostPort 2224                  │
             ▼                                │
   Gateway listener `browssh`                 │
             │ TCPRoute                       │
             ▼                                ▼
   Service browser-ssh               Service browser-web :7681
             │                                │
             ▼                                ▼
        sshd (pod)                    ttyd (pod, xterm.js page)
             │ ForceCommand                  │ one process per client
             ▼                                ▼
        browser-session ◄──── both spawn ────┘
             │  fresh Firefox profile: proxy user.js + mitm CA import
             ▼
        browsh TUI ──► headless Firefox ──► 127.0.0.1:8080
                                              mitmproxy (Arachnidium addon)
                                                │ bun-api :3000 (minify)
                                                ▼
                                            the public internet
```

One pod, one network namespace, rzbl. Each session (SSH or web) gets its own
browsh and its own Firefox: a profile-in-use error forces fresh profiles,
so `browser-session` makes one per session anyway. No PVC; everything is
ephemeral.

## Image plan (own repo, `bfeitknecht/browser`)

House pattern: the repo holds the container, infra holds the Deployment.

```
browser/
├── Dockerfile        FROM browsh/browsh:<pinned digest>
│                     + python 3.13 + uv (Arachnidium deps from a pinned commit)
│                     + bun-api runtime baked in
│                     + openssh-server, libnss3-tools (certutil), ttyd
├── patches/          Arachnidium patches applied at build
├── entrypoint.sh     start bun-api; mitmdump (regular mode, 127.0.0.1:8080);
│                     wait for mitm CA; then sshd and ttyd
├── browser-session   per-session wrapper: mktemp HOME, user.js proxy prefs,
│                     certutil CA import into the fresh profile, exec browsh
│                     under `timeout 12h`
├── sshd_config       ForceCommand browser-session, no forwarding of any kind,
│                     MaxSessions 3
├── defaults.json     Arachnidium: ENABLE_GUI false, image quality
└── config.toml       browsh config (columns, frame rate)
```

Arachnidium patches (kept as `.patch` files against the pinned commit):

1. Run `mitmdump -s addon.py --mode regular@127.0.0.1:8080` instead of
   `main.py` (skips the wireguard mode and the tkinter GUI).
2. In `load()`: drop the WireGuard generation (ipify call, `wg-keys.json`);
   bake the ad blocklist into the image instead of fetching jsdelivr each
   start.
3. `defaults.json`: `ENABLE_GUI: false`.

CI: the reusable `publish-image.yaml`, same as apex/glob/exhib. amd64 only
for v1 (the browsh image bundles x64 Firefox). arm64 means building browsh
itself; separate task, not a blocker.

## Infra plan (`applications/browser/`, ns `browser`)

- `namespace.yaml`, `deployment.yaml`, `service.yaml` (browser-web `7681`,
  browser-ssh `22`), `httproute.yaml`, `tcproute.yaml`, `kustomization.yaml`,
  `browser-ssh-host-key.sops.yaml` (stable host keys, apex `apex-ssh-host-key`
  pattern).
- Deployment: tier-2 shape (image `ghcr.io/bfeitknecht/browser:latest`,
  `imagePullPolicy: Always`, Keel). Node pinned to rzbl (amd64). Sizing for
  1-3 sessions: limits `2` cpu, `2.5Gi` memory, single replica.
  `readOnlyRootFilesystem`; `emptyDir` for `/tmp`, sshd host keys are
  replaced by the sops-mounted ones.
- SSH: new gateway listener `browssh`, port `2224`, `hostPort: 2224` on
  rbpi (apex `apexssh` pattern), TCPRoute to `browser-ssh`. Owner forwards
  WAN `2224` to `10.10.20.10` on the Zyxel (_router change, like 2223_).
  Port audit: 22 apex, 2222 WAN-reserved dev box, 2223 git, so 2224 is free.
- Web: HTTPRoute `browser.0xbf.ch` on `websecure` (LE wildcard covers it,
  ddns wildcard covers DNS; no cert change). Websockets upgrade through the
  Gateway like devil's ghostty-web ttyd route.
- Egress CiliumNetworkPolicy `browser-egress`: DNS (udp 53 to kube-dns) and
  tcp 80/443 out. The proxy must offer web traffic and nothing else.
- Gatus: `public` group check on `browser.0xbf.ch`. SSH checks probe the
  web side only (a TCP probe against a WAN port from inside is not
  meaningful).
- Atlas + AGENTS.md: SERVICE row, HOSTS entry (both fronts), tree line,
  component note, tier list, DONE line at rollout.

## Security and abuse

- Threat: an open browsing proxy. Cost: bandwidth upstream. Benefit: a
  useful tool. Text frames on the client side stay tiny; the WAN bill is
  the pages Firefox fetches, which Arachnidium already shrinks.
- Caps: pod limits, single replica, sshd `MaxSessions 3`, ttyd `-m 3`,
  per-session `timeout 12h`, no SSH forwarding of any kind. One Firefox per
  session bounds the memory.
- Auth, two open decisions:
    - SSH route: apex-tui style open (any username, host key only) or require
      a client pubkey. Recommendation: require the owner key. This route is a
      live proxy into arbitrary sites, not a static portfolio; open SSH makes
      the home IP a free anonymizer for anyone who scans 2224.
    - Web route: open with ttyd credentials (`-c user:pass`) or authentik
      forward auth on the public hostname. Recommendation: authentik; the
      pattern exists (public client, forward auth).
- The Arachnidium blocklist drops ad/tracker domains before Firefox sees
  them.

## Rollout checklist

1. Build the browser repo image; smoke test locally:
   `just image && docker run -p 7681:7681 -p 2224:22 ghcr.io/bfeitknecht/browser:dev`,
   then `ssh -p 2224 localhost` and open `http://localhost:7681`.
   Confirm both fronts browse; measure a heavy page against direct fetch.
2. Owner: forward WAN `2224` to `10.10.20.10` on the Zyxel.
3. Infra changes in one tag: `applications/browser/`, listener, routes,
   gatus, atlas, AGENTS.md.
4. `just check && just fmt --check`, then `just release X.Y.Z`.
5. Watch Keel pick the image up; watch Gatus go green.
6. Test from LTE: `ssh -p 2224 browser.0xbf.ch`, browse a media-heavy site,
   record the data used. Compare a second run with MoSH later.

## Open decisions

- SSH auth: open (apex style) vs client pubkey (recommended).
- Web auth: ttyd credentials vs authentik forward auth (recommended).
- Arachnidium `IMAGE_QUALITY`: default 20 is aggressive; 50-60 looks better.
  Runtime config in `defaults.json`, no rebuild.
- Later: MoSH endpoint for roaming LTE; arm64 build for rbpi redundancy.
