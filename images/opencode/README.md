# opencode

The image of the isolated opencode web server (`infra/kubernetes/applications/opencode`).

- `opencode-ai` (pinned) on node 22.
- `opencode-sandbox` (pinned) in `/opt/opencode-sandbox`, loaded by `file://`
  from the opencode config. Every bash command runs in bubblewrap with a
  filesystem allowlist and a network domain allowlist.
- `patch.mjs` sets `enableWeakerNestedSandbox`: a Kata container cannot mount
  a fresh `/proc`, so the sandbox binds the existing one. Commands still run
  in their own user, PID and network namespaces.

Published with the infra release tag, like `sshmux`.
