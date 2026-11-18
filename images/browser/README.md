# browser

Browsh + Arachnidium: a very low bandwidth browsing pod.

SSH only: port 22; the infra `sshmux` chains in here with
`ssh -p 2222 browser@0xbf.ch`. One browsh TUI + one Firefox, one session at
a time (browsh hard-codes Marionette 2828 and refuses to start beside
another headless Firefox).

The session Firefox sends all
traffic through the in-pod Arachnidium mitmproxy: images to WebP/AVIF,
html/css/js/svg minified, responses recompressed at max levels.

The layout and the cluster side are planned in
[`infra/docs/BROWSER.md`](https://github.com/bfeitknecht/infra) (the plan
document is the source of truth for ports and routing).

## Files

- `Dockerfile` — browsh image (pinned digest) + openssh + uv + bun +
  Arachnidium (pinned commit) + patches
- `patches/patch.py` — exact-anchor rewrite of `addon.py` for in-pod use
- `entrypoint.sh` — bun-api, mitmdump, then sshd as the main process
- `browser-session` — per-SSH-session browsh: lock, fresh HOME + profile + TMPDIR, 12h cap
- `prepare-profile.sh` — proxy prefs (`user.js`) + mitm CA import via certutil
- `config.toml` — browsh TUI config
- `defaults.json` — Arachnidium settings (GUI off, image quality)

## Commands

- `just image` builds the local image
- `just run` runs it and prints the local URLs
- `just release` tags `v<VERSION>` and pushes; CI publishes to
  `ghcr.io/bfeitknecht/browser`
