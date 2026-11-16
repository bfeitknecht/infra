# Roadmap

Status as of 2026-11-16. Three lanes: **infra** (this repo), **omni** (nix), **web** (apex, glob, exhib, whims). `.private/TODO.md` in each repo feeds this file.

## Where things stand

- **Cluster:** 3 nodes on Talos 1.14.6, K8s 1.35.3. `oci` control plane, `rbpi` (Pi 5) and `rzbl` (Razer Blade, GTX 1660 Ti) workers. Infra tag `v1.20.0`.
- **rzbl joined 2026-11-15.** Talos on USB stick, `/var` on NVMe, NVMe + 4 TB SSD as user volumes. Direct tailnet path to oci (rule 5200 + own `/32` route). GPU via NVIDIA device plugin (`nvidia.com/gpu: 1`).
- **rbpi storage migrated** to `ExistingVolumeConfig` (`/var/mnt/storage-nvme0|1`). Data kept in place.
- **Public apps live:** apex `0xbf.ch` (site), exhib `gallery.0xbf.ch` (6 collections uploaded), forgejo `git.0xbf.ch` (SSH `2223`), pds, atuin.
- **Internal apps live:** AGH, knot/kresd, homepage, devil, jellyfin (GPU), sonarr, radarr, prowlarr, ollama (GPU, qwen2.5-coder:7b, cluster-internal). GPU is time-sliced (4 slots).
- **Prepared, suspended** (wait for owner secrets, see `docs/RZBL_WORKLOADS.md`): immich, dawarich, copyparty, Time Machine (`10.10.20.145`), forgejo runner, opencode web, authentik (`auth.0xbf.ch`).
- **Broken on purpose until thyme is on Typst Universe:** glob (ImagePullBackOff), apex-tui SSH (CrashLoop).
- **Monitoring off** (Prometheus, Grafana, Gatus commented out). metrics-server stays.
- **Backup:** relay pod runs since 2026-11-16. Garage on friend NAS refuses `3900` on its tailnet IP. Nothing is backed up yet.

## NOW

- [ ] **Router:** Zyxel rule `2223/tcp` to `10.10.20.10:2223` (git SSH from WAN).
- [ ] **thyme on Typst Universe** (typst/packages#6393), then `just release v0.1.0` in glob and apex.
- [ ] **Secrets for prepared apps** (`docs/RZBL_WORKLOADS.md`), then un-suspend one by one.
- [ ] **Jellyfin public:** finish wizard at `jellyfin.internal`, then public HTTPRoute (name TBD).
- [ ] **Backup path:** friend fixes Garage bind on `3900`. Then restic round-trip, restore drill (forgejo), k8up Schedules for exhib, immich, media configs. **Gate for immich real use.**
- [ ] **Forgejo Actions:** enable `[actions]`, runner secret, push mirrors to GitHub.
- [ ] **Authentik** (decided): secret, un-suspend, own admin + passkey, then connect forgejo, immich, jellyfin (`docs/AUTHENTIK.md`).
- [ ] **Homepage:** remove grafana/gatus widgets from `homepage-services` (sops) while monitoring is off.

## NEXT

- [ ] **Download client** (qBittorrent) for *arr. Needs VPN decision.
- [ ] Immich ML `-cuda` image on a GPU slot.
- [ ] Open WebUI on top of Ollama (optional; opencode web covers coding).
- [ ] **rzbl keyboard** white: needs openrazer as custom Talos extension.
- [ ] **Renovate** + monitoring back (Prometheus, Grafana, Gatus, alerting receiver).
- [ ] **rbpi case** design + final assembly (HARDWARE.md).

### omni: pre-reset parity (macbook reset gate)

- [ ] Back up age key (`~/.config/sops/age/keys.txt`).
- [ ] Zed settings to nix. macOS defaults via nix-darwin. Brewfile parity.
- [ ] SSH config `Host git.0xbf.ch` with `Port 2223` (so `git@git.0xbf.ch:owner/repo` works).

## LATER

- [ ] Identity rollout (forgejo, jellyfin, immich OIDC; blog comments).
- [ ] Upgrades: k8s `1.35.3` to `1.37` (`talosctl upgrade-k8s`).
- [ ] Daytona agent sandbox; opencode kata container.
- [ ] Macbook factory reset to omni bootstrap.

## Done (recent)

- [x] 2026-11-16 rbpi storage migration, rzbl workloads (media), GPU plugin, relay fix (PodSecurity + state on PVC).
- [x] 2026-11-15 Talos 1.14.6 on all nodes, rzbl join, Traefik pinned to rbpi, SSH ports (apex `22`, git `2223`), exhib live with one container.
- [x] 2026-10-24 Teleport removed. Devil uses ssh `2222` + ghostty-web.

## SOMEDAY / ideas

XMPP (Prosody), Mumble, I2P, Yggdrasil, Reticulum, Meshtastic, wasmCloud, opengist, atproto ecosystem experiments (knot, spindle), flake exposes apps/tools (nvim, home), deeper nvf config.

## Whims workflow (standing)

Trying a language or framework is tier-3 whim. No git manifests, no planning, registry push = deploy:

```nu
kn service create <name> --image ghcr.io/bfeitknecht/<name>:<tag> --port <port> -n whimsy
kn service update <name> --image ghcr.io/bfeitknecht/<name>:<new-tag>   # use SHA/version tags, not :latest
```

Domain template is `{{.Name}}.0xbf.ch`. KSvc name sets subdomain. Pull secrets are on namespace default SA. Candidates: idea tracker, blog backend, any framework itch.

## PVC layout

| Node | Path | Disk | Users |
| --- | --- | --- | --- |
| rbpi | `/var/mnt/storage-nvme0` | NVMe 256 GB | agh, pds, atuin, devil, exhib |
| rbpi | `/var/mnt/storage-nvme1` | NVMe 250 GB | forgejo |
| rzbl | `/var/mnt/storage-nvme0` | NVMe 893 GB | media configs, immich db/models, dawarich, runner (class `local-path-nvme`) |
| rzbl | `/var/mnt/storage-ssd0` | SATA SSD 4 TB | media library, immich photos, copyparty, Time Machine (class `local-path-ssd`) |

## Conventions for every new application

- One directory per app in `kubernetes/applications/<category>/<app>/` with own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`. Set `dependsOn` only to what it needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; new app needs only HTTPRoute, never DNS entry. Exception: non-cluster LAN devices get explicit records in knot `internal.` zone (e.g. `router.internal` to router IP). No HTTPRoute, no Traefik, no internal CA.
- Tier discipline: tier 1 is pinned image, git-tagged; tier 2 is Keel-polled `:latest` with `spec.ignore` on image; tier 3 is `kn` in `whimsy`, never in this tree. Do not put Keel annotations on tier 1/tier 3.
