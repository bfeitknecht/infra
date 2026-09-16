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

- **Networking & Ingress:** Cilium, MetalLB, Traefik, Tailscale, Cert-Manager + Cloudflare DNS-01 Challenge
- **Monitoring:** Metrics Server

### Applications

- **Development:** Forgejo, wasmCloud
- **Media & Storage:** Yarr, Copyparty, Immich,d *arr + Jellyfin
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
│   ├── talsecret.sops.yaml         # SOPS-encrypted cluster secrets bundle
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
