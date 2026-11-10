# Roadmap

Status as of 2026-10-14. Three lanes run in parallel: **infra** (this repo), **omni** (nix), **web** (apex + whims). They meet at few gates. This file is ordered work queue. `.private/TODO.md` in each repo feeds it.

## Where things stand

- **Platform baseline is live** through `v1.14.0`. Flux reconciles full tree (`storage` to `cilium` to `ipam`, `cert-manager` to `traefik` to `tailscale`, CRDs). Gateway holds `10.10.20.128`. LE wildcard and internal CA certs are issued. Monitoring + Gatus are up. K8up operator is deployed. Keel (tier 2) and Knative Serving + `whimsy` (tier 3) are live.
- **Kata shipped in `v1.14.0`**. Schematics for rbpi + rzbl. RuntimeClass `kata-qemu`.
- **Teleport CE removed** 2026-10-24 after friend demo. `infrastructure/teleport/` and devil agent wiring are removed. Devil now uses ssh 2222 + ghostty-web.
- **Apps live:** apex, AdGuard Home, knotd + kresd, DDNS, Homepage, Forgejo at `git.0xbf.ch`, ATProto PDS at `pds.0xbf.ch`.
- **Local, unpushed:** `b19a45f` holds topf patch restructure (`patches/node/<host>/`), `schematic.rzbl.yaml` + rzbl patches, HARDWARE.md. Push when convenient. `talos/` uses `topf apply`, not Flux tag.
- **rbpi is powered down** mid-rework. Step 0 is plug it in. It rejoins on old schematic.
- **Backup gap:** k8up is deployed. Forgejo and pds Schedules exist. Jobs fail until NAS tailnet path is fixed. Nothing is backed up yet.
- **omni** is working flake: home modules (shell, tools, git, editor/nvf, nix tooling, gpg, sops secrets) + hosts `auto` (darwin), `devil` (NixOS kata-pod image), `vm` (microvm test bed).
- **apex** is one-page Deno site (Preact + htm, no client runtime). Full rework is planned. CV and blog go into new structure.

## Dependency graph

```
rbpi plugged in (old schematic) -> cluster back -> NOW queue
case design -> validated -> final assembly (HARDWARE.md) -> rbpi up -> samba + SATA
rzbl: maintenance mode -> topf apply -> GPU labels -> THEN queue
      needs only oci + tailnet. Can run ahead of case work.
backup path works -> GATE: no irreplaceable data (immich, photos) before this
omni: age key backed up -> zed + macOS parity -> macbook reset -> nix iteration
```

## NOW: cluster is back (no hardware prereqs)

- [x] First: plug rbpi in, let it boot and rejoin (old schematic), then `flux get kustomizations` all green.

### Cluster

