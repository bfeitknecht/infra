# opencode

The image of the isolated opencode web server (`infra/kubernetes/applications/opencode`).

- `@opencode/cli` (opencode v2, pinned) on node 22. The server command is
  `opencode serve`; it serves the API and the web UI and always requires a
  password (`OPENCODE_PASSWORD` from `opencode-secrets`).
- `opencode-sandbox` (pinned) in `/opt/opencode-sandbox`, loaded by `file://`
  from the opencode config (directory form; v2 resolves `dist/v2.js`). Every
  bash command runs in bubblewrap with a filesystem allowlist and a network
  domain allowlist.
- `patch.mjs` sets `enableWeakerNestedSandbox`: a Kata container cannot mount
  a fresh `/proc`, so the sandbox binds the existing one. Commands still run
  in their own user, PID and network namespaces.

Published with the infra release tag, like `sshmux`.
