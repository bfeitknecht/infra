# Roadmap

Platform baseline is live: Flux reconciles the full tree (`storage → cilium → ipam`, `cert-manager → traefik → tailscale`, CRDs phase), the Gateway holds `10.10.20.128` from the Cilium LB-IPAM pool, certificates for `*.0xbf.ch` (Let's Encrypt) and `*.internal` (internal CA) are issued. What follows is application churn in smart order — each app is one directory, one Kustomization, one subdomain. Public vs internal exposure is decided per app by the owner, not in this document.

## Phase 1 — Backups to the friend's NAS (first, before real data exists)

Target: the friend's UGREEN NAS (DXP4800 Plus) on his LAN, reached over Tailscale. k8up (restic-based) backs up everything non-declarative — the local-path PVC data on the NVMe now, SATA SSDs later. Declarative state lives in git; secrets are backed up independently; etcd is deferred (the OCI control plane is trusted for now) but the destination is chosen so etcd backups can plug in later.

- [ ] **Network path:** friend runs Tailscale on the NAS (UGOS app or Docker container) and **shares the NAS node** to our tailnet (Tailscale admin → Share); accept the share. `rbpi` (already on the tailnet via `ext-tailscale`) then reaches the NAS at its `100.x` address — WireGuard-encrypted transport, no UGREEN Link cloud relay (that portal is for admin UI only, never backup traffic).
- [ ] **Destination backend — decision:**
    - **Garage (S3) in Docker on the NAS** — recommended: OSS, single binary, no GUI (AIStor is MinIO's paid successor; MinIO OSS itself is deprecated). Future-proof: the same endpoint later serves etcd backups (velero) — "plug into the UGREEN" as requested. Plain HTTP is fine over the tailnet (WireGuard wraps transport; restic encrypts at rest).
    - **SFTP** (UGOS SSH + limited user + key) — zero extra services on the NAS, restic-native, but no velero path later.
- [ ] **k8up operator:** HelmRepository `https://k8up-io.github.io/k8up`, HelmRelease `k8up` 4.10.0; CRDs via `cluster/crds.yaml` (GitRepository `k8up-io/k8up` @ `k8up-4.10.0`, path `./charts/k8up/crds`, `prune: false`).
- [ ] **Schedule CR:** nightly restic backup of all local-path PVCs with retention (e.g. 7 daily / 4 weekly / 3 monthly).
- [ ] SOPS secrets: restic repository password + S3 credentials (owner encrypts).

## Phase 2 — DDNS + DNS foundation

Public names need a DNS record pointing at the (dynamic) home IP; LAN names need a resolver.

- [ ] **DDNS updater** (`applications/utilities/ddns-updater/`): keeps the single apex A record `0xbf.ch` pointed at the current home IP — prerequisite for anything public on the domain. Cloudflare API token via SOPS. Never per-subdomain records: the wildcard cert covers `*.0xbf.ch`, Traefik routes subdomains by Host header.
- [ ] **Knot Resolver** (`applications/utilities/dns/`): LAN-only recursive resolver with DNSSEC validation enabled, wildcard local data for internal names → `10.10.20.128`. Never exposed publicly. Own LoadBalancer IP from the ipam pool (DNS is not HTTP — no Gateway involvement).
- [ ] Point devices at it (router DHCP or manual), retire any hosts-file stopgaps.
- [ ] **Pi-hole** (`applications/utilities/pihole/`): LAN-only ad-blocking DNS, forwarding to Knot (Knot stays the recursive/validating resolver, Pi-hole is not the sole resolver). Decision on ordering: Pi-hole first as the LAN-facing resolver with Knot behind it, or Knot first and Pi-hole later.

## Phase 3 — Forgejo (high priority)

The sooner this is live, the sooner git is self-hosted — `git.0xbf.ch` once Phase 2 DDNS + exposure are in place.

- [ ] Scaffold `applications/` tree + first entries in `cluster/applications.yaml`.
- [ ] Forgejo with SQLite, everything under one `/data` PVC — no Postgres unless it ever outgrows (CloudNativePG would be the escape hatch).
- [ ] HTTPRoute + subdomain (exposure: owner decides).
- [ ] SMTP relay for outgoing mail.
- [ ] Decision: git-over-SSH — Gateway `TCPRoute` (needs Traefik `experimentalChannel`), dedicated LoadBalancer port, or HTTPS-only to start.
- [ ] Admin hardening: registration policy, root user, SSH keys.

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
- [ ] **ATProto PDS** — `pds` (public per owner decision).

## Phase 8 — Platform & someday

- [ ] Decision: public exposure mechanism for public apps — home-router port-forward + DDNS (Phase 2 covers the DDNS half), Tailscale Funnel, or an OCI-side ingress. Gates every public app.
- [ ] Observability: metrics-server, kube-prometheus-stack, Gatus + alerting.
- [ ] Kubernetes 1.35 → 1.37 (`talosctl upgrade-k8s`), Talos 1.14.0 → 1.14.1, local kubectl upgrade.
- [ ] Tailscale subnet route from the worker (off-LAN access without DNS gymnastics).
- [ ] Dex (OIDC) for SSO across Forgejo/Grafana.
- [ ] Ollama + Open WebUI (GPU via the Blade).
- [ ] XMPP (Prosody), Mumble, I2P, Yggdrasil.

## Conventions for every new application

- One directory per app under `kubernetes/applications/<category>/<app>/` with its own `kustomization.yaml`.
- One Kustomization entry in `cluster/applications.yaml`, `dependsOn` only what it actually needs (usually `traefik`).
- Exposure via `HTTPRoute` (Gateway API only); secrets via SOPS; storage via local-path PVCs.
- DNS: one apex record + wildcard cert; adding an app means adding an HTTPRoute, never a DNS entry.
