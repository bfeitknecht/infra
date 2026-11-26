# AGENTS.md

Read this before you change the repo. It holds the rules and the traps.
The full notes per component (how, why, history) are in `docs/COMPONENTS.md`:
**read the section of a component before you change it**, and update it in the
same commit. Owner runbook: `docs/OPERATIONS.md`.

## What this is

Declarative infra for a hybrid Talos Linux cluster (Talos 1.14.6, K8s 1.37.2). One control plane in Oracle Cloud `eu-zurich-1` at `10.20.20.10` (oci). Two workers at home: `10.10.20.10` (rbpi, Pi 5) and `10.10.20.11` (rzbl, Razer Blade 15, i7-9750H, GTX 1660 Ti). Flux manages all cluster state from this repo.

## Rules

Use ASD-STE100. Write short sentences. Be terse and explicit.

The cluster consumes only published OCI artifacts:

```
edit manifests -> git commit -> push vX.Y.Z tag -> CI publishes to ghcr.io/bfeitknecht/infra -> Flux reconciles
```

- Do not run `kubectl apply`. Dry-run is allowed.
- OCIRepository tracks `semver >=1.0.0`. Re-tagging the same commit does nothing. Check tag content with `git show <tag>:<path>`.
- A broken tag breaks reconcile until the next tag. `just release X.Y.Z` gates on `just fmt --check` and `just check`.
- `docs/web/index.html` is the interactive atlas (open in a browser, no build). When you change cluster state, update its DATA block (NODES, SERVICES, NEEDS, TAGS, SECRETS) in the same PR. Add every finished task as one line to `DONE` (`[date, what]`, newest first).
- Owner runs nushell. Write all owner-facing commands in nushell (`let`, `$env.X` only for export, `http get`, `from json`, quoted `"@nameserver"` args).

## Layout

```
images/opencode/      flake.nix pinning omni: the OpenCode server image (Nix build)
talos/                topf config, schematics, node patches (talos/patches/node/<node>/)
docs/                 COMPONENTS.md (full notes), OPERATIONS.md (runbook), GUIDE.md, journey.md, web/ (atlas)
kubernetes/
├── flux/             source.yaml (OCIRepository), sync.yaml (root Kustomization)
├── cluster/          root Kustomizations: crds.yaml (pinned CRD sources), infrastructure.yaml, applications.yaml
├── infrastructure/   storage, backup (k8up), egress (tailscale-relay), gpu, kata, keel, knative,
│                     monitoring, network (cilium, ipam), ingress (cert-manager, traefik, tailscale)
└── applications/     one directory = one namespace = one Flux Kustomization
```

Apps: apex (`0xbf.ch` + SSH TUI), glob (`blog`), exhib (`gallery`), atuin, forgejo (`git`), forgejo-runner, pds, immich (`photos`), authentik (`auth`), agh, ddns, dns, media (jellyfin `videos`, *arr, navidrome `music`, seerr, bazarr, flaresolverr), qbittorrent (ns media), ollama, opencode (Kata), copyparty (`files`), dawarich (`locations`), samba (Time Machine), devil (Kata NixOS VM, tailnet only), renovate, ntfy (`notify`), sshmux (sshpiper on WAN 2222), homepage (off).

## Naming conventions

One rule per kind. New resources must follow them.

