# Browser initiative: brow.sh + Arachnidium

Status: plan, not built. Facts verified against upstream sources and the
browsh `raw_text_server.go` source, 2026-11-18. Nothing here is deployed yet.

## Goal

One pod, two fronts, all squeezed through Arachnidium first:

1. **Web, public, the upstream-documented browsh web front**:
   `https://browser.0xbf.ch/<url>` (HTML mode) and
   `https://text.browser.0xbf.ch/<url>` (plain text mode). Page in, a few
   KB of light text out. No login, no ttyd, no xterm — this is exactly how
   browsh's own `html.brow.sh` / `text.brow.sh` instances work.
2. **SSH, personal, the interactive TUI**: `ssh browser@0xbf.ch` opens the
   real browsh TUI — click links, scroll, tabs, mouse, forms, even video as
   text frames. Only text frames cross the WAN link. It rides the EXISTING
   port 22 forward through a new sshd mux; no new WAN port, no new gateway
   listener, no router change.

All upstream traffic goes through the Arachnidium proxy in the pod, so the
Firefox behind browsh downloads less too.

## The SSH port question

SSH sends no hostname before the handshake: there is no SNI, so true
name-based demuxing of several SSH services on one port is impossible at
the protocol level. What IS possible, and what this plan uses:

- **One front sshd on port 22 routes by username** (the
  `git@github.com` model). The existing chain stays: router 22 → rbpi
  hostPort → `apexssh` listener → ONE TCPRoute, backend swapped from
  `apex-tui:2222` to the mux:
    - `ssh 0xbf.ch` (user `bf`, the ssh default) → apex TUI, exactly as today.
    - `ssh browser@0xbf.ch` → browsh TUI.
    - `ssh devil@0xbf.ch` → devil VM (later, mux key into the VM).
    - Any other username → apex TUI (today's any-username behavior).
- The mux authenticates the owner key once, then runs the target itself
  (per-user `ForceCommand`): for apex-tui the mux runs an ssh client
  (apex-ssh needs no key), for browser it holds a mux key authorized in the
  browser pod, bridging stdio to the client. One auth, one known_hosts
  entry for `0xbf.ch:22`, no double handshake.
- **Git cannot ride the mux.** Forgejo authenticates pushes by the END
  USER's key; a shared mux key would collapse everyone into one identity.
  Git keeps its own `2223` forward. This is the same reason GitHub does
  not sit behind such a mux.
- The strategic alternative, if the port zoo ever grows again: SNI
  demuxing over **443** (`TLSRoute` per `ssh.<name>.0xbf.ch`, ssh wrapped
  in TLS via `ProxyCommand openssl s_client`, stunnel sidecars to unwrap).
  That is the only true name-based WAN multiplexing; it costs a client
  alias and a TLS unwrap per service. Out of scope until a third or fourth
  TCP service wants in.

## Findings

### browsh v1.8.3 (browsh-org/browsh, LGPL-2.1)

- A real browser: Go TUI fronting headless Firefox plus a webextension
  injected over a remote debugging connection. The TTY client is the
  mature one: keyboard, mouse, tabs, realtime frames.
- `--http-server-mode` (source-verified, `raw_text_server.go`):
    - URL bar is the path: `GET https://host/https://example.com`; a
      `slashFix` wrapper keeps `//` intact.
    - Mode by host: a host containing `text.` serves PLAIN mode;
      `browser.0xbf.ch` gives HTML mode with live anchor links. A
      `X-Browsh-Raw-Mode: DOM` header dumps the DOM.
    - Built-ins: rate limit (ulule syntax, honours `X-Forwarded-For`),
      `blocked-domains` and `blocked-user-agents` regex lists, gzip,
      `Cache-Control: public, max-age=600`, render timeout, robots.txt
      (`Allow: /$` only), and a healthy-response for probe user agents.
    - Empty path serves a welcome page; the browsh upstream instances are
      literally `html.brow.sh` and `text.brow.sh`.
    - One shared Firefox instance serves all HTTP requests; each TTY client
      spawns its own.
- Base `browsh/browsh` image is amd64 only; the pod lands on rzbl.
- Browsh also speaks MoSH ("further reduce bandwidth, survive roaming").
  SSH first; MoSH is a later nice-to-have.

### Arachnidium (p2r3/Arachnidium, MIT)

- A mitmproxy addon optimizing every HTTP(S) response: images to WebP/AVIF
  (quality in `defaults.json`, default 20), html/css/js/svg minification,
  recompression at max levels, redirect and error bodies emptied,
  speculative prefetch of minified links, hagezi ad blocklist.
- Shape: python (uv) + a local Bun service (`bun-api`, `localhost:3000`)
  doing the actual minification.
- Upstream ships x64 portable builds only and hardcodes
  `--mode wireguard:wg-keys.json` (the phone-VPN use case), with an
  `api.ipify.org` call and a `wg-keys.json` read at load. Patches needed.
- The author does not intend to maintain it long term. Pin the commit,
  vendor the patches, expect ownership. MIT.

## Architecture

```
 phone / laptop
   │                        └──────────────────────────────┐
   │ ssh browser@0xbf.ch   (text frames)                    │ https://(text.)browser.0xbf.ch/<url>
   ▼                                                        ▼
router WAN 22 → rbpi (already forwarded)          Traefik websecure (LE wildcard)
   ▼                                                        │
Gateway `apexssh` listener, hostPort 22                       ▼
   ▼                                            Service browser-web :4333
ONE TCPRoute → Service sshmux :22                          │
   ▼                                                        ▼
ssh-mux (sshd, rbpi)                            browsh --http-server-mode
   │ per-user ForceCommand                     (shared Firefox, HTML/PLAIN)
   │  bf/* → apex-tui                                        │
   │  browser ─────────────────────────────────────────┐    │
   ▼                                                   ▼    ▼
                         (inter-pod ssh, mux key)   browser-ssh sshd
                                                       │ ForceCommand
                                                       ▼
                                           browser-session (fresh profile: user.js
                                                       │ proxy + CA import)
                                                       ▼
                                           browsh TUI + own Firefox
                                                       │
        every Firefox ──── user.js proxy ──► 127.0.0.1:8080 mitmproxy (Arachnidium)
                                                       │ bun-api :3000 (minify)
                                                       ▼
                                                 the public internet
```

Browser pod on rzbl, one network namespace, no PVC. HTTP mode uses one
shared Firefox; each SSH session adds its own (per-session HOME profile,
Arachnidium CA imported, proxy prefs written).

## Image plan (own repo, `bfeitknecht/browser`)

```
browser/
├── Dockerfile        FROM browsh/browsh:<pinned digest>
│                     + python 3.13 + uv (Arachnidium deps, pinned commit)
│                     + bun-api runtime baked in
│                     + openssh-server, libnss3-tools (certutil)
├── patches/          Arachnidium patches (below), applied at build
├── entrypoint.sh     bun-api, then mitmdump (regular, 127.0.0.1:8080),
│                     wait for the mitm CA, then sshd and browsh --http-server-mode
├── browser-session   per-session wrapper: mktemp HOME, user.js, certutil
│                     CA import, exec browsh under `timeout 12h`
├── sshd_config       mux key only, ForceCommand browser-session, no forwarding
├── defaults.json     Arachnidium: ENABLE_GUI false, image quality
└── config.toml       browsh: http-server bind/port, rate-limit,
                      blocked-domains, columns/rows, render timeout
```

Arachnidium patches (`.patch` files against the pinned commit):

1. Run `mitmdump -s addon.py --mode regular@127.0.0.1:8080` instead of
   `main.py` (skips wireguard mode and the tkinter GUI).
2. In `load()`: drop the WireGuard generation (ipify call,
   `wg-keys.json`); bake the ad blocklist into the image.
3. `defaults.json`: `ENABLE_GUI: false`.

CI: the reusable `publish-image.yaml`, as apex/glob/exhib. amd64 only for
v1 (the browsh image bundles x64 Firefox).

## Infra plan

- `applications/browser/`, ns `browser`: namespace, deployment (tier-2
  Keel shape, pinned to rzbl, limits `2` cpu / `2.5Gi` for the HTTP
  Firefox plus 1-2 TUI sessions), services `browser-web` `4333`
  and `browser-ssh` `22`, kustomization.
- HTTPRoute `browser.0xbf.ch` **and** `text.browser.0xbf.ch` (two
  hostnames, one route) on `websecure`. LE wildcard and ddns wildcard
  already cover both; no cert or DNS change.
- `applications/sshmux/`, ns `sshmux` (tiny openssh image, rbpi): port 22
  front, owner-key auth, sops `sshmux-host-key.sops.yaml` + mux keys.
  Users: `bf`/unknown → apex-tui (chain as today), `browser` → pod sshd.
  The ONE TCPRoute behind `apexssh` repoints to it; the router forward,
  listener and WAN port do not change. Note: the public host key for
  port 22 becomes the mux key — one known_hosts update, then apex's
  port-22 users never see a key change again.
- Egress CiliumNetworkPolicy `browser-egress`: DNS (udp 53 to kube-dns)
  and tcp 80/443 out. Proxy serves web traffic and nothing else.
- Gatus `public` group: `browser.0xbf.ch/` (probe user agent gets the
  built-in healthy response; assert host header not `text.` to probe the
  HTML mode path too), plus `sshmux` as a platform TCP check.
- Atlas + AGENTS.md: SERVICE rows (browser, sshmux), HOSTS entries, tree
  lines, component notes, tier list, DONE lines at rollout.

## Security and abuse

- Web front: browsh's own rate limit plus a Traefik rate-limit
  middleware; blocked-domains; the Arachnidium blocklist drops
  ads/trackers before Firefox sees them; responses cached 600 s.
  One shared Firefox renders public fetches — worst case is bandwidth,
  capped by limits.
- SSH front: owner key only, at the mux. Public low-bandwidth browsing
  happens on the web fronts; the interactive TUI is personal. An open
  TUI would make the home IP a free browsing anonymizer.
- SSH hardening at the pod sshd: mux key only, no forwarding anywhere,
  `MaxSessions 2`, per-session 12 h timeout.

## Rollout checklist

1. Browser repo image; smoke test locally:
   `just image && docker run -p 4333:4333 -p 22:22 ghcr.io/bfeitknecht/browser:dev`;
   `curl http://localhost:4333/https://example.com` (HTML),
   UA `GoogleHC` probe (healthy), ssh in and browse.
   Measure a heavy page: direct fetch vs through Arachnidium.
2. sshmux image/repo (or chart the smallest possible): test with a local
   key that `bf` chains to a local apex-tui stub and `browser` chains to
   the browser pod.
3. Infra changes in one tag: `applications/browser/`, `applications/sshmux/`,
   the ONE TCPRoute backend swap, gatus, atlas, AGENTS.md.
4. `just check && just fmt --check`, then `just release X.Y.Z`.
5. Keel picks the images up; Gatus goes green.
6. Owner: update known_hosts for `0xbf.ch` once (mux key). Test
   `ssh 0xbf.ch` (apex still), `ssh browser@0xbf.ch`,
   `https://browser.0xbf.ch/https://news.ycombinator.com`,
   same on `text.`. Record LTE data use for both fronts.

## Open decisions

- Mux auth: owner key only (recommended) vs apex-style open. Affects every
  port-22 user immediately — apex's any-username behavior only survives
  as "unknown user → apex".
- Arachnidium `IMAGE_QUALITY`: default 20 is aggressive; 50-60 looks
  better. Runtime config in `defaults.json`, no rebuild.
- Devil as a mux username (mux key into the VM) also retires the LAN-only
  `devilssh` listener someday; separate change.
- Later: MoSH on the web front? No — MoSH rides the SSH front, worth it
  for roaming LTE. Also later: the 443 SNI TLSRoute world if more TCP
  services arrive.
