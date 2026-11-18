# browser

Browsh + Arachnidium: a very low bandwidth browsing pod.

Two fronts:

- **Web (public):** `https://browser.0xbf.ch/<url>` returns a light HTML
  rendering; `https://text.browser.0xbf.ch/<url>` returns plain text. This
  is browsh's own `--http-server-mode` — the same server behind browsh's
  `html.brow.sh` / `text.brow.sh`.
- **SSH (personal):** port 22; the infra `sshmux` chains in here with
  `ssh -p 2222 browser@0xbf.ch`. One browsh TUI + one Firefox per session.

Every Firefox (the shared HTTP one and each session's own) sends all
traffic through the in-pod Arachnidium mitmproxy: images to WebP/AVIF,
html/css/js/svg minified, responses recompressed at max levels.

The layout and the cluster side are planned in
[`infra/docs/BROWSER.md`](https://github.com/bfeitknecht/infra) (the plan
document is the source of truth for ports and routing).

## Files

- `Dockerfile` — browsh image (pinned digest) + openssh + uv + bun +
  Arachnidium (pinned commit) + patches
- `patches/patch.py` — exact-anchor rewrite of `addon.py` for in-pod use
- `entrypoint.sh` — bun-api, mitmdump, sshd, `browsh --http-server-mode`
- `browser-session` — per-SSH-session browsh: fresh HOME + profile, 12h cap
- `prepare-profile.sh` — proxy prefs (`user.js`) + mitm CA import via certutil
- `config.toml` — browsh HTTP server (port, rate limit, blocked domains)
- `defaults.json` — Arachnidium settings (GUI off, image quality)

## Commands

- `just image` builds the local image
- `just run` runs it and prints the local URLs
- `just release` tags `v<VERSION>` and pushes; CI publishes to
  `ghcr.io/bfeitknecht/browser`