- **Namespace = app directory name.** Platform parts use their component name (`ingress`, `egress`, `gpu`).
- **Workload and Service = `<app>`**; helpers `<app>-<role>` (`<app>-db`, `<app>-redis`, `<app>-<component>`). File names match the role.
- **PVC = `<app>-<role>`**, role: `data` (state, SQLite), `db` (Postgres), `files` (bulk user content), `cache` (rebuildable). Shared volumes use the namespace as `<app>`.
- **StorageClass by role:** `data`/`db`/`cache` on `local-path-nvme`, `files` on `local-path-ssd` (rzbl). rbpi apps use `local-path`.
- **Secret = `<app>-secrets`** (env keys) or `<app>-config` (whole config file). **File = `<secret-name>.sops.yaml`.** Exception: GHCR pull secret `dockerconfigjson` in `ghcr.sops.yaml`.
- **ConfigMap = `<app>-config`** (`configMapGenerator`, hash suffix).
- **Hostnames:** public services by **purpose** (`git`, `auth`, `blog`, `gallery`, `videos`, `files`, `photos`, `locations`, `music`). The authentik launcher shows them as `Purpose (Software)`, e.g. `Git (Forgejo)`. Avoid names with two meanings. Internal tools by **software**: `<app>.internal`. Every new `*.internal` name goes into the `internal-hosts` certificate `dnsNames` in the same PR.
- **LB IPs:** last octet = `100 + (port mod 100)`. Check for a clash first. Gateway is `.128`.
- **Flux Kustomization = app directory name.**
- Known exceptions: Service `pds-http` (a Service `pds` injects `PDS_PORT` and breaks the image); Service `resolver` in `dns`; qbittorrent runs in ns `media` (shares PVC `media-files`).
- PVC rename without copying: PV `Retain`, suspend + scale 0, delete PVC, set PV `claimRef` to the new name (no uid), tag, resume.

## Workload placement

One node failure must take down one role only.

- **oci:** control plane + `dns` resolver. The taint stays. No other workloads.
- **rbpi** (always-on edge): Traefik (pinned), AGH, tier-1 small-state apps (forgejo, pds, atuin), tier-2 sites, monitoring. Platform controllers **prefer** rbpi (`preferredDuringScheduling`, weight 100): cert-manager, Keel, tailscale operator, local-path-provisioner, Flux (a `kubectl patch`; a new `flux install` drops it).
- **rzbl** (heavy): GPU, bulk storage, Postgres apps (authentik, immich, dawarich), Kata VMs (opencode, devil), CI runner. It boots from USB: do not make the cluster depend on it to heal.
- Stateless apps float. Stateful apps follow their PVC (local-path PVs are node-bound).

## Kustomization dependency tree

```
storage -> cilium -> ipam;  storage -> egress-tailscale
cilium also dependsOn prometheus-crds
cilium -> cert-manager -> traefik -> tailscale
traefik also dependsOn gateway-api-crds, traefik-crds
monitoring dependsOn prometheus-crds, traefik
backup dependsOn k8up-crds, egress-tailscale
knative-operator dependsOn knative-operator-crds; knative-serving dependsOn knative-operator
keel, gpu, kata: no dependencies

apps: most depend on storage and traefik
agh +dns; media, ollama +gpu; devil +kata; opencode +ollama, authentik
forgejo-runner +forgejo; qbittorrent +media; authentik +k8up-crds
sshmux +traefik, sshpiper-crds; renovate: none
```

Dry-run validates all manifests in a Kustomization before apply. A CR without its CRD fails the dry-run, and then nothing in that Kustomization applies (also not the HelmRelease that would make the CRD). So:

- Never put CRs and their CRD source in the same Kustomization.
- CRDs come from pinned upstream GitRepository tags in `cluster/crds.yaml` (`prune: false`), from Helm charts, or from an operator at runtime. Never vendor CRD YAML.
- Bump a chart and its CRD GitRepository tag in the same commit.

## Traps

Each line broke something once. Details in `docs/COMPONENTS.md`.