- [x] **Teleport CE**. Deployed and bootstrapped (`infrastructure/teleport/`, chart 18.10.0, multiplex TLS on LB IP `10.10.20.154`, local + WebAuthn, k8up-scheduled). Admin `bf` (access/editor/auditor) registered with passkey. `tsh login --proxy teleport.internal` works. **Removed 2026-10-24**. See LATER.
- [x] **Devil live. Access model switched (2026-10-20)**: Teleport is superseded and removed 2026-10-24. New doors via gateway (one hostname `devil.internal`, knot wildcard, no DNS record):
    - **ssh 2222**. New entrypoint `devilssh` (port `2222`, no hostPort, no WAN; router forwards nothing; WAN `2222` reserved for future dev box) + gateway listener + TCPRoute `ssh` to headless Service to VM sshd (pubkey-only, host keys on PVC).
    - **ghostty-web**. HTTPRoute `devil` (`websecure-internal`, allowlist copy in devil ns, only middleware, no basic-auth) to headless Service `7681` to **ttyd in VM** (`devil.nix` in omni) serving static page (ConfigMap `devil-ghostty-web` from `ghostty-web/index.html`; one html file, ghostty-web from CDN, ttyd wire protocol) and running **real `login`**. Auth is bf PAM password (omni sops `login/devil`), not middleware.
    - Headless Service is required. Kata VM bypasses Cilium service translation both ways. ClusterIP never reaches VM. Clients use pod IP via Endpoints (pod-to-pod path that works).
    - PVC renamed `devil-state` to `devil-pvc` (subPaths `home`/`ssh`). See migration runbook before tag (`.private/devil-pvc-rename.md`). Flux prune deletes old bound PVC and its data (running VM holds age key, omni clone, teleport identity). Steps: scale devil to `0`, create `devil-pvc` from manifest, busybox copy pod with `cp -a` and verify `du`, keep replicas at `0`, tag; prune deletes `devil-state` and manifest restores `replicas: 1`.
    - Remaining: owner keypair + secrets (omni `ssh/devil`, `login/devil`) to `nix build .#devil` to `docker import --platform linux/arm64` to push `latest` to infra tag to smoke tests (ssh from mac/ish, login at https://devil.internal).
- [ ] **atuin server** on cluster (omni already ships client).
- [ ] **Backup path**. Fix friend tailnet ACL (`autogroup:shared` to `100.96.72.126:3900`), smoke-test restic round-trip, then restore drill on forgejo PVC. **Gate for all data-bearing apps below.**
- [ ] **Fix grafana homepage API widget.**
- [ ] **LAN DNS cutover**. Router DHCP DNS to `10.10.20.153` (AGH), tailnet split DNS for `internal.`; retire hosts-file stopgaps.
- [ ] **Forgejo actions** (optional): CI runner so apex/whim repos can leave GitHub Actions.

### Web

- [ ] **apex: complete rework**. Rebuild site, not append. New structure and design. Include CV and blog. Comments come later (identity lane).

### omni: pre-reset parity (macbook reset gate)

- [ ] **Back up age key** (`~/.config/sops/age/keys.txt`). Do this before any transfer.
- [ ] **Zed settings to nix** (layout, theme, extensions). Keep global config minimal. Prefer per-project `.zed/settings.json`.
- [ ] **macOS defaults parity** via nix-darwin `system.defaults`: dock (autohide, show speed), finder (quittable), wallpaper, liquid-glass styling.
- [ ] **Brewfile parity**. Uncomment casks in use so reset restores app parity.
- [ ] FileVault is enabled manually during reset. It is not declarable via nix-darwin.

## NEXT: hardware

### Case + final assembly (gates samba)

- [ ] **Design rbpi case**. CAD to print to validate fit and clearance against HARDWARE.md stack (Pi + 52Pi B12 + Penta HAT + back-mounted Seeed + heatsinks + FFC routing).
- [ ] **Final assembly** per HARDWARE.md checklist (power module to PCIe chain/FFCs to fans to standoffs to multimeter check to power-on order).
- [ ] rbpi back up to **samba** (SATA drives via Penta HAT) + **storage planning** (what lives where, hostPath vs PVC).

### Razer Blade (technically independent: needs only oci + tailnet)

- [ ] Boot Talos media to maintenance mode. Add node to `talos/topf.yaml` with `schematicId: "@schematic.rzbl.yaml"` and real IP. Patches already exist (`patches/node/rzbl/`: NVMe install disk, sysctls, tailscale).
- [ ] Run `topf apply` to join. Verify join. Add node labels/taints + NVIDIA device plugin for GPU workloads.
- [ ] This unlocks THEN queue.

## THEN: unlocked by Blade

- [ ] **Immich** (`photos`, ML on GPU). Only after backup gate.
- [ ] ***arr + Jellyfin** (`prowlarr`/`sonarr`/`radarr`, `jellyfin`).
- [ ] **Copyparty** (`files`), **Dawarich**, **ppty**.
- [ ] **Ollama + Open WebUI** (GPU).

## LATER

- [ ] **Identity & SSO**. Research before commit:
    - Choose aggregator: authentik vs dex. Forgejo, grafana, blog will use OIDC.
    - Research atproto as primary identity: atproto OAuth is own profile, not plain OIDC. PDS in front of aggregator needs bridge, or atproto stays parallel flow. This decides if friends can use Google/Apple and atproto behind one door.
    - Then: forgejo OIDC, grafana OIDC, identity-gated blog comments.
- [ ] **Renovate**. Decide: GitHub App on this repo vs self-hosted against Forgejo.
- [ ] **Alerting**. Choose Alertmanager receiver (ntfy/Discord/Telegram); build grafana dashboards.
- [x] **Teleport teardown**. Done 2026-10-24 after friend demo: `infrastructure/teleport/` deleted, devil teleport mounts/secret/configmap + `dependsOn: teleport` removed, omni teleport unit + port `3022` + `TELEPORT_SESSION` prompt removed, AGENTS/README updated. Devil uses ssh `2222` + ghostty-web (ttyd + login).
- [ ] **Daytona** agent sandbox; opencode kata container (if not done with devil).
- [ ] **Macbook factory reset** to omni bootstrap (README runbook) to iterate; rice (sketchybar/yabai/etc.) lives here, post-reset.
- [ ] Upgrades: k8s `1.35.3` to `1.37` (`talosctl upgrade-k8s`), Talos patch bumps, local kubectl.

## SOMEDAY / ideas

XMPP (Prosody), Mumble, I2P, Yggdrasil, Reticulum, Meshtastic, wasmCloud, opengist, atproto ecosystem experiments (knot, spindle), flake exposes apps/tools (nvim, home), deeper nvf config.

## Whims workflow (standing)

Trying a language or framework is tier-3 whim. No git manifests, no planning, registry push = deploy:

```nu
kn service create <name> --image ghcr.io/bfeitknecht/<name>:<tag> --port <port> -n whimsy
kn service update <name> --image ghcr.io/bfeitknecht/<name>:<new-tag>   # use SHA/version tags, not :latest
```

Domain template is `{{.Name}}.0xbf.ch`. KSvc name sets subdomain. Pull secrets are on namespace default SA. Candidates: idea tracker, blog backend, any framework itch.

## PVC planning

| Service         | Node | PVC                                  |
| --------------- | ---- | ------------------------------------ |
| AdGuard Home    | rbpi | nvme? 1Gi                            |
| prometheus      | rbpi | nvme? 1Gi                            |
| gatus           | rbpi | nvme? 1Gi                            |
| renovate        | rbpi |                                      |
| Homepage        | rbpi |                                      |
| Forgejo         | rbpi | nvme                                 |
| ATProto PDS     | rbpi | nvme                                 |
| apex            | rbpi |                                      |
| atuin           | rbpi | small                                |
| devil           | rbpi | devil-pvc 20Gi (home, ssh host keys) |
| Immich          | rzbl |                                      |
| Copyparty       | rzbl |                                      |
| Dawarich        | rzbl |                                      |
| *arr + Jellyfin | rzbl |                                      |

## Conventions for every new application

- One directory per app in `kubernetes/applications/<category>/<app>/` with own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`. Set `dependsOn` only to what it needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; new app needs only HTTPRoute, never DNS entry. Exception: non-cluster LAN devices get explicit records in knot `internal.` zone (e.g. `router.internal` to router IP). No HTTPRoute, no Traefik, no internal CA.
- Tier discipline: tier 1 is pinned image, git-tagged; tier 2 is Keel-polled `:latest` with `spec.ignore` on image; tier 3 is `kn` in `whimsy`, never in this tree. Do not put Keel annotations on tier 1/tier 3.
