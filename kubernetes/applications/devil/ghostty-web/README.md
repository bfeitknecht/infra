# ghostty-web — the devil.internal terminal page

One static `index.html`: a bare autosized terminal div importing
[ghostty-web](https://github.com/coder/ghostty-web) 0.4.0 and
@xterm/addon-fit from esm.sh — no runtime, no build, no npm. It speaks
ttyd's wire protocol (documented in the html comment): `GET /token`, then
`wss://<host>/ws` subprotocol `ttyd`, binary frames `'0'`+input /
`'1'`+resize, server `'0'`+output. Themes are a pure inverse pair
(fff-on-000 / 000-on-fff), start dark, and follow the system theme via a
`prefers-color-scheme` watcher.

The server is **ttyd inside the devil VM** (omni flake, `devil.nix`): it
serves this page (`-I /srv/ghostty-web/index.html`, mounted from the
ConfigMap below) and puts a **real `login` prompt** on the PTY — auth is
bf's PAM password (omni sops, `login/devil`), not a middleware. The
`internal-allowlist` middleware is the only gate on the route.

Routing (this directory): HTTPRoute `devil` (devil.internal → headless
Service port 7681), TCPRoute `ssh` (devilssh entrypoint → headless
Service port 2222). The headless Service exists because the kata VM
bypasses Cilium's ClusterIP translation — see `deployment.yaml`.

No secrets live here. Updates: edit `index.html` → tag; the
configMapGenerator hash rolls the pod.