- **Cilium:** `kubeProxyReplacement: true` with `socketLB.hostNamespaceOnly: true` (Kata VMs bypass socket hooks). `gatewayAPI.enabled: false` (Traefik owns Gateway API). Do not vendor Cilium CRDs.
- **Traefik:** values schema is strict (`global`, not `globalArguments`; `http.redirections.entryPoint`, not `redirectTo`). Listeners use entrypoint ports `8000/8443/22/2222`, not Service ports. `experimentalChannel: true` (TCPRoute). To change the Gateway API channel, delete the `safe-upgrades` VAP and binding first. Do not add a hostname filter to `websecure`: it breaks the bare domain.
- **Router:** the Zyxel forwards WAN only to DHCP-known devices, so Traefik binds `hostPort` 80/443/22/2222 on rbpi. DNS is grey-cloud only; the owner rejects the Cloudflare proxy.
- **DNS:** do not point the router DNS at the LAN resolver (ISP firmware hijack, loop). AGH at `10.10.20.153` is the LAN edge; kresd Service pinned at `10.96.0.53`.
- **Internal CA:** name-constrained to `.internal`; `internal-hosts` lists explicit names (no `*.internal`). After a CA re-issue, delete Secret `internal-hosts-tls` and re-install the CA on devices.
- **Tailscale operator:** do not rename Secret `operator-oauth`. OAuth client tags are fixed at creation.
- **Tailscale nodes:** an extra home node needs `--accept-routes --advertise-routes=<ip>/32` plus `RoutingRuleConfig` priority 5200 `dst 10.10.0.0/16 table main`, or rbpi's route hijacks LAN traffic.
- **Tagged nodes cannot reach shared-in machines.** Use the untagged `tailscale-relay` (ns `egress`) for shared targets (Garage).
- **Kata memory:** each Kata VM is 2 GiB plus its memory limit, backed by rzbl `/dev/shm` (8.3 GB). A full shm kills qemu (SIGBUS, no guest log). Keep both VMs' limits + 4 GiB below shm: opencode 2Gi, devil 4Gi. rzbl runs its own qemu config (`reclaim_guest_freed_memory`, `talos/patches/node/rzbl/08-kata.yaml`).
- **Kata pods:** a clean shutdown still leaves the pod `Error` (exit 143); with `strategy: Recreate` it blocks the rollout until deleted. Each force-delete can leave an orphan qemu: check `talosctl -n <node> ps | grep qemu`. The stop can also hang with the guest still up (devil, v1.92.0: Terminating for 15 min): `ssh bf@devil sudo systemctl poweroff` ends it cleanly, no orphan.
- **devil:** stays Kata (owner, 2026-11-23). Tailscale SSH only (`ssh bf@devil`): no sshd, no Service, no route; do not add an HTTPRoute. `register-nix-paths.service` stays masked in omni (it hangs the systemd job queue). After a move: no qemu on the old node, and `rex whoami` matches.
- **opencode:** the image pin in `applications/opencode/` must equal the release tag (`just release` refuses a mismatch); bump `images/opencode/flake.lock` with `nix flake update omni`. Never set `OPENCODE_SANDBOX_CONFIG` (it overrides the policy file). Never put model keys or `ANTHROPIC_API_KEY` in env vars.
- **Tier-2 (apex, glob, exhib):** `:latest` + Keel; the Kustomization must ignore the image field, or Flux reverts Keel. No Keel on tier 1, tier 3 or Knative.
- **Knative:** all config in the `KnativeServing` CR `spec.config` (the operator overwrites ConfigMaps). Istio plugin disabled. Its PDBs block drains: `topf upgrade --delete-if-eviction-fails`. Whims (`whimsy` ns) are outside Flux: deploy with `kn`.
- **Forgejo:** app.ini edits go into the ConfigMap seed **and** the live `/data/gitea/conf/app.ini` (as `su-exec git`). `ACCOUNT_LINKING = login`, never `auto`. SSO only; clear local 2FA with `forgejo admin user reset-mfa` (`--skip-local-2fa` is a no-op in 16).
- **Web client patches** (jellyfin, immich): initContainer `web` copies the image's web root and patches it with sed. Its image tag must equal the server's. After an upgrade, check its log for "did not match".
- **Seeded configs** (AGH, jellyfin SSO, forgejo app.ini) are copied only if absent; the app owns the file after. Configs from Secrets (copyparty, ntfy) need a `0xbf.ch/config-rev` bump.
- **Services:** a Service named like an app can inject `<NAME>_PORT` env and break images (pds, atuin): use `enableServiceLinks: false` or another name.
- **authentik:** rename blueprint objects in the blueprint, never in the GUI (a GUI rename ends in a duplicate).
- **Header trust:** apps that trust `X-authentik-*` (navidrome, copyparty, exhib upload) need a CNP that admits only Traefik.
- **sshmux:** a new SSH TUI = a new `Pipe`, never a new WAN port. Git is not on the mux.
- **Artifact contents:** `flux push artifact` drops files by its `--ignore-paths` default (`*.jpg`, `*.gif`, `*.zip`, ...; `.sourceignore` is not read). The publish workflow sets the list without `*.png` (v1.95.0 broke media and immich: PNGs missing). A new binary type for a configMapGenerator: check `flux build artifact` contents first.
- **YAML:** quote `"0xbf"` (unquoted it is the number 191).
- **Talos:** `topf.yaml` `kubernetesVersion` must match the cluster, or `topf apply` rolls it back. A new schematic needs `--submit-to-factory` once. topf has no reboot mode: use auto, then `talosctl reboot`.
- **Backups:** Garage is a shared-in NAS: when its tailnet IP changes, update the relay forwarder (`egress/tailscale/relay.yaml`). Never rotate the restic repo password (`k8up-secrets` `password`).

