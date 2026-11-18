# The commands for this repository.

# List the recipes
default:
    @just --list

# Build the in-tree image locally. CI builds and pushes them on release tags.
image:
    #!/usr/bin/env sh
    set -eu
    docker build -t ghcr.io/bfeitknecht/sshmux:dev --platform linux/arm64 images/sshmux

# Check: every Flux Kustomization path must build. Reads from disk, no cluster access.
check:
    #!/usr/bin/env sh
    set -eu
    # `kubectl kustomize` decrypts nothing: sops files build with their
    # ciphertext, which is what the OCI artifact carries too.
    # `path:` values sit two spaces in, in the Flux Kustomizations. Only
    # `./kubernetes/...` paths live in this repo (the OCI artifact root).
    # The CRD sources use paths inside their pinned GitRepositories instead.
    # `./kubernetes/cluster` is the Flux root: it holds Kustomization manifests
    # (Flux resources), not a kustomize directory. Flux applies it as a list.
    paths="$(grep -hE '^  path: \./kubernetes/' kubernetes/cluster/*.yaml kubernetes/flux/sync.yaml 2>/dev/null \
      | sed 's/^ *path: //' | grep -v '^\./kubernetes/cluster$' | sort -u)"
    [ -n "$paths" ] || { echo "check: no Kustomization paths found" >&2; exit 1; }
    for p in $paths; do
        printf '==> %s\n' "$p"
        kubectl kustomize "$p" > /dev/null
    done
    echo "all Kustomizations build"

# Format the YAML tree and the justfile. `just fmt --check` only reports. Sops files excluded.
fmt *args:
    #!/usr/bin/env sh
    set -eu
    # `.yamlfmt` (repo root) holds the style and the exclusions. yamlfmt has
    # only single-dash flags, so the recipe owns them and takes just `--check`.
    if ! command -v yamlfmt >/dev/null 2>&1; then
        echo "yamlfmt not found — install it with: go install github.com/google/yamlfmt/cmd/yamlfmt@v0.21.0" >&2
        echo "(brew: brew install yamlfmt)" >&2
        exit 1
    fi
    case "{{ args }}" in
      "")
        yamlfmt
        just --fmt
        ;;
      "--check")
        yamlfmt -lint
        just --fmt --check
        ;;
      *)
        echo "fmt: unknown flag {{ args }} (known: --check)" >&2
        exit 1
        ;;
    esac

# Tag vX.Y.Z and push. `--check` validates only. Never commits: tags a clean tree.
release version *flags:
    #!/usr/bin/env sh
    set -eu
    version="{{ version }}"
    tag="v${version}"
    flags="{{ flags }}"

    # The version is not stored in a file: pass X.Y.Z, and no 'v' prefix.
    printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' \
      || { echo "release: version '${version}' is not X.Y.Z" >&2; exit 1; }
    ! git rev-parse -q --verify "refs/tags/${tag}" >/dev/null \
      || { echo "release: tag ${tag} exists" >&2; exit 1; }
    [ -z "$(git status --porcelain)" ] \
      || { echo "release: working tree is not clean; commit first" >&2; exit 1; }
    git fetch -q origin
    [ "$(git rev-parse HEAD)" = "$(git rev-parse '@{u}')" ] \
      || { echo "release: HEAD differs from upstream; push or pull first" >&2; exit 1; }

    # The in-tree image (sshmux) publishes with the release tag. The
    # Deployment pins must name it: a tag whose images mismatch crashes loops.
    for app in sshmux; do
        pin="$(grep -oE 'ghcr.io/bfeitknecht/'"$app"':v[0-9]+\.[0-9]+\.[0-9]+' \
          "kubernetes/applications/$app/deployment.yaml" | head -1)"
        [ "$pin" = "ghcr.io/bfeitknecht/$app:$tag" ] \
          || { echo "release: $app deployment pins '$pin', not $tag; bump the pin in the same commit" >&2; exit 1; }
    done

    just check
    just fmt --check
    case "$flags" in *--check*) echo "${tag} is ready"; exit 0 ;; esac

    # A tag publishes the OCI artifact and Flux reconciles it. A broken tag
    # blocks reconcile until the next tag, so everything runs before it exists.
    git tag -a "${tag}" -m "Release ${version}"
    # One push, so a failed tag push cannot leave the branch without its tag.
    git push --atomic origin HEAD "${tag}"
    echo "release: pushed ${tag}; CI publishes ghcr.io/bfeitknecht/infra; Flux reconciles"
