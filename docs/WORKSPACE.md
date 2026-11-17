# Workspace conventions (GENESIS)

Status 2026-11-16. Rules come from the draft post `glob/posts/notes-to-agents.typ`.

## Target interface

Every repository has:

- `flake.nix` with a dev shell (`nix develop`) that pins every tool CI uses.
- `justfile` with these verbs (only the ones that apply):

| Verb                                    | Meaning                                                                  |
| --------------------------------------- | ------------------------------------------------------------------------ |
| `just`                                  | list recipes (`default: @just --list`)                                   |
| `just fmt` / `just fmt --check`         | format in place / report only (CI)                                       |
| `just check`                            | everything CI runs: format check, lint, tests, build                     |
| `just serve`                            | local preview                                                            |
| `just image`                            | build container image locally                                            |
| `just release` / `just release --check` | read version from manifest, validate, tag `vX.Y.Z`, push / validate only |

- CI job that runs format check and lint on every push and pull request.
- `release` never commits. It tags a clean tree that matches origin.
- Version source of truth is the manifest: `Cargo.toml`, `pyproject.toml`, `typst.toml`.

## Current gaps

| Repo  | flake dev shell                 | fmt --check                                | check            | release form                                             | CI lint                   |
| ----- | ------------------------------- | ------------------------------------------ | ---------------- | -------------------------------------------------------- | ------------------------- |
| apex  | **missing** (cargo not on host) | yes (2026-11-16)                           | yes              | `release` (from Cargo.toml, 2026-11-17)                  | yes                       |
| exhib | **missing**                     | yes (2026-11-16)                           | yes (2026-11-16) | `release` (from pyproject.toml)                          | yes (2026-11-16)          |
| glob  | **missing**                     | `fmt` formats the justfile only, not Typst | yes              | `release` (from `VERSION`, no commit, 2026-11-17)        | **missing**               |
| thyme | **missing**                     | `fmt args="--inplace"` (typstyle)          | yes + `lint`     | `release` (from typst.toml; commits built artefacts)     | yes                       |
| omni  | is the flake                    | no justfile                                |                  |                                                          | no CI                     |
| infra | **missing**                     | no justfile                                |                  | tags by hand                                             | no CI lint (only publish) |

## Next steps (proposed, not done)

1. One shared dev shell: omni exposes `devShells` per language (rust, python, typst). Each repo's `flake.nix` imports it. Then `cargo`, `uv`, `typst`, `typstyle`, `just`, `kubectl` come from one place.
2. glob: `fmt` runs typstyle with the thyme settings (`--line-width 120`). `release` stops auto-committing and reads the version from one file.
3. ~~Unify `release` arguments~~: done 2026-11-17. All four take no argument, read the manifest, support `--check`. thyme still commits its rebuilt manual and thumbnail by design.
4. infra: `justfile` with `check` (kustomize build of every dir + yamllint) and `release` (next semver tag). CI runs `check` on pull requests.
