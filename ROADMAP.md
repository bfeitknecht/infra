# Roadmap

Status as of 2026-10-14. Three lanes run in parallel — **infra** (this repo), **omni** (nix), **web** (apex + whims) — and only touch at a few gates. This file is the ordered work queue; the `.private/TODO.md` scratchpads in each repo feed it and can be pruned against it.

## Where things stand

- **Platform baseline is live** (through tag `v1.14.0`): Flux reconciles the full tree (`storage -> cilium -> ipam`, `cert-manager -> traefik -> tailscale`, CRDs phase), the Gateway holds `10.10.20.128`, LE wildcard + internal CA certificates issued, monitoring + Gatus up, k8up operator deployed, Keel (tier 2) and Knative Serving + `whimsy` (tier 3) live.
- **Kata shipped in `v1.14.0`** — schematics for rbpi + rzbl, RuntimeClass `kata-qemu`.
- **Teleport CE wired in tree** (`infrastructure/teleport/`, chart 18.10.0): standalone auth+proxy, multiplex TLS on its own LB IP `10.10.20.154`, local + WebAuthn auth, k8up-scheduled. Live: admin user + passkey bootstrapped; devil agent join pending.
- **Apps live:** apex, AdGuard Home, knotd + kresd, DDNS, Homepage, Forgejo (`git.0xbf.ch`), ATProto PDS (`pds.0xbf.ch`).
- **Local, unpushed:** `b19a45f` — topf patch restructure (`patches/node/<host>/`), `schematic.rzbl.yaml` + rzbl node patches, HARDWARE.md. Push when convenient; `talos/` rides `topf apply`, not the Flux tag.
- **rbpi is currently powered down** mid-rework. Step 0 of everything cluster-side is plugging it back in — it rejoins as-is on the old schematic.
- **Backup gap:** k8up is deployed and forgejo/pds Schedules exist, but jobs fail until the NAS tailnet path is fixed — nothing is actually backed up yet.
- **omni** is a working dendritic flake: home modules (shell, tools, git, editor/nvf, nix tooling, gpg, sops secrets) + hosts `auto` (darwin), `devil` (NixOS kata-pod image), `vm` (microvm test bed).
- **apex** is a one-page Deno site (Preact + htm, no client runtime); a **complete rework** is planned — CV and blog land in the new structure, not as an appendage.

## The dependency graph

```
rbpi plugged in (old schematic) -> cluster back -> NOW queue
case design -> validated -> final assembly (HARDWARE.md) -> rbpi up -> samba + SATA storage
rzbl: maintenance mode -> topf apply -> GPU labels -> THEN queue
      -> technically needs only oci + tailnet — may be pulled ahead of the case work
backup path works -> GATE: nothing irreplaceable (immich, photos) before this
omni: age key backed up -> zed + macOS parity -> macbook factory reset -> nix iteration
```

## NOW — cluster is back (no hardware prerequisites)

- [x] First: plug rbpi in, let it boot and rejoin (old schematic), then `flux get kustomizations` all green.

### Cluster

