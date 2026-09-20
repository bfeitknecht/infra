# Infra

## Summary

Raspberry Pi running Talos Linux Kubernetes cluster.

### Hardware

- Raspberry Pi 5 (16GB RAM)
- 52Pi Double FPC PCIe HAT
- Seeed Studio Dual M.2 HAT
- Radxa Penta SATA HAT

### Infrastructure & Operations

- **CD & Automation:** Flux, Renovate, Kustomize
- **Secrets Management:** SOPS + age

### Network & Cluster

- **Networking & Ingress:** Cilium, Traefik, Tailscale, Cert-Manager + Cloudflare DNS-01 Challenge
- **Monitoring:** Metrics Server

### Applications

- **Development:** Forgejo, wasmCloud
- **Media & Storage:** Yarr, Copyparty, Immich, *arr + Jellyfin
- **Utilities & Dashboard:** Pi-hole, Knot, DDNS, Dawarich, Homepage

### Planned

- **Communication:** XMPP, Mumble
- **AI & Mesh:** Ollama, Opencode, Open WebUI, I2P, Yggdrasil
- **Miscellaneous**: Dex, ATProto PDS

### Repository Structure

```
.
├── README.md
├── ROADMAP.md
├── .sops.yaml                       # SOPS configuration (age public key)
│
├── talos/                          # Talos & topf OS Configurations
│   ├── topf.yaml                   # TOPF cluster definition & node mapping
│   ├── secrets.sops.yaml           # SOPS-encrypted cluster secrets bundle
│   └── patches/
│       ├── all/                     # HostnameConfig from topf node name
│       │   └── 01-hostname.yaml.tpl
│       ├── control-plane/           # OCI Cloud VM (10.20.20.10)
│       │   ├── 01-installation.yaml # UnattendedInstallConfig → /dev/sda
│       │   └── 02-network.yaml      # eth0 DHCP + cert SANs (public/private)
│       └── worker/                  # Pi Worker (10.10.20.10) — populated on arrival
│
└── kubernetes/                     # Flux GitOps Manifests
    ├── flux/                       # Flux controller bootstrap & tag filter
    │   └── gotk-sync.yaml
    ├── cluster/                    # High-level entrypoints
    │   ├── infrastructure.yaml
    │   └── applications.yaml
    ├── infrastructure/             # Platform Core
    │   ├── storage/                # Local Path Provisioner (/var/mnt/storage)
    │   ├── network/                # Cilium (LB Pool: 10.10.20.200-210), Tailscale
    │   └── ingress/                # Traefik (IngressRoute CRDs), cert-manager
    └── applications/               # User Workloads
        ├── dev/                    # Forgejo, ATProto PDS, wasmCloud
        ├── media/                  # Immich, Jellyfin, *arr, Copyparty, Yarr
        ├── utilities/              # Pi-hole, Homepage, Dawarich
        └── template/               # Blueprint for custom Dockerfile apps
            ├── kustomization.yaml
            └── app.yaml
```

### Network Model

Addressing follows `10.<location>.<function>.<host>` with `location = 10` for home and `location = 20` for cloud (eu-zurich-1).

Function zones use decade-based third octets.

| Zone | Home subnet   | OCI subnet    | Purpose                           |
| ---- | ------------- | ------------- | --------------------------------- |
| 10   | 10.10.10.0/24 | 10.20.10.0/24 | Infrastructure, routers, DNS, VPN |
| 20   | 10.10.20.0/24 | 10.20.20.0/24 | Kubernetes nodes and compute      |
| 30   | 10.10.30.0/24 | 10.20.30.0/24 | Storage and internal services     |
| 40   | 10.10.40.0/24 | 10.20.40.0/24 | Trusted LAN devices               |
| 50   | 10.10.50.0/24 | 10.20.50.0/24 | IoT and smart-home devices        |
| 60   | 10.10.60.0/24 | 10.20.60.0/24 | Guest and DMZ workloads           |

### Current Stack

