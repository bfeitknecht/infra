# Cluster Bootstrapping & Provisioning Overview

## Core Objective

Bootstrap a hybrid Kubernetes cluster using **Talos Linux** with:

- **Control Plane Node:** OCI Zurich (`10.20.20.10`, Public IP `140.238.210.235`).
- **Worker Node:** Raspberry Pi 5 (`10.10.20.10`).
- **Tooling Stack:** `topf` (for cluster/patch orchestration), `talosctl` (for bootstrap/API interaction), `sops` + `age` (for secret encryption), and `flux` (for GitOps delivery).

---

## Targeted Repository Structure

```text
.
├── README.md
├── ROADMAP.md
├── .sops.yaml                       # SOPS configuration (age public key)
│
├── talos/                          # Talos & topf OS Configurations
│   ├── topf.yaml                   # TOPF cluster definition & node mapping
│   ├── talsecret.sops.yaml         # SOPS-encrypted cluster secrets bundle
│   └── patches/
│       ├── all/                     # Applied to all nodes
│       │   └── 01-hostname.yaml.tpl # HostnameConfig from topf node name
│       ├── control-plane/           # Applied to OCI Cloud VM (10.20.20.10)
│       │   ├── 01-installation.yaml # UnattendedInstallConfig → /dev/sda
│       │   └── 02-network.yaml      # eth0 DHCP + cert SANs (public/private)
│       └── worker/                  # Applied to Pi Worker (10.10.20.10) — populated on arrival
│
└── kubernetes/                     # Flux GitOps Manifests
    ├── flux/                       # Flux controller bootstrap & tag filter
    │   └── gotk-sync.yaml
    ├── cluster/                    # High-level entrypoints
    │   ├── infrastructure.yaml
    │   └── applications.yaml
    ├── infrastructure/             # Platform Core
    │   ├── storage/                # Local Path Provisioner (/var/mnt/storage)
    │   ├── network/                # Cilium, MetalLB (Pool: 10.10.20.200-210), Tailscale
    │   └── ingress/                # Traefik (IngressRoute CRDs), cert-manager
    └── applications/               # User Workloads
        ├── dev/                    # Forgejo, ATProto PDS, wasmCloud
        ├── media/                  # Immich, Jellyfin, *arr, Copyparty, Yarr
        ├── utilities/              # Pi-hole, Homepage, Dawarich
        └── template/               # Blueprint for custom Dockerfile apps
            ├── kustomization.yaml
            └── app.yaml
```

---

## Agent Operational Sequence

### Phase 1: Secrets & TOPF Configuration

1. **Secrets Initialization:**
    - Use `sops` with your `age` key (defined in `.sops.yaml`).
    - Generate the secret bundle via `talosctl gen secrets -o talos/talsecret.sops.yaml` and encrypt it using `sops -e -i`.

2. **Patch Architecture (topf scope layers: `all/` → `<role>/` → `node/<host>/`):**
    - **`talos/patches/all/01-hostname.yaml.tpl`:** Sets each node's hostname from its topf node name via `HostnameConfig`.
    - **`talos/patches/control-plane/01-installation.yaml`:** Install disk via `UnattendedInstallConfig` (Talos ≥ 1.14) targeting `/dev/sda`, `wipe: false`.
    - **`talos/patches/control-plane/02-network.yaml`:** DHCP on `eth0` (OCI VNIC) and machine cert SANs (`140.238.210.235`, `10.20.20.10`).
    - **`talos/patches/worker/…`:** Populated when the Pi 5 arrives (PCIe 3.0, storage mounts under `/var/mnt/storage`; `rpi5-worker` hostname comes free from the `all/` template).
    - **CNI:** Default flannel is kept for bootstrap; a patch setting `cluster.network.cni.name: none` is added only once Cilium is deployed via Flux.

3. **TOPF Definition (`talos/topf.yaml`):**
    - Declare cluster metadata (`infra`), network endpoint (`https://140.238.210.235:6443`), `secretsPath` → SOPS bundle, and node maps linking IPs to their roles (`control-plane`/`worker`) with per-node platform overrides (`oracle` vs `metal`).

---

### Phase 2: OCI Control Plane Bootstrap

1. **Configuration Application:**
    - Execute `topf apply` (or `talosctl apply-config --insecure`) targeting the OCI node (`140.238.210.235`).
    - Allow Talos to process the patch stack, apply static settings, and reboot out of maintenance mode.

2. **`talosctl` Client Sync:**
    - Configure local `talosconfig` to set `endpoints` and `nodes` to the public OCI address.

3. **Cluster Bootstrap:**
    - Execute `talosctl bootstrap` against the OCI controller node to trigger single-node `etcd` initialization.
    - Monitor health using `talosctl health` until the Kubernetes API server responds on port `6443`.

4. **Kubeconfig Retrieval:**
    - Fetch the cluster admin kubeconfig (`talosctl kubeconfig`) and verify control plane node registration (`kubectl get nodes`).

---

### Phase 3: Local Pi 5 Worker Onboarding

1. **Flash & Mount Preparation:**
    - Flash the Pi 5 SD card with Talos ARM64 image (including required PCIe system extensions).
    - Ensure HAT hardware is attached.

2. **Node Join Execution:**
    - Execute `topf apply` targeting the local worker node (`10.10.20.10`).
    - The Pi 5 receives `rpi5.yaml` patches, formats/mounts storage under `/var/mnt/storage`, and joins the OCI control plane over the network.
    - Verify cluster membership: `kubectl get nodes -o wide`.

---

### Phase 4: FluxCD GitOps Transfer

1. **Repository Setup:**
    - Push repository state to **Tangled.sh**.

2. **Flux Bootstrap:**
    - Initialize FluxCD watching `kubernetes/flux/gotk-sync.yaml`.
    - Configure Flux source controller with **SemVer tag filtering** (`>=1.0.0`) so reconciliation is strictly tag-driven.
    - Inject the `age` private key as a Kubernetes Secret (`sops-age`) into `flux-system` to allow Flux to decrypt in-repo SOPS secrets natively.

3. **Reconciliation Sequence:**
    - **Order of Execution:** Storage Provisioner $\rightarrow$ Cilium CNI $\rightarrow$ MetalLB (LAN Pool `10.10.20.200-210`) $\rightarrow$ Traefik Ingress & `cert-manager` (Cloudflare DNS-01) $\rightarrow$ Tailscale $\rightarrow$ Tenant Applications (Forgejo, ATProto PDS, Immich, etc.).

---

## Key Constraints & Guardrails

- **No Direct Master Writes:** The OCI control plane is tainted; user workloads run exclusively on the Pi 5 worker node.
- **Tag-Driven Deployments:** Pushing commits to `main` must **not** trigger Flux deployment; releases require a Git tag push (`v1.0.0`).
- **No Annotations Ingress Hacks:** All Traefik routing rules must use native `IngressRoute` / `IngressRouteTCP` CRDs.
- **Zero Cloudflare Proxying:** Cloudflare records must remain **Grey Cloud (DNS Only)** to prevent proxy rate limits and allow direct TLS termination.
