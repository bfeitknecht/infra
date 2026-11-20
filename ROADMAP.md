# Roadmap

Status as of 2026-11-20. Three lanes: **infra** (this repo), **omni** (nix), **web** (apex, glob, exhib, whims). `.private/TODO.md` in each repo feeds this file. Owner steps: `docs/OPERATIONS.md`; day-to-day use: `docs/GUIDE.md`; where things run: `README.md`.

## Where things stand

- **Cluster:** 3 nodes on Talos 1.14.6, K8s 1.37.2, all Ready. Infra tag `v1.57.0`, every Flux Kustomization ready, Gatus 31/32 green (the red one is the Garage backup check). Load: rbpi ~45 % RAM, rzbl ~47 %, oci ~36 %.
- **Git:** Forgejo `git.0xbf.ch` is primary for the six repos; push mirrors to GitHub carry commits and tags to CI. Bots: `opencode` (agent VM), `renovate` (weekly, on Forgejo).
- **Public:** apex `0xbf.ch` (0.1.16, `/cv` behind Anubis, SSH TUI `ssh -p 2222 0xbf.ch`), glob `blog.0xbf.ch` (0.1.5), exhib `gallery.0xbf.ch` (0.5.8 with the web uploader), forgejo, pds, atuin, jellyfin `stream.0xbf.ch` (SSO), immich `photos.0xbf.ch`, copyparty `files.0xbf.ch` (SSO), ntfy, authentik.
- **Internal:** AGH, knot/kresd, devil (Kata, SSH `2223`, Rex server), *arr, qBittorrent (Proton VPN), Navidrome, Dawarich, Time Machine, ollama (GPU), opencode (Kata + CNP + bubblewrap sandbox), Renovate.
- **Backup:** relay runs; Garage on the friend NAS refuses `3900`. Nothing is backed up. Test data only.
- **thyme:** 0.1.3 (reading time left of the date) waits in Universe PR typst/packages#6463; then glob and apex move to it.

## NOW

- [ ] **Backup path:** friend fixes Garage on `3900`. Then restic round-trip, restore drill (forgejo), k8up Schedules for immich, copyparty, samba, exhib and the app databases. **Gate for real data.**
- [ ] **authentik passkey:** recover with `docs/GUIDE.md` section 1; add TOTP + static codes so one broken passkey never locks you out.
- [ ] **Go live with test data:** `docs/OPERATIONS.md` section 2: Time Machine of echo, Tailscale ACL autoApprovers, Immich admin (not created yet: `immich.internal`), ntfy app, Dawarich email.
- [ ] **Forgejo cleanup:** delete tokens `repo-migration`, `repo-migration-2`. Your Forgejo email is the ETH student address: move it to an address that outlives your studies.
- [ ] **Stale branches:** ~40 old feature and `arena/*` branches on GitHub and Forgejo (infra, apex). Say the word and the agent deletes the merged ones.
- [ ] **thyme 0.1.3 merged:** bump glob and apex.

## NEXT

- [ ] **Rex over the tailnet:** `services.rex.tailscale` on devil (own tailnet device, HTTPS), so the iPhone connects without an SSH key. Until then: SSH key from the app.
- [ ] **Music streaming:** connect qBittorrent in Lidarr, Navidrome app on the phone; public `music.0xbf.ch` when wanted.
- [ ] Nix dev shells per repo from omni (`docs/OPERATIONS.md`, section 10). Host has no working `rustup` shim.
- [ ] glob post descriptions (wording).
- [ ] **rbpi case** design + final assembly (HARDWARE.md).

### omni (details in omni/ROADMAP.md)

- [ ] **MacBook Pro echo -> anti:** anti host is minimal; omni `docs/MIGRATION.md` lists what can move. Time Machine of echo first.
- [ ] Back up age key (`~/.config/sops/age/keys.txt`) before any reset.
- [ ] Zed settings to nix, macOS defaults (ready block in MIGRATION.md), Brewfile parity.

## LATER

- [ ] Identity: atproto login source.

## Done (recent)

- [x] 2026-11-20 Forgejo primary with GitHub push mirrors, Renovate on Forgejo (v1.57.0); docs unified (OPERATIONS, GUIDE, README diagram); Anubis on `/cv` plain monochrome (v1.56.x); exhib web uploader (0.5.8, v1.55.0); glob links in the footer (0.1.5); thyme 0.1.3 PR; `.private` cleanup.
- [x] 2026-11-19 Jellyfin + copyparty SSO, opencode isolated with bubblewrap sandbox + Forgejo bot, agent sandboxes removed, Rex on devil, anti host in omni.
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