| Layer        | Component                                             | Version             |
| ------------ | ----------------------------------------------------- | ------------------- |
| OS           | Talos Linux                                           | 1.14.0              |
| Kubernetes   | API server / kubelet                                  | 1.35.3              |
| GitOps       | Flux (source, kustomize, helm, notification)          | 2.9.5               |
| CNI          | Cilium (kube-proxy replacement, LB-IPAM, L2 announce) | 1.20.2              |
| Ingress      | Traefik via Gateway API                               | chart 41.6.0 (v3.7) |
| Gateway API  | standard channel CRDs                                 | 1.6.2               |
| Certificates | cert-manager                                          | 1.21.2              |
| Mesh / VPN   | Tailscale (operator in-cluster, extension on nodes)   | 1.102.3             |

### GitOps Delivery

Manifests are packaged as an OCI artifact and published to `ghcr.io/bfeitknecht/infra` by GitHub Actions on every `v*` tag. The `flux-system` OCIRepository tracks `semver >=1.0.0`, so pushing a tag is the only deployment mechanism — the cluster never reads the working tree or plain git.

```
git tag vX.Y.Z && git push origin master vX.Y.Z   # CI publishes, Flux reconciles
flux reconcile source oci flux-system             # optional: pull immediately
flux reconcile kustomization flux-system          # optional: apply immediately
```

### Kustomization Topology

```
cluster/crds.yaml            gateway-api-crds (v1.6.2), traefik-crds (v41.6.0)
                             ↑ pinned upstream GitRepository sources, prune: false

cluster/infrastructure.yaml  storage → cilium → ipam
                                     └────► cert-manager → traefik → tailscale
```

A Kustomization's server-side dry-run validates its whole manifest set before applying anything, so custom resources must never share a Kustomization with the HelmRelease that creates their CRDs. Cilium's CRDs are created by its operator at runtime (no upstream files exist), which is why the LB pool and L2 policy live in their own `ipam` Kustomization depending on `cilium`.

### Ingress & Certificates

- Traefik is the Gateway API implementation (`gatewayClassName: traefik`). Gateway listeners bind to the entrypoint ports 8000/8443; the LoadBalancer Service exposes 80/443.
- The Gateway address `10.10.20.128` comes from the Cilium LB-IPAM pool (`network/ipam`) and is L2-announced on the worker's `end0` interface.
- Public names (`0xbf.ch`, `*.0xbf.ch`) terminate with a Let's Encrypt wildcard certificate via Cloudflare DNS-01.
- Internal names (`*.internal`) terminate with a cert-manager internal CA (self-signed bootstrap → 10y CA → 1y wildcard certificate).
- Traefik dashboard: `https://dashboard.internal` (chart-managed IngressRoute, LAN allowlist middleware).

### Secrets

All secrets are SOPS-encrypted with age (`.sops.yaml`); Flux decrypts in-cluster using the `sops-age` key. In-repo secrets: `ghcr-pat` (OCI artifact pull), `cloudflare-dns01` (DNS-01 solver), `operator-oauth` (Tailscale operator), plus the Talos secrets bundle and node Tailscale patch under `talos/`.

### Access

- `kubeconfig` and `talosconfig` live in the repo root (gitignored).
- Off-LAN access runs over the tailnet: the nodes run the Tailscale system extension; advertise `10.10.20.0/24` from the worker node and approve the route in the Tailscale admin console.
- `dashboard.internal` (and every other `*.internal` name) resolves via the DNS stack: AdGuard Home (`10.10.20.153`, LAN-facing) → kresd (recursion + DNSSEC, ClusterIP `10.96.0.53`, in-cluster only) → knotd (authoritative `internal.` zone, wildcard → `10.10.20.128`; non-cluster devices get explicit records, e.g. `router.internal` → `10.10.10.1`). LAN: router DHCP DNS field → `10.10.20.153`. Off-LAN (tailnet): Tailscale split DNS, domain `internal.` → `10.10.20.153` (requires MagicDNS; reachable via the advertised subnet routes). Until the router field is set, a hosts entry remains the stopgap.
