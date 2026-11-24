# opencode

The image of the isolated OpenCode server (`infra/kubernetes/applications/opencode`).

It is a Nix build. The definition lives in omni, `modules/images/opencode.nix`;
`flake.nix` here pins omni in `flake.lock`, so a release tag names exactly one image.
CI (`publish-manifests.yaml`) builds it with `nix build ./images/opencode#default`
and pushes it as `ghcr.io/bfeitknecht/opencode:<release tag>`.

- OpenCode v2 (`@opencode/cli` prebuilt binary, glibc loader linked at `/lib64`).
  `opencode serve` serves the API and the web UI and requires a password.
- `opencode-sandbox` (pinned, patched with `enableWeakerNestedSandbox` for Kata) as a
  root-owned copy in `/opt/opencode-sandbox`. Every bash command runs in bubblewrap.
- The sandbox policy is `/etc/opencode-sandbox.json` (root-owned, generated in omni):
  writes to the project, `/tmp` and single-user nix; every store path the image ships
  is write-denied (they run unsandboxed); secrets and OpenCode's state are read-denied;
  a network domain allowlist. infra's CiliumNetworkPolicy must allow the same names.
- Claude Code with `/etc/claude-code/managed-settings.json`.
- Single-user lix as uid 1000 (`node`): `nix develop` works without a daemon.
- MCP servers `mcp-nixos`, `forgejo-mcp` (configured in `opencode.json`).

Bump omni (OpenCode, Claude Code, the policy): `nix flake update omni` here, commit,
release. Build locally: `just image` (x86_64-linux, e.g. on devil).
