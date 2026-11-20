# Roadmap

Status as of 2026-11-19. Three lanes: **infra** (this repo), **omni** (nix), **web** (apex, glob, exhib, whims). `.private/TODO.md` in each repo feeds this file. Owner steps to go live: `docs/OPERATIONS.md`.

## Where things stand

- **Cluster:** 3 nodes on Talos 1.14.6, K8s 1.37.2. Infra tag `v1.46.0`. Placement roles (AGENTS.md "Workload placement"): oci = control plane + DNS, rbpi = edge + always-on core + platform controllers (preferred), rzbl = GPU, bulk storage, Postgres apps, Kata agents.
- **Public:** apex `0xbf.ch` (v0.1.14; SSH TUI `ssh -p 2222 0xbf.ch` through the sshmux), glob `blog.0xbf.ch` (v0.1.1), exhib `gallery.0xbf.ch` (v0.5.7), forgejo `git.0xbf.ch` (git SSH on `22`, SSO), pds, atuin, jellyfin `stream.0xbf.ch`, immich `photos.0xbf.ch`, copyparty `files.0xbf.ch`, ntfy `notify.0xbf.ch`, authentik `auth.0xbf.ch`.
- **Internal:** AGH, knot/kresd, devil (Kata, SSH `2223`), *arr, qBittorrent (Proton VPN), Navidrome, Dawarich, Time Machine (`smb://10.10.20.145`), ollama (GPU), opencode (Kata + CNP + authentik), agent sandboxes (Agent Sandbox v1.0.11, warm pool 1), Renovate (weekly, rzbl).
- **Monitoring:** Grafana `grafana.internal` (home dashboard `0xbf`, authentik SSO), Gatus `status.internal`, Prometheus on rbpi, alerts to ntfy. Homepage off.
- **Backup:** relay runs. Garage on the friend NAS refuses `3900`. Nothing is backed up yet. Test data only until then.
- **Release:** every repo uses `just release` (infra: `just release X.Y.Z`, gates on `check` + `fmt --check`, pins the in-tree sshmux image).
- **Removed 2026-11-19:** browser (browsh over SSH): looked bad, cost RAM.

## NOW

- [ ] **Router:** WAN 2222 forward to rbpi for the sshmux; drop the dead `2223` rule.
- [ ] **Backup path:** friend fixes Garage on `3900`. Then restic round-trip, restore drill (forgejo), k8up Schedules for immich, copyparty, samba and the app databases. **Gate for real data.**
- [ ] **Go live with test data:** `docs/OPERATIONS.md` section 2 (Time Machine of echo first, router, ACL, Immich admin, ntfy).
- [ ] **Forgejo:** Actions + runner live. Push mirrors to GitHub when repos move to Forgejo.
- [ ] **devil home:** check that `~` is complete (an old VM overlapped the new pod for ~4 min once).

## NEXT

- [ ] **Music streaming:** Lidarr + Navidrome + qBittorrent live. Connect qBittorrent in Lidarr, Navidrome app on the phone; public `music.0xbf.ch` when wanted.
- [ ] Nix dev shells per repo from omni (`docs/OPERATIONS.md`, section 10). Host has no working `rustup` shim (`~/.cargo/bin` links dangle).
- [ ] **rbpi case** design + final assembly (HARDWARE.md).

### omni (details in omni/ROADMAP.md)

- [ ] **Flesh out omni:** Rex on devil is declared (personal server, client on every host); left: `nh os switch .#devil` in the pod. opencode on devil attached to the opencode web server (needs a CNP rule from `devil`).
- [ ] **MacBook Pro echo -> anti:** omni `docs/MIGRATION.md` lists what can move. Time Machine of echo first (`docs/OPERATIONS.md` section 2).

### omni: pre-reset parity (macbook reset gate)

- [ ] Back up age key (`~/.config/sops/age/keys.txt`).
- [ ] Zed settings to nix. macOS defaults (ready block in omni `docs/MIGRATION.md`). Brewfile parity.

## LATER

- [ ] Identity: atproto login source, Jellyfin SSO when the plugin supports 12.x.
- [ ] Tailscale autoApprovers for `tag:infra` routes (snippet in AGENTS.md, tailscale on nodes).

## Done (recent)

