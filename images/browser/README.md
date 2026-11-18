# browser

browsh over SSH: a text browser in the terminal.

SSH only: port 22; the infra `sshmux` chains in here with
`ssh -p 2222 browser@0xbf.ch`. One browsh TUI + one Firefox, one session at
a time (browsh hard-codes Marionette 2828 and refuses to start beside
another headless Firefox).

The layout and the cluster side are planned in
[`infra/docs/BROWSER.md`](https://github.com/bfeitknecht/infra) (the plan
document is the source of truth for ports and routing).

## Files

- `Dockerfile` — browsh image (pinned digest) + openssh
- `entrypoint.sh` — sshd as the only process
- `browser-session` — per-SSH-session browsh: lock, fresh HOME + profile + TMPDIR, 12h cap
- `config.toml` — browsh TUI config

## Commands

- `just image` builds the local image
- `just run` runs it and prints the local URLs
- `just release` tags `v<VERSION>` and pushes; CI publishes to
  `ghcr.io/bfeitknecht/browser`
