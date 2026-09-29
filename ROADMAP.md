# Roadmap

Platform baseline is live: Flux reconciles the full tree (`storage → cilium → ipam`, `cert-manager → traefik → tailscale`, CRDs phase), the Gateway holds `10.10.20.128` from the Cilium LB-IPAM pool, certificates for `*.0xbf.ch` (Let's Encrypt) and `*.internal` (internal CA) are issued. What follows is application churn in smart order — each app is one directory, one Kustomization, one subdomain. Public vs internal exposure is decided per app by the owner, not in this document.

## Phase 1 — Backups to the friend's NAS (first, before real data exists)

Target: the friend's UGREEN NAS (DXP4800 Plus) on his LAN, reached over Tailscale. k8up (restic-based) backs up everything non-declarative — the local-path PVC data on the NVMe now, SATA SSDs later. Declarative state lives in git; secrets are backed up independently; etcd is deferred (the OCI control plane is trusted for now) but the destination is chosen so etcd backups can plug in later.

- [x] **Network path:** NAS on the tailnet at `dxp4800plus-brd.tail112719.ts.net` — WireGuard-encrypted transport, no UGREEN Link cloud relay (that portal is for admin UI only, never backup traffic).
- [x] **Destination backend — Garage (S3) in Docker on the NAS:** OSS, single binary, no GUI (AIStor is MinIO's paid successor; MinIO OSS itself is deprecated). Future-proof: the same endpoint later serves etcd backups (velero). Plain HTTP is fine over the tailnet (WireGuard wraps transport; restic encrypts at rest).
- [x] **k8up operator:** HelmRepository `https://k8up-io.github.io/k8up`, HelmRelease `k8up` 4.10.0 (operator v2.16.0); CRDs via `cluster/crds.yaml` (GitRepository `k8up-io/k8up` @ `k8up-4.10.0`, path `./charts/k8up/crds`, `prune: false`); schedules fire in `Europe/Zurich`; global S3/repo-password env vars on the operator so per-namespace Schedules need no backend block and no secret copies.
- [x] **Backup model — namespace-scoped, opt-in per app:** k8up backs up the PVCs of the namespace a Schedule lives in, nothing else. No Schedules exist today (monitoring/agh deliberately excluded); an app opts in by adding a Schedule to its own directory (snippet in README).
- [x] SOPS secrets: restic repository password + Garage S3 credentials (owner encrypts).
- [ ] **Smoke-test the endpoint:** bucket exists + credentials work + restic round-trip (README "Verifying the backup path"), after the next tag deploy.
- [ ] **Restore drill:** restore a real snapshot to a scratch location once a tier-1 app with a PVC exists.

## Phase 2 — DDNS + DNS foundation

Public names need a DNS record pointing at the (dynamic) home IP; LAN names need a resolver.

- [ ] **DDNS updater** (`applications/utilities/ddns-updater/`): keeps the single apex A record `0xbf.ch` pointed at the current home IP — prerequisite for anything public on the domain. Cloudflare API token via SOPS. Never per-subdomain records: the wildcard cert covers `*.0xbf.ch`, Traefik routes subdomains by Host header.
- [x] **Knot Resolver** (`applications/utilities/dns/`): LAN-only recursive resolver with DNSSEC validation enabled, never exposed publicly. Shipped as one pod: kresd (recursion + DNSSEC, ClusterIP `10.96.0.53`) + knotd (authoritative `internal.` zone, wildcard → `10.10.20.128`). kresd local-data cannot expand wildcards, so the zone is grafted via an authoritative stub (`forward: subtree: internal, authoritative: true, dnssec: false`) — the documented pattern for reserved TLDs.
- [ ] Point devices at it (router DHCP or manual), retire any hosts-file stopgaps.
- [x] **AdGuard Home** (`applications/utilities/agh/`, replaced Pi-hole): LAN-only ad-blocking DNS edge at `10.10.20.153` (static LB IP — inherited from Pi-hole, the router DHCP target must not float). Design: AGH forwards everything — including `.internal` — to kresd, which stubs the zone to knotd; no edge-side wildcard needed because AGH does not special-case the reserved TLD. Config seeded from `agh-config.sops.yaml`; admin UI at `agh.internal` via allowlisted HTTPRoute.

## Phase 3 — Forgejo (high priority)

The sooner this is live, the sooner git is self-hosted — `git.0xbf.ch` once Phase 2 DDNS + exposure are in place.

- [x] Scaffold `applications/forgejo/` + entry in `cluster/applications.yaml`.
- [x] Forgejo with SQLite, everything under one `/data` PVC — no Postgres unless it ever outgrows (CloudNativePG would be the escape hatch).
- [x] HTTPRoute + subdomain: `git.0xbf.ch`, public (`websecure` listener).
- [ ] SMTP relay for outgoing mail — Proton Premium custom domain + SMTP token (`smtp.protonmail.ch`) once Proton is live; mailer disabled until then.
- [x] Decision: git-over-SSH — Gateway `TCPRoute` (Traefik `experimentalChannel`, `gitssh` entrypoint hostPort 22 on rbpi; WAN 22 → git via router forward, no router SSH, the future dev box takes WAN 2222).
- [x] Admin hardening: registration disabled, admin bootstrapped from `forgejo-secrets.sops.yaml` on first boot.

## Phase 4 — Renovate (soon)

- [ ] Renovate keeping chart + CRD tag bumps flowing (pairs with the lockstep rule: chart version ↔ CRD tag).
- [ ] Decision: GitHub App on this repo now vs self-hosted Renovate against Forgejo once it is live.

## Phase 5 — Razer Blade worker node (higher medium)

A second worker unlocks the heavy stuff; the GPU is the point.

- [ ] Talos on the Razer Blade, join as worker (image with NVIDIA extensions).
- [ ] NVIDIA GPU operator / container toolkit for ML workloads.
- [ ] Node labels/taints so GPU workloads schedule there deliberately.
- [ ] Unlocks Immich ML acceleration; later Ollama.

## Phase 6 — Media & utilities

- [ ] Storage planning for the Pi SATA HAT disks (what lives where, hostPath vs PVC).
- [ ] **Immich** — `photos` (ML on the Blade once Phase 5 lands).
- [ ] **Jellyfin** — `jellyfin`.
- [ ] ***arr suite + Yarr** — `prowlarr`, `sonarr`, `radarr`, `yarr`.
- [ ] **Copyparty** — `files` (public per owner decision).
- [ ] **Dawarich** — `dawarich`.
- [ ] **Homepage** — `home`, dashboard linking everything as it lands.

## Phase 7 — Dev platforms (later)

- [ ] **wasmCloud** — `wasm` (public per owner decision).
- [x] **ATProto PDS** — `pds` (public; vanity handles `<name>.0xbf.ch` via well-known resolution, no per-account DNS).

## Phase 8 — Platform & someday

- [ ] Decision: public exposure mechanism for public apps — home-router port-forward + DDNS (Phase 2 covers the DDNS half), Tailscale Funnel, or an OCI-side ingress. Gates every public app.
- [ ] Observability: metrics-server, kube-prometheus-stack, Gatus + alerting.
- [ ] Kubernetes 1.35 → 1.37 (`talosctl upgrade-k8s`), Talos 1.14.0 → 1.14.1, local kubectl upgrade.
- [x] Tailscale subnet route from the worker (off-LAN access without DNS gymnastics) — `10.10.10.0/24` and `10.10.20.0/24` advertised from `rbpi`.
- [ ] Dex (OIDC) for SSO across Forgejo/Grafana.
- [ ] Ollama + Open WebUI (GPU via the Blade).
- [ ] XMPP (Prosody), Mumble, I2P, Yggdrasil.

## Conventions for every new application

- One directory per app under `kubernetes/applications/<category>/<app>/` with its own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`, `dependsOn` only what it actually needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; adding an app means adding an HTTPRoute, never a DNS entry. Exception: non-cluster LAN devices get explicit records in the knot `internal.` zone (e.g. `router.internal` → the router's own IP) — no HTTPRoute, no Traefik, no internal CA.
