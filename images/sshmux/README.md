# sshmux

One WAN port (2222) in; one SSH TUI backend per username out. The cluster
side (users, routes, keys) lives in
[`infra` `applications/sshmux`](https://github.com/bfeitknecht/infra), not
in this image:

- `ssh -p 2222 browser@0xbf.ch` → browsh (browser repo, rzbl)
- `ssh -p 2222 0xbf.ch` (any username) → apex TUI
- new TUI services = new usernames in infra; no new WAN ports

- `entrypoint.sh` — users from the mux table, then sshd
- `to-apex` — the default chain into the apex portfolio
- `to-browser` — the key-carrying chain into the browser pod