- [x] 2026-11-19 Immich public at `photos.0xbf.ch` (v1.46.0); browser removed (v1.45.0); Arachnidium dropped (v1.44.0); apex 0.1.12-0.1.14 (plain help, syndicate in projects, cursor and selection fixes); thyme 0.1.2 released (Universe PR #6452).
- [x] 2026-11-18 Port cutover (v1.42.x): git on `22`, sshmux on `2222`, devil on `2223`; `justfile` (check, fmt, release) + yamlfmt + CI format gate.
- [x] 2026-11-18 Mail via Proton SMTP (noreply@0xbf.ch) for authentik, Forgejo, PDS, Immich; authentik SSO for Immich, Dawarich, Navidrome and the admin tools; forgot-password flow.
- [x] 2026-11-18 qBittorrent over Proton VPN, Renovate live, ntfy with Alertmanager + Gatus alerts, omni ssh git.0xbf.ch port 2223.
- [x] 2026-11-18 Lidarr, Navidrome, Dawarich, Time Machine live; thyme history email rewrite (bundle in `.private/`).
- [x] 2026-11-17 Kubernetes 1.35.3 -> 1.36.6 -> 1.37.2; journey page + deck.
- [x] 2026-11-17 copyparty (files.0xbf.ch), Immich with GPU ML, Forgejo Actions + runner, agent sandbox slots (scripts/sandbox.nu).
- [x] 2026-11-17 monitoring v2 (curated dashboards, 0xbf home, Gatus, GPU exporter), Flux on rbpi, Forgejo landing /bf, apex one-line footer (0.1.9).
- [x] 2026-11-17 authentik admin with passkey, Forgejo SSO linked (grant_types fix v1.30.0), circle mark everywhere.
- [x] 2026-11-17 Agent Sandbox (v1.29.0), placement review (controllers prefer rbpi), atlas pan/zoom, copyparty hosts, release unification (apex, glob, thyme), exhib v0.5.6 (video pauses on navigation), apex v0.1.6 (Firefox freeze after new tab), apex v0.1.7 (Polyring, mobile nav + touch scroll, light cursor, iOS dvh).
- [x] 2026-11-17 authentik live + blueprints, Forgejo SSO + theme, Jellyfin public + branding, opencode in Kata with CNP + forward auth, Cilium `socketLB.hostNamespaceOnly`, devil clean stop.
- [x] 2026-11-16 rbpi storage migration, rzbl workloads (media), GPU plugin, relay fix, thyme on Typst Universe, Zyxel `2223`.
- [x] 2026-11-15 Talos 1.14.6 on all nodes, rzbl join, Traefik pinned to rbpi, SSH ports (apex `22`, git `2223`), exhib live with one container.

## Projects (owner ideas, not scheduled)

- [ ] **radio.0xbf.ch** — internet radio. Music made with **Strudel** (live-coded patterns in the browser); the station plays recorded sets and the library (Navidrome). Likely Icecast + Liquidsoap on rzbl, public by purpose (`radio`).
- [ ] **exhib: playlist content type** (maybe) — a collection of tracks next to photos and writing, possibly fed by radio sets.
- [ ] **Second brain** — Obsidian as the editor; a public digital garden plus a private wiki of everything known. Vault in git on Forgejo; garden published as a static site (Quartz or thyme-based), wiki internal behind authentik.
- [ ] **Comments for blog and gallery** — own project (owner builds it), replaces the identity-rollout idea of third-party comments.

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

| Node | Path                     | Disk          | Users                                                                             |
| ---- | ------------------------ | ------------- | --------------------------------------------------------------------------------- |
| rbpi | `/var/mnt/storage-nvme0` | NVMe 256 GB   | agh, pds, atuin, devil, exhib                                                     |
| rbpi | `/var/mnt/storage-nvme1` | NVMe 250 GB   | forgejo                                                                           |
| rzbl | `/var/mnt/storage-nvme0` | NVMe 893 GB   | media configs, authentik db, ollama, opencode, immich db/models, dawarich, runner |
| rzbl | `/var/mnt/storage-ssd0`  | SATA SSD 4 TB | media library, immich photos, copyparty, Time Machine (class `local-path-ssd`)    |

## Conventions for every new application

- One directory per app in `kubernetes/applications/<category>/<app>/` with own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`. Set `dependsOn` only to what it needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; new app needs only HTTPRoute, never DNS entry. Exception: non-cluster LAN devices get explicit records in knot `internal.` zone (e.g. `router.internal` to router IP). No HTTPRoute, no Traefik, no internal CA.
- Tier discipline: tier 1 is pinned image, git-tagged; tier 2 is Keel-polled `:latest` with `spec.ignore` on image; tier 3 is `kn` in `whimsy`, never in this tree. Do not put Keel annotations on tier 1/tier 3.
