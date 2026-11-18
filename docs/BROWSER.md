# Browser initiative: brow.sh + Arachnidium

**Update 2026-11-18 (v1.43.0): the web front is dropped. The browser is SSH
only.** browsh hard-codes Marionette `2828` and refuses to start beside
another headless Firefox, so one pod runs one browsh. The owner chose the
TUI. **2026-11-19 (v1.44.0): Arachnidium is removed too** (browsh already
sends only text frames; the proxy only degraded pages). Sections below about Arachnidium, `browser.0xbf.ch`, `text.browser.0xbf.ch`, port
`4333` and the HTTP server are history. Live state: AGENTS.md (browser).

Status: implemented 2026-11-18. Both images are in-tree
under `images/` (no separate repos): `publish-manifests.yaml` builds and
pushes them with the release tag, before the OCI artifact. Smoke-tested
locally - both web fronts answer through the full chain (the first fetch
needs a warm Firefox and was slow only under this Mac's QEMU emulation).
Left to ship: the router forward, tag infra.

Facts verified against upstream sources and the browsh `raw_text_server.go`
source, 2026-11-18.

## Goal

One browser pod plus one new ssh-mux pod, all upstream traffic squeezed
through Arachnidium:

1. **Web, public, the upstream-documented browsh web front**:
   `https://browser.0xbf.ch/<url>` (HTML mode) and
   `https://text.browser.0xbf.ch/<url>` (plain text mode). Page in, a few
   KB of light text out. No login, no ttyd, no xterm — this is exactly how
   browsh's own `html.brow.sh` / `text.brow.sh` instances work.
2. **SSH, personal, the interactive TUI through the mux**:
   `ssh -p 2222 browser@0xbf.ch` opens the real browsh TUI — links, tabs,
   scrolling, mouse, forms, even video as text frames. Only text frames
   cross the WAN link.

## The port map (decision made 2026-11-18)

SSH never transmits the hostname, so no service can route by the dialed
name. One port = one backend. The mux routes by username instead — the
`git@github.com` model:

| Where              | Port                                | Serves       | Use                                                                                                              |
| ------------------ | ----------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------- |
| WAN 22             | entrypoint 22, hostPort rbpi        | forgejo sshd | `ssh://git@git.0xbf.ch/owner/repo.git` — the clean 22, no port suffix                                            |
| WAN 2222           | entrypoint 2222, hostPort rbpi      | sshmux       | `ssh -p 2222 browser@0xbf.ch` → browsh; any other username → apex TUI (`ssh -p 2222 0xbf.ch`, `someone@…` alike) |
| LAN + tailnet only | entrypoint 2223, no hostPort, LB IP | devil VM     | internal only. Moves from 2222 to the freed 2223                                                                 |

Rules the mux encodes:

- `browser` → inter-pod ssh into the browser pod (owner key, forced
  `browser-session`).
- Every other username → chained to apex-tui, today's any-username
  behavior. Default someone stays apex.
- Devil is and stays internal only. Not a mux name.
- New SSH TUI services in the future = one new mux username. No new WAN
  port, listener, or router forward — the mux is the one multiplexer.
- Apex's reinforced port is now 2222 (public command becomes
  `ssh -p 2222 0xbf.ch`). Apex repo README copy changes at rollout.

Two consequences accepted with this layout:

- WAN `2222` stops being reserved for the dev box (the old devil note).
- Renumbered internal devil SSH (2222 → 2223): LAN/tailnet users change
  one keystroke. Devil never appears on the WAN.

## Mux authentication

The mux must authenticate before it can dispatch by username. Two
populations ride it:

- `browser`: owner key only (`browser` user, no password). Nothing else
  gets the browsing proxy.
- Everyone else, bound for apex: apex is public today and stays public.
  sshd cannot authenticate nobody, so the apex path takes the empty
  password: `PermitEmptyPasswords` limited to non-`browser` users. A
  stranger types `ssh -p 2222 0xbf.ch`, presses Enter at the password
  prompt, and is in the portfolio. The owner never sees the prompt
  (pubkey wins first).

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
      (`Allow: /$` only), and a healthy response for probe user agents.
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
   │ ssh -p 2222 (text frames)                               │ https://(text.)browser.0xbf.ch/<url>
   ▼                                                        ▼
router WAN 2222 → rbpi (new forward)           Traefik websecure (LE wildcard)
   ▼                                                        │
Gateway entrypoint 2222, hostPort rbpi                       ▼
   ▼                                            Service browser-web :4333
ONE TCPRoute → Service sshmux :22                          │
   ▼                                                        ▼
sshmux pod (sshd, rbpi)                        browsh --http-server-mode
   │  user: browser → mux key                 (shared Firefox, HTML/PLAIN)
   │  any other user → apex-tui                              │
   │ browser ──────────────────────────────────────────┐    │
   ▼                                                    ▼    ▼
                       (inter-pod ssh, mux key)       browser-ssh sshd
   git: WAN 22 ── entrypoint 22 ── TCPRoute           │ ForceCommand
        → forgejo sshd (clean URLs, own keys)          ▼
                                          browser-session (fresh profile:
                                                       │ user.js proxy + CA)
   devil: entrypoint 2223, LB only ──► devil VM       ▼
   (internal only, unchanged otherwise)   browsh TUI + own Firefox
                                                       │
        every Firefox ──── user.js proxy ──► 127.0.0.1:8080 mitmproxy (Arachnidium)
                                                       │ bun-api :3000 (minify)
                                                       ▼
                                                 the public internet
