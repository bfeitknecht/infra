# Roadmap

Status as of 2026-11-27. Three lanes: **infra** (this repo), **omni** (nix), **web** (apex, glob, exhib, whims). `.private/TODO.md` in each repo feeds this file. Owner steps: `docs/OPERATIONS.md` and the atlas "Needs you"; day-to-day use: `docs/GUIDE.md`; where things run: `README.md`.

## Where things stand

- **Cluster:** 3 nodes on Talos 1.14.6, K8s 1.37.2, all Ready. Infra tag `v1.100.0`. Load: rbpi ~29 % RAM, rzbl ~75 % (devil's Kata VM), oci ~37 %. opencode server gone (v1.98.0), Forgejo runner gone (v1.99.0).
- **Git:** Forgejo `git.0xbf.ch` is the origin for the six repos (apex, infra, thyme, glob, exhib, omni). Forgejo push mirrors carry commits and tags to GitHub. GitHub is the mirror and the CI runner (GHCR images, the OCI artifact, Typst releases). Forgejo Actions off; no Forgejo workflows in any repo. Bot: `renovate`.
- **Machines:** anti (MacBook, nix-darwin) is the daily driver since 2026-11-25; echo is retired. devil (Kata NixOS VM on rzbl) is the dev box: Tailscale SSH `ssh bf@devil`, Rex over `ssh://devil`, the agents run there.
- **Public:** apex `0xbf.ch` (0.1.20), glob `blog.0xbf.ch` (0.1.7; 0.1.8 waits for thyme 0.2.0 on Universe), exhib `gallery.0xbf.ch` (0.7.0), forgejo (SSO only), pds, atuin, jellyfin `videos`, immich `photos`, copyparty `files`, navidrome `music`, dawarich `locations`, ntfy, authentik.
- **Internal:** AGH, knot/kresd, devil, *arr, qBittorrent (Proton VPN), Time Machine, ollama (GPU), Renovate.
- **Backup:** works since 2026-11-25 (NAS on a new tailnet IP, v1.93.0). Nightly (green since 2026-11-26): atuin, authentik, forgejo, pds. Restore drill not done.
- **thyme:** 0.2.0 waits in Universe PR typst/packages#6496; then glob 0.1.8.

## NOW

- [ ] **Backup path:** nightlies green since 2026-11-26 (atuin, authentik, forgejo, pds). Left: restore drill (forgejo), k8up Schedules for immich, copyparty, samba, exhib and the app databases. **Gate for real data.**
- [ ] **Age key backup** off the Mac (omni NOW). It decrypts omni and infra; `talos/talosconfig` and `kubeconfig` regenerate from it.
- [ ] **CLI logins** by hand: `gh`, `tea`, `glab` on devil; `gh`, `tea` on anti (atlas `cli-logins`).
- [ ] **opencode leftovers:** delete the Forgejo bot `opencode` and the GHCR package `opencode` (atlas `opencode-gone`). Namespace, PVC and qemu are gone (checked 2026-11-27).
- [ ] **Dawarich phone setup:** app on `locations.0xbf.ch` with the API key; then the agent sets `ALLOW_EMAIL_PASSWORD_LOGIN=false` (atlas `dawarich-phone`).
- [ ] **Time Machine on anti:** add the disk (atlas `timemachine-mac`).
- [ ] **thyme 0.2.0:** wait for Universe PR typst/packages#6496, then tag glob 0.1.8.

## Audit findings (2026-11-25)

- [x] **API timeouts from home to oci** (2026-11-27): tailscaled used the `cilium_host` IP (pod CIDR) as a path; it loops through Cilium VXLAN over Tailscale and stalled ~7 s every 1-2 min. etcd was fast (all lease writes < 0.4 s). Fixed with Talos rule 5190 (`talos/patches/all/04-tailscale-loop.yaml`) on all nodes. Watch k8up restarts and the apiserver lease 504 count.
- [ ] **rbpi -> rzbl kubelet (`10.10.20.11:10250`) partly over Tailscale**, not the LAN. Looks like the route-hijack trap: check rbpi's `RoutingRuleConfig` (priority 5200, `dst 10.10.0.0/16 table main`).
- [ ] **Renovate Monday runs:** a manual run works (Dependency Dashboard issue #1, PRs #2 Talos 1.14.7, #3 patch group). Watch the next scheduled run.
- [ ] **devil rollout hangs:** a Kata stop can hang with the guest up (v1.92.0, again v1.98.0: Terminating for hours). The fix is `ssh bf@devil sudo systemctl poweroff`. Find the cause (qemu stop timeout, agent shutdown).
- [ ] **podman on devil:** undecided (omni SOMEDAY).

## NEXT

- [ ] **Music streaming:** connect qBittorrent in Lidarr, Navidrome app on the phone (`music.0xbf.ch` is public since 2026-11-23).
- [ ] Nix dev shells per repo from omni (`docs/OPERATIONS.md`, section 10).
- [ ] glob post descriptions (wording).
- [ ] **rbpi case** design + final assembly (`docs/HARDWARE.md`).

### omni (details in omni/ROADMAP.md)

- [ ] Rice on anti, one piece per `nh darwin switch` (tiling, bar, borders, launcher, keys, look).
- [ ] Rex on the phone over `ssh://bf@devil`; then delete the Tailscale node `iotar`.

## LATER

- [ ] Identity: atproto login source.

## Done (recent)

- [x] 2026-11-27 Forgejo runner out of the tree (namespace, PVC, Kustomization, secret) and Forgejo Actions off (seed and live `app.ini`): Forgejo is the origin, GitHub the mirror and CI (v1.99.0). No Forgejo workflows in any repo, all branches checked.
- [x] 2026-11-27 Rex over Tailscale SSH: the Rex nodes `deviler`, `antir` are gone; clients use `ssh://devil` and `ssh://anti`. anti runs the open-source tailscaled (`tag:anti`).
- [x] 2026-11-25 echo -> anti: anti is the daily driver (omni RESET and MIGRATION runbooks retired 2026-11-27).
- [x] 2026-11-25 Duplicate CI gone: Forgejo workflows removed from all repos; merged fork branches `thyme-0.1.0`...`0.1.3` deleted; Renovate works on Forgejo.
- [x] 2026-11-25 authentik passkey recovery, go-live with test data, Forgejo token cleanup, thyme 0.1.3 in glob and apex.
- [x] 2026-11-27 opencode server out of the tree (app, cert name, authentik objects absent, image and CI step, release pin check): rzbl memory; the agents run on devil. Live in v1.98.0, with k8up 4.10.1 and the CRD tag check in `just check`; devil 3Gi/5Gi. Atlas and journey current as of v1.97.0.

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
| rbpi | `/var/mnt/storage-nvme0` | NVMe 256 GB   | agh, pds, atuin, ntfy, exhib, monitoring                                          |
| rbpi | `/var/mnt/storage-nvme1` | NVMe 250 GB   | forgejo                                                                           |
| rzbl | `/var/mnt/storage-nvme0` | NVMe 893 GB   | media configs, authentik db, ollama, devil, immich db/models, dawarich           |
| rzbl | `/var/mnt/storage-ssd0`  | SATA SSD 4 TB | media library, immich photos, copyparty, Time Machine (class `local-path-ssd`)    |

## Conventions for every new application

- One directory per app in `kubernetes/applications/<category>/<app>/` with own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`. Set `dependsOn` only to what it needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; new app needs only HTTPRoute, never DNS entry. Exception: non-cluster LAN devices get explicit records in knot `internal.` zone (e.g. `router.internal` to router IP). No HTTPRoute, no Traefik, no internal CA.
- Tier discipline: tier 1 is pinned image, git-tagged; tier 2 is Keel-polled `:latest` with `spec.ignore` on image; tier 3 is `kn` in `whimsy`, never in this tree. Do not put Keel annotations on tier 1/tier 3.
