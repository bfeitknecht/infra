# Infrastructure Implementation Roadmap

This roadmap breaks down the setup of the hybrid Talos Linux Kubernetes cluster into explicit, sequential phases. The cluster runs its Control Plane on Oracle Cloud Infrastructure (OCI) and its Worker Node on a local Raspberry Pi 5.

---

## Phase 0: Prerequisites & Tooling Setup

- [x] Install local CLI dependencies on developer workstation:
    - `topf` (Talos Orchestrator by PostFinance)
    - `talosctl` & `kubectl`
    - `sops` & `age`
    - `flux` CLI
- [x] Generate an `age` key pair for secret encryption:
    - Store public key in `.sops.yaml` in repo root.
    - Keep private key secure locally for SOPS workflows.
- [x] Ensure domain `yourdomain.com` is delegated to Cloudflare DNS (Grey Cloud / Proxy Disabled).
- [x] Create a Cloudflare API Token with `DNS:Edit` permissions.

---

## Phase 1: Talos OS & Cluster Bootstrap

### 1.1 Control Plane (Oracle Cloud Infrastructure)

- [x] Download `oracle-arm64.qcow2` from Sidero Image Factory (`factory.talos.dev`).
- [x] Import `qcow2` image into OCI as a Custom Image (Paravirtualized mode).
- [x] Provision OCI Ampere A1 VM (12 GB RAM, 2 OCPUs) running native Talos Linux.
- [x] Configure `talos/topf.yaml` (cluster `infra`, endpoint `https://140.238.210.235:6443`) and `talos/patches/` (`all/` hostname template; `control-plane/` DHCP networking, cert SANs, install disk).
- [x] Apply configuration using `topf apply --auto-bootstrap`.

### 1.2 Worker Node (Raspberry Pi 5)

- [ ] Generate Pi 5 Talos Linux raw image from Image Factory with PCIe/SATA system extensions.
- [ ] Flash image to Pi 5 SD card and boot node.
- [ ] Configure `talos/patches/worker/rpi5.yaml`:
    - Enable PCIe Gen 3.0.
    - Mount NVMe/SATA HAT storage to `/var/mnt/storage`.
- [ ] Apply configuration using `topf apply` to join Pi 5 as a dedicated Worker Node.
- [ ] Verify node status with `kubectl get nodes -o wide`.

---

## Phase 2: FluxCD & Core Infrastructure

### 2.1 FluxCD Bootstrap

- [ ] Configure `kubernetes/flux/gotk-sync.yaml` with SemVer tag filtering (`spec.ref.semver: ">=1.0.0"`).
- [ ] Bootstrap FluxCD pointing to Tangled.sh Git repository.
- [ ] Create `sops-age` Secret in `flux-system` namespace containing the `age` private key for in-memory decryption.

### 2.2 Storage & CNI

- [ ] Deploy **Local Path Provisioner** configured to use `/var/mnt/storage` for persistent volumes.
- [ ] Deploy **Cilium CNI** in `kube-proxy` replacement mode (eBPF dataplane).

### 2.3 Load Balancing, Ingress & TLS

- [ ] Deploy **MetalLB** in Layer 2 mode:
    - Configure `IPAddressPool` targeting a reserved range on local LAN (`10.0.0.0/8`).
    - Configure `L2Advertisement` targeting the Pi 5 worker node.
- [ ] Deploy **Traefik Ingress Controller**:
    - Enable Traefik `IngressRoute` CRDs.
    - Configure public HTTPS entrypoint (`:443`) and Git SSH entrypoint (`:2222`).
- [ ] Deploy **cert-manager**:
    - Create SOPS-encrypted Secret with Cloudflare API token.
    - Create `ClusterIssuer` using `letsencrypt-prod` via Cloudflare DNS-01 challenge.
- [ ] Deploy **Tailscale Operator** and configure IP whitelist middleware for private routes.

---

## Phase 3: Core Platform Applications

Deploy platform workloads incrementally via Git tags (`v1.0.0`, `v1.1.0`, etc.):

### 3.1 Operations & Monitoring

- [ ] Deploy **Metrics Server**.
- [ ] Deploy **Homepage** dashboard.
- [ ] Deploy **Pi-hole** DNS.

### 3.2 Development & ATProto Ecosystem

- [ ] Deploy **Forgejo** (Git hosting & packages):
    - Expose HTTP via Traefik `IngressRoute`.
    - Expose Git SSH via Traefik `IngressRouteTCP` on port `2222`.
- [ ] Deploy **ATProto PDS** (Self-hosted Personal Data Server):
    - Configure persistent storage on NVMe PVC.
    - Expose public endpoint via Traefik `IngressRoute` and `cert-manager`.
- [ ] Deploy **wasmCloud**.

---

## Phase 4: Media, Storage & Utilities

- [ ] Deploy **Copyparty** & **Yarr**.
- [ ] Deploy **Immich** (Photo & Video management using NVMe/SATA storage).
- [ ] Deploy ***arr stack** (Sonarr, Radarr, Prowlarr) + **Jellyfin**.
- [ ] Deploy **Dawarich** (Location tracking).

---

## Phase 5: Planned Expansion

- [ ] Communication: **XMPP**, **Mumble**.
- [ ] Decentralized Mesh: **I2P**, **Yggdrasil**.
- [ ] AI Services (Offloaded to secondary GPU node when available): **Ollama**, **Opencode**, **Open WebUI**.