```

Browser pod on rzbl, one network namespace, no PVC. HTTP mode uses one
shared Firefox; each mux session adds its own (per-session HOME profile,
Arachnidium CA imported, proxy prefs written).

## Image plan (in-tree, `images/browser`)

Tier-1 shape: the build context lives in the infra repo, `publish-manifests.yaml` builds and pushes the image with the release tag, and the Deployment pins that tag. Bump the pin in the release commit; `just release` refuses mismatches.

```
images/browser/
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

amd64 only (the browsh image bundles x64 Firefox; the pod is pinned to rzbl). sshmux is arm64 (rbpi).

## Infra plan

- `applications/browser/`, ns `browser`: namespace, deployment (tier-2
  Keel shape, pinned to rzbl, limits `2` cpu / `2.5Gi` for the HTTP
  Firefox plus 1-2 mux sessions), services `browser-web` `4333`
  and `browser-ssh` `22`, kustomization.
- HTTPRoute `browser.0xbf.ch` **and** `text.browser.0xbf.ch` (two
  hostnames, one route) on `websecure`. LE wildcard and ddns wildcard
  already cover both; no cert or DNS change.
- `applications/sshmux/`, ns `sshmux` (tiny openssh image, rbpi): the
  username router above; sops `sshmux-host-key.sops.yaml` plus the mux
  keys. ONE TCPRoute behind a new `muxssh` entrypoint `2222`,
  hostPort `2222` on rbpi.
- Listener surgery in the same tag (all one user-visible port map change):
    - `gitssh` moves `2223` → `22` (WAN 22 already forwards to rbpi 22 —
      no router change, the NAT rule stays), TCPRoute to forgejo sshd.
    - `apexssh` listener retires (apex rides the mux as the default user).
    - `devilssh` moves `2222` → `2223`, still LB-only, no hostPort.
    - new `muxssh` listener `2222` + hostPort.
- Owner router action: add WAN `2222` → `10.10.20.10`. Nothing else.
- Egress CiliumNetworkPolicy `browser-egress`: DNS (udp 53 to kube-dns)
  and tcp 80/443 out. Proxy serves web traffic and nothing else.
- Gatus `public` group: `browser.0xbf.ch/` (probe user agent gets the
  built-in healthy response; one check per hostname so both HTML and PLAIN
  modes are covered), plus TCP checks for `sshmux` and git on 22.
- Atlas + AGENTS.md: SERVICE rows (browser, sshmux), HOSTS entries, tree
  lines, component notes, tier list, DONE lines. AGENTS edits needed:
  apex (`ssh -p 2222 0xbf.ch`), forgejo (`ssh://git@git.0xbf.ch/...`
  without port), devil (2223, WAN-2222 note dead), the port list in the
  traefik/gateway notes, apex repo README at the next apex release.

## Security and abuse

- Web front: browsh's own rate limit plus a Traefik rate-limit
  middleware; blocked-domains; the Arachnidium blocklist drops
  ads/trackers before Firefox sees them; responses cached 600 s.
  One shared Firefox renders public fetches — worst case is bandwidth,
  capped by limits.
- Mux: `browser` is owner-key-only; the browsing proxy is personal.
  The apex path's empty password keeps the public portfolio reachable
  but grants nothing else (chained straight into apex-tui, which has no
  exec, no SFTP, no shell).
- Browser pod sshd: mux key only, no forwarding anywhere,
  `MaxSessions 2`, per-session 12 h timeout.

## Rollout checklist

Done (2026-11-18): manifest work; local image smoke tests — the full chain
answers on both web fronts (`just image` rebuilds; `docker run -p 4333:4333
-p 2222:22 ghcr.io/bfeitknecht/browser:dev` re-verifies). Remaining:

1. Owner: add the router forward WAN `2222` → `10.10.20.10` (any time; it
   stays inert until the tag lands). Optionally drop the dead `2223` rule.
2. Bump the two image pins to the release tag in the release commit (the
   release recipe refuses a mismatch). Currently pinned: `v1.42.0`.
3. `just release X.Y.Z`: gates, then CI builds both images and pushes them
   before the OCI artifact. Gatus goes green.
4. Cut over and verify: `ssh://git@git.0xbf.ch/owner/repo.git` clone
   (clean 22), `ssh -p 2222 0xbf.ch` (apex), `ssh -p 2222 browser@0xbf.ch`
   (browsh, from LTE — record data use), devil.internal on 2223.
   One host-key notice: the sshmux key for port 2222, one known_hosts entry.

## Open decisions

- Arachnidium `IMAGE_QUALITY`: default 20 is aggressive; 50-60 looks
  better. Runtime config in `defaults.json`, no rebuild.
- Empty-password apex path vs owner-key-only mux (apex SSH portfolio
  becomes owner-only). The plan keeps apex public; flip by removing
  `PermitEmptyPasswords` if unwanted.
- Later: MoSH for roaming LTE on the mux front; 443 SNI (`TLSRoute`)
  stays parked — with the mux, no new inbound port is in sight anyway.
