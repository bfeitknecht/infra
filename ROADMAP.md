# Roadmap

Status as of 2026-11-25. Three lanes: **infra** (this repo), **omni** (nix), **web** (apex, glob, exhib, whims). `.private/TODO.md` in each repo feeds this file. Owner steps: `docs/OPERATIONS.md` and the atlas "Needs you"; day-to-day use: `docs/GUIDE.md`; where things run: `README.md`.

## Where things stand

- **Cluster:** 3 nodes on Talos 1.14.6, K8s 1.37.2, all Ready. Infra tag `v1.91.0`, every Flux Kustomization and HelmRelease ready, Gatus 35/35 green. Load: rbpi ~28 % RAM, rzbl ~54 %, oci ~36 %.
- **Git:** Forgejo `git.0xbf.ch` is primary for the six repos; push mirrors to GitHub carry commits and tags to CI. CI runs on GitHub only (Forgejo workflows removed 2026-11-25; the runner is idle). Bots: `opencode`, `renovate`.
- **Public:** apex `0xbf.ch` (0.1.20, brand palette), glob `blog.0xbf.ch` (0.1.7; 0.1.8 waits for thyme 0.2.0 on Universe), exhib `gallery.0xbf.ch` (0.7.0, curated photo metadata live), forgejo (SSO only), pds, atuin, jellyfin `videos`, immich `photos`, copyparty `files`, navidrome `music`, dawarich `locations`, ntfy, authentik.
- **Internal:** AGH, knot/kresd, devil (Kata NixOS VM, Tailscale SSH `ssh bf@devil`, Rex node `deviler`), *arr, qBittorrent (Proton VPN), Time Machine, ollama (GPU), opencode (Nix image in Kata, bubblewrap sandbox), Renovate.
- **Backup:** works again since 2026-11-25 (NAS on a new tailnet IP, v1.93.0; bucket back). First snapshot: atuin. Nightly schedules: atuin, authentik, forgejo, pds. Restore drill not done yet.
- **thyme:** 0.2.0 waits in Universe PR typst/packages#6496; then glob 0.1.8.

## NOW

- [ ] **Next push: echo -> anti** (factory reset, apply omni). Runbook and decisions: omni `docs/RESET.md`. Gate: the age key is off the Mac (it decrypts omni and infra; `talos/talosconfig` and `kubeconfig` regenerate from it).
- [ ] **Backup path:** bucket and relay fixed (2026-11-25, manual atuin snapshot OK). Left: watch the first green nightly, restore drill (forgejo), k8up Schedules for immich, copyparty, samba, exhib and the app databases. **Gate for real data.**
- [ ] **CLI logins** by hand on devil and anti: `gh`, `tea`, `glab` (atlas `cli-logins`).
- [ ] **Dawarich phone setup:** app on `locations.0xbf.ch` with the API key; then the agent sets `ALLOW_EMAIL_PASSWORD_LOGIN=false` (atlas `dawarich-phone`).
- [ ] **darwin switch:** first `nh darwin switch` on anti (part of echo -> anti).
- [ ] **thyme 0.2.0:** wait for Universe PR typst/packages#6496, then tag glob 0.1.8.
- [x] **authentik passkey:** recover with `docs/GUIDE.md` section 1; add TOTP + static codes so one broken passkey never locks you out.
- [x] **Go live with test data:** `docs/OPERATIONS.md` section 2: Time Machine of echo, Tailscale ACL autoApprovers, Immich admin (not created yet: `immich.internal`), ntfy app, Dawarich email.
- [x] **Forgejo cleanup:** delete tokens `repo-migration`, `repo-migration-2`. Your Forgejo email is the ETH student address: move it to an address that outlives your studies.
- [x] **thyme 0.1.3 merged:** bump glob and apex.

## Audit findings (2026-11-25)

After the reset, development moves to devil (`ssh bf@devil`, repos in `~/Projects`); anti is no longer a dev machine.

- [x] **Renovate works** (2026-11-25): a manual run found 283 dependencies and opened the Dependency Dashboard (issue #1, 30 updates waiting for Monday); a run with the schedule lifted opened PR #2 (Talos 1.14.7) and #3 (patch group). Review both: #3 bumps the k8up chart without its CRD tag in `cluster/crds.yaml`. Why the Monday runs never got that far is unknown (logs gone); watch the next one.
- [ ] **API timeouts from home to oci** (`100.73.186.19:6443` over Tailscale): ~150 five-second timeouts from rbpi in 20 h; the API server answers in < 0.1 s, so it is the path. k8up restarted 19 times in 32 h (lost leader lease).
- [ ] **rbpi -> rzbl kubelet (`10.10.20.11:10250`) partly over Tailscale**, not the LAN. Looks like the route-hijack trap: check rbpi's `RoutingRuleConfig` (priority 5200, `dst 10.10.0.0/16 table main`).
- [ ] **Rex node `deviler` ran over the DERP relay in Frankfurt.** 2026-11-25 after the devil restart: direct (`31.164.81.63`). Drop if it stays direct.
- [x] **Leftovers:** two `Completed` authentik pods and 18 failed k8up Jobs from the Garage outage deleted (2026-11-25).
- [ ] **forgejo-runner is idle** since CI moved to GitHub only: keep it for later or remove `applications/forgejo-runner/` and turn off `[actions]`.
- [ ] **podman on devil:** undecided (omni SOMEDAY).
- [x] Duplicate CI: Forgejo workflows removed from all repos; GitHub runs CI.
- [x] Merged fork branches `thyme-0.1.0`...`0.1.3` deleted.

## NEXT

- [x] **Rex over the tailnet:** declared in omni (`services.rex.tailscale`, node `devil`, owner-only). Left: `nh os switch` on devil, open the sign-in link from `rex server status`, disable key expiry on the node, then on the iPhone add `https://devil.tailac5960.ts.net`.
- [ ] **Music streaming:** connect qBittorrent in Lidarr, Navidrome app on the phone; (`music.0xbf.ch` is public since 2026-11-23).
- [ ] Nix dev shells per repo from omni (`docs/OPERATIONS.md`, section 10). Host has no working `rustup` shim.
- [ ] glob post descriptions (wording).
- [ ] **rbpi case** design + final assembly (`docs/HARDWARE.md`).

### omni (details in omni/ROADMAP.md)

- [ ] **MacBook Pro echo -> anti:** now in NOW. Runbook `docs/RESET.md`, inventory `docs/MIGRATION.md`.

## LATER

- [ ] Identity: atproto login source.

## Done (recent)

- [x] 2026-11-20 devil browser terminal removed (v1.58.0); 89 merged branches deleted across the repos.
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