- [x] **Teleport CE** — deployed and bootstrapped (`infrastructure/teleport/`, chart 18.10.0 standalone, multiplex TLS on own LB IP `10.10.20.154`, local + WebAuthn, k8up-scheduled). Admin user `bf` (access/editor/auditor) registered with a passkey; `tsh login --proxy teleport.internal` works.
- [x] **Devil live — access model switched (2026-10-20)**: teleport is superseded but **stays until the friend demo** (teardown is a queued LATER item). New doors, all via the gateway (one hostname, `devil.internal`, knot wildcard — no DNS record needed):
    - **ssh 2222** — new traefik entrypoint `devilssh` (port 2222, **no hostPort**, no WAN — the router forwards nothing; WAN 2222 stays reserved for the future dev box) + gateway listener + TCPRoute `ssh` → headless Service → VM sshd (pubkey-only, host keys persisted on the PVC).
    - **ghostty-web** — HTTPRoute `devil` (websecure-internal, internal-allowlist copy — the only middleware, no basic-auth) → headless Service :7681 → **ttyd in the VM** (`devil.nix` in omni) serving the static page (ConfigMap `devil-ghostty-web` from `ghostty-web/index.html` — one html file, ghostty-web from CDN, ttyd wire protocol) and running a **real `login`** — auth is bf's PAM password (omni sops), not a middleware.
    - The **headless** Service exists because the kata VM bypasses Cilium's service translation in both directions — ClusterIP/LB never reach it; clients dial the pod IP via Endpoints (the pod-to-pod path that works).
    - PVC renamed `devil-state` → `devil-pvc` (subPaths home/ssh/teleport). ⚠️ **migration runbook before the tag** (`.private/devil-pvc-rename.md`) — Flux prune deletes the old bound PVC and its data (the running VM holds the age key, the omni clone, the teleport identity): scale devil to 0, create `devil-pvc` from the manifest, busybox copy pod (`cp -a`, verify `du`), keep replicas at 0, tag — prune deletes `devil-state` and the manifest restores `replicas: 1`.
    - Remaining: owner keypair+secrets (omni: `ssh/devil`, `login/devil`) → `nix build .#devil` → `docker import --platform linux/arm64` → push `latest` → infra tag → smoke tests (ssh from mac/ish, login prompt at https://devil.internal, `tsh ssh` still works).
- [ ] **atuin server** on the cluster (omni already ships the client).
- [ ] **Backup path** — fix the friend's tailnet ACL (`autogroup:shared` -> `100.96.72.126:3900`), smoke-test the restic round-trip, then a restore drill against forgejo's PVC. **Gate for every data-bearing app below.**
- [ ] **Fix grafana homepage API widget.**
- [ ] **LAN DNS cutover** — router DHCP DNS -> `10.10.20.153` (AGH), tailnet split DNS for `internal.`; retire hosts-file stopgaps.
- [ ] **Forgejo actions** (optional now): CI runner so apex/whim repos can move off GitHub Actions.

### Web

- [ ] **apex: complete rework** — rebuild the site rather than appending to it: new structure and design, CV and blog included in the rework. Comments come later (identity lane).

### omni — pre-reset parity (the macbook reset gate)

- [ ] **Back up the age key** (`~/.config/sops/age/keys.txt`) — before any transfer, full stop.
- [ ] **Zed settings -> nix** (layout, theme, extensions) — as little global config as possible; prefer per-project `.zed/settings.json`.
- [ ] **macOS defaults parity** via nix-darwin `system.defaults`: dock (autohide, show speed), finder (quittable), wallpaper, liquid-glass styling.
- [ ] **Brewfile parity** — un-comment the casks actually in use so the reset restores app parity.
- [ ] FileVault is enabled manually during the reset (not declarable via nix-darwin).

## NEXT — hardware

### Case + final assembly (gates samba)

- [ ] **Design the rbpi case** — CAD -> print -> validate fit/clearance against the HARDWARE.md stack (Pi + 52Pi B12 + Penta HAT + back-mounted Seeed + heatsinks + FFC routing).
- [ ] **Final assembly** per the HARDWARE.md checklist (power module -> PCIe chain/FFCs -> fans -> standoffs -> multimeter check -> power-on order).
- [ ] rbpi back up -> **samba** (SATA drives via the Penta HAT) + **storage planning** (what lives where, hostPath vs PVC).

### Razer Blade (technically independent — only needs oci + tailnet)

- [ ] Boot Talos media -> maintenance mode -> add the node to `talos/topf.yaml` (`schematicId: "@schematic.rzbl.yaml"`, real IP) — patches already exist (`patches/node/rzbl/`: NVMe install disk, sysctls, tailscale).
- [ ] `topf apply` -> verify join -> node labels/taints + NVIDIA device plugin so GPU workloads schedule deliberately.
- [ ] Unlocks the THEN queue.

## THEN — unlocked by the Blade

- [ ] **Immich** (`photos`, ML on the GPU) — only after the backup gate.
- [ ] ***arr + Jellyfin** (`prowlarr`/`sonarr`/`radarr`, `jellyfin`).
- [ ] **Copyparty** (`files`), **Dawarich**, **ppty**.
- [ ] **Ollama + Open WebUI** (GPU).

## LATER

- [ ] **Identity & SSO** — research before committing:
    - Decide the aggregator: authentik vs dex — the thing forgejo/grafana/blog talk OIDC to.
    - Research atproto-as-primary-identity: atproto OAuth is its own profile, not plain OIDC — putting the PDS in front of an aggregator needs a bridge, or atproto stays a parallel login flow. This decision determines whether friends can use Google/Apple _and_ atproto behind one door.
    - Then: forgejo OIDC, grafana OIDC, identity-gated blog comments.
- [ ] **Renovate** — decision: GitHub App on this repo vs self-hosted against Forgejo.
- [ ] **Alerting** — Alertmanager receiver decision (ntfy/Discord/Telegram); grafana dashboards.
- [ ] **Teleport teardown (queued — kept for the friend demo)**: `infrastructure/teleport/`, the devil teleport mounts/secret/configmap + `dependsOn: teleport`, omni's teleport unit + port 3022 + `TELEPORT_SESSION` prompt special-case, AGENTS/README notes. Devil runs ssh (2222) + ghostty-web (ttyd + real login) meanwhile.
- [ ] **Daytona** agent sandbox; opencode kata container (if not done with devil).
- [ ] **Macbook factory reset** -> omni bootstrap (README runbook) -> iterate; rice (sketchybar/yabai/…) lives here, post-reset.
- [ ] Upgrades: k8s 1.35.3 -> 1.37 (`talosctl upgrade-k8s`), Talos patch bumps, local kubectl.

## SOMEDAY / ideas

XMPP (Prosody), Mumble, I2P, Yggdrasil, Reticulum, Meshtastic, wasmCloud, opengist, atproto ecosystem experiments (knot, spindle), flake exposes apps/tools (nvim, home), deeper nvf config.

## The whims workflow (standing)

Trying a language or framework is a tier-3 whim — no git manifests, no planning, registry push = deploy:

```nu
kn service create <name> --image ghcr.io/bfeitknecht/<name>:<tag> --port <port> -n whimsy
kn service update <name> --image ghcr.io/bfeitknecht/<name>:<new-tag>   # SHA/version tags, not :latest
```

The domain template is `{{.Name}}.0xbf.ch` — the KSvc name declares the subdomain. Pull secrets are already on the namespace default SA. Candidates from the idea pile: idea tracker, blog backend, whatever framework itch.

## PVC planning

| Service         | Node | PVC                                                     |
| --------------- | ---- | ------------------------------------------------------- |
| AdGuard Home    | rbpi | nvme? 1Gi                                               |
| prometheus      | rbpi | nvme? 1Gi                                               |
| gatus           | rbpi | nvme? 1Gi                                               |
| renovate        | rbpi |                                                         |
| Homepage        | rbpi |                                                         |
| Forgejo         | rbpi | nvme                                                    |
| ATProto PDS     | rbpi | nvme                                                    |
| apex            | rbpi |                                                         |
| atuin           | rbpi | small                                                   |
| teleport        | rbpi |                                                         |
| devil           | rbpi | devil-pvc 20Gi (home, ssh host keys, teleport identity) |
| Immich          | rzbl |                                                         |
| Copyparty       | rzbl |                                                         |
| Dawarich        | rzbl |                                                         |
| *arr + Jellyfin | rzbl |                                                         |

## Conventions for every new application

- One directory per app under `kubernetes/applications/<category>/<app>/` with its own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`, `dependsOn` only what it actually needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; adding an app means adding an HTTPRoute, never a DNS entry. Exception: non-cluster LAN devices get explicit records in the knot `internal.` zone (e.g. `router.internal` -> the router's own IP) — no HTTPRoute, no Traefik, no internal CA.
- Tier discipline: tier 1 = pinned image, git-tagged; tier 2 = Keel-polled `:latest` with `spec.ignore` on the image field; tier 3 = `kn` in `whimsy`, never in this tree. Keel annotations never go on tier 1/tier 3 workloads.