## Secrets

- SOPS + age. `.sops.yaml` matches `*.sops.yaml`. Flux decrypts with Secret `sops-age` in `flux-system`. The file list is in `docs/COMPONENTS.md` (Secrets).
- **Do not decrypt existing secrets to read them. Never print, log or write a plaintext value.**
- Agents may seed **random** secrets: generate in a shell variable, pipe `kubectl create secret ... --dry-run=client -o yaml | sops --encrypt --filename-override <file> --input-type yaml --output-type yaml /dev/stdin > <file>`. Check structure with `sops -d` piped into a redacting parser.
- Owner-provided values come from a file in `.private/` or from `input -s` on the owner's side.
- Some apps echo their config on errors. After a crash loop, check logs before you share them, and rotate any leaked value.

## Cluster access

- `kubectl --kubeconfig kubeconfig ...` (repo root, gitignored; 24 h cert, renew with `topf kubeconfig`). Endpoint: oci tailscale IP `100.73.186.19:6443`. Manage from a tailnet device only.
- `talosctl --talosconfig talos/talosconfig -e 10.20.20.10 -n <node-ip>` for node work (the root `talosconfig` is an empty stub).
- Storage: rbpi `/var/mnt/storage-nvme0|1`; rzbl `/var/mnt/storage-nvme0` and `/var/mnt/storage-ssd0` (4 TB). rzbl Talos is on a USB stick.

## Debugging playbook

1. `flux get kustomizations`: check the first red or Unknown link.
2. `kubectl -n flux-system describe kustomization <name>`: build, dry-run, apply or health error.
3. `kubectl -n <ns> describe helmrelease <name>`: chart values schema error.
4. All Flux controllers crash with `dial tcp 10.96.0.1:443: no route to host`: in-cluster routing is down (often after a Cilium restart). Fix the datapath, then `kubectl -n flux-system rollout restart deployment`.
5. Before a tag: `just check` (builds every Kustomization), `just fmt --check`, `kubectl apply --dry-run=server -f <file>` for `cluster/*.yaml`.
6. After a chart bump, diff `values.yaml` against the pinned values.

## Conventions

- YAML style is `just fmt` (yamlfmt 0.21.0, `.yamlfmt`): 2-space indent, comments and key order kept. Sops files are excluded.
- Use Gateway API for all routing. The Traefik dashboard IngressRoute is the only exception.
- Do not vendor manifests. Operators and charts are pinned.
- Keep YAML comments only for load-bearing facts.
- No hardcoded IPs in Helm values. Keep cluster-specific values in git resources (ipam pool, middlewares).
- Mail: one address, `noreply@0xbf.ch` (Proton SMTP). Bot users take a plus-address. Admin mail to `admin@0xbf.ch`.
- Identities: personal account `bf` / `Basil` / `io@0xbf.ch` everywhere (it is the authentik user). Native admin accounts are `admin` / `admin@0xbf.ch`, never `bf`. Forgejo has no separate admin (`bf`).
- authentik is the IdP for every app that supports it. Table: `docs/OPERATIONS.md` section 1.
