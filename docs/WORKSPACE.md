# Workspace conventions (GENESIS)

Status 2026-11-19. Rules come from the post `glob/posts/agents.typ`.

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

| Repo      | flake dev shell                 | fmt --check                                | check            | release form                                         | CI lint                   |
| --------- | ------------------------------- | ------------------------------------------ | ---------------- | ---------------------------------------------------- | ------------------------- |
| apex      | **missing** (cargo not on host) | yes                                        | yes              | `release` (from Cargo.toml)                          | yes                       |
| exhib     | **missing**                     | yes                                        | yes              | `release` (from pyproject.toml)                      | yes                       |
| glob      | **missing**                     | `fmt` formats the justfile only, not Typst | yes              | `release` (from `VERSION`, no commit)                | **missing**               |
| thyme     | **missing**                     | `fmt args="--inplace"` (typstyle)          | yes + `lint`     | `release` (from typst.toml; commits built artefacts) | yes                       |
| syndicate | **missing**                     | yes (typstyle)                             | yes + `test`     | `release` (from typst.toml)                          | yes                       |
| omni      | is the flake                    | `nix fmt` (nixfmt-tree), no justfile       |                  |                                                      | no CI                     |
| infra     | **missing**                     | yes (yamlfmt 0.21.0 + `just --fmt`)        | yes (kustomize)  | `release X.Y.Z` (gates, pins sshmux image)           | yes (2026-11-18)          |

apex, exhib, glob, thyme and infra have `.forgejo/workflows/` mirrors of their GitHub workflows (2026-11-18). They need the secret `GHCR_TOKEN` on Forgejo.

## Next steps (proposed, not done)

1. One shared dev shell: omni exposes `devShells` per language (rust, python, typst). Each repo's `flake.nix` imports it. Then `cargo`, `uv`, `typst`, `typstyle`, `just`, `kubectl` come from one place.
2. glob: `fmt` runs typstyle with the thyme settings (`--line-width 120`), and a CI lint job.
3. omni: a `justfile` (`fmt`, `check` = `nix flake check`) and CI.
