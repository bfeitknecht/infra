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
- **Backups:** k8up (restic) -> Garage S3

### Network & Cluster

- **Networking & Ingress:** Cilium, Traefik, Tailscale, Cert-Manager + Cloudflare DNS-01 Challenge
- **Monitoring:** kube-prometheus-stack, Metrics Server, Gatus

### Applications

- **Public:** apex site (Keel-polled `:latest`)
- **Utilities & Dashboard:** AdGuard Home, knotd + kresd (`.internal` zone), DDNS, Homepage

### Planned

- **Communication:** XMPP, Mumble
- **AI & Mesh:** Ollama, Opencode, Open WebUI, I2P, Yggdrasil, Reticulum, Meshtastic
- **Miscellaneous**: Dex, ATProto PDS

### Repository Structure

```
.
├── README.md
├── ROADMAP.md
├── .sops.yaml                       # SOPS configuration (age public key)
│
├── talos/                          # Talos OS config (declarative, applied with topf)
│   ├── topf.yaml                   # TOPF cluster definition; per-node schematicId
│   ├── schematic.<node>.yaml       # Image-factory schematics (extensions + SBC overlays)
│   ├── secrets.sops.yaml           # SOPS-encrypted cluster secrets bundle
│   └── patches/                     # merged in order: all/ -> <role>/ -> node/<host>/
│       ├── all/                     # cluster-wide: hostname, tailscale ext-config, CNI
│       ├── control-plane/           # oci: install disk (/dev/sda) + network/certSANs
│       └── node/                    # per-host: 01-install, 02-network, 03-tailscale, 04-storage
│
└── kubernetes/                     # Flux GitOps Manifests
    ├── flux/                       # Flux controller bootstrap & tag filter
    │   └── gotk-sync.yaml
    ├── cluster/                    # High-level entrypoints
    │   ├── crds.yaml               # Pinned upstream CRD installs (prune: false)
    │   ├── infrastructure.yaml     # Kustomization dependency tree
    │   └── applications.yaml       # Per-app Kustomizations
    ├── infrastructure/             # Platform Core
    │   ├── storage/                # Local Path Provisioner (/var/mnt/storage)
    │   ├── backup/                 # k8up (restic -> Garage S3)
    │   ├── keel/                   # Image updater (tier-2 :latest apps)
    │   ├── knative/                # Knative operator + Serving (tier-3 whims)
    │   ├── monitoring/             # kube-prometheus-stack, metrics-server, Gatus
    │   ├── teleport/               # Teleport CE access plane (own LB IP; devil's only door)
    │   ├── network/                # Cilium (LB-IPAM pool, L2 announce), Tailscale
    │   └── ingress/                # Traefik (Gateway API), cert-manager, Tailscale
    └── applications/               # User Workloads (one directory = one namespace)
        ├── apex/                   # Public site (Keel-polled :latest)
        ├── agh/                    # AdGuard Home (LAN DNS edge)
        ├── ddns/                   # favonia/cloudflare-ddns (0xbf.ch -> home IP)
        ├── dns/                    # knotd + kresd (the .internal zone)
        ├── devil/                  # Kata VM pod (ssh 2222 via TCPRoute, ghostty-web terminal at devil.internal; page source in ghostty-web/)
        ├── forgejo/                # Git forge (git.0xbf.ch, git-ssh via TCPRoute)
        ├── pds/                    # ATProto PDS (Bluesky; handles at <name>.pds.0xbf.ch)
        └── homepage/               # Dashboard
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

| Layer         | Component                                             | Version                         |
| ------------- | ----------------------------------------------------- | ------------------------------- |
| OS            | Talos Linux                                           | 1.14.2                          |
| Kubernetes    | API server / kubelet                                  | 1.35.3                          |
| GitOps        | Flux (source, kustomize, helm, notification)          | 2.9.5                           |
| CNI           | Cilium (kube-proxy replacement, LB-IPAM, L2 announce) | 1.20.2                          |
| Ingress       | Traefik via Gateway API                               | chart 41.6.0 (v3.7)             |
| Gateway API   | standard channel CRDs                                 | 1.6.2                           |
| Certificates  | cert-manager                                          | 1.21.2                          |
| Mesh / VPN    | Tailscale (operator in-cluster, extension on nodes)   | 1.102.3                         |
| Monitoring    | kube-prometheus-stack, metrics-server, Gatus          | 91.4.1 / 3.14.0 / v5.36.0       |
| Backups       | k8up (restic -> Garage S3)                            | chart 4.10.0 (operator v2.16.0) |
| Whim platform | Knative Serving via operator (scale-to-zero)          | 1.23.0 (operator 1.23.1)        |
| Access plane  | Teleport CE (standalone chart, TLS routing)           | 18.10.0                         |

### GitOps Delivery

Manifests are packaged as an OCI artifact and published to `ghcr.io/bfeitknecht/infra` by GitHub Actions on every `v*` tag. The `flux-system` OCIRepository tracks `semver >=1.0.0`, so pushing a tag is the only deployment mechanism — the cluster never reads the working tree or plain git.

```
git tag vX.Y.Z && git push origin master vX.Y.Z   # CI publishes, Flux reconciles
flux reconcile source oci flux-system             # optional: pull immediately
flux reconcile kustomization flux-system          # optional: apply immediately
```

### Kustomization Topology

```
cluster/crds.yaml            gateway-api-crds (v1.6.2), traefik-crds (v41.6.0),
                             prometheus-crds (kube-prometheus-stack 91.4.1),
                             k8up-crds (k8up-4.10.0), knative-operator-crds (v1.23.1)
                             ↑ pinned upstream GitRepository sources, prune: false

cluster/infrastructure.yaml  storage -> cilium -> ipam
                             cilium -> cert-manager -> traefik -> tailscale
                             k8up-crds -> backup
                             knative-operator-crds -> knative-operator -> knative-serving
                             keel, monitoring (dependsOn prometheus-crds + traefik)
```

A Kustomization's server-side dry-run validates its whole manifest set before applying anything, so custom resources must never share a Kustomization with the HelmRelease that creates their CRDs. Cilium's CRDs are created by its operator at runtime (no upstream files exist), which is why the LB pool and L2 policy live in their own `ipam` Kustomization depending on `cilium`.

### Ingress & Certificates

- Traefik is the Gateway API implementation (`gatewayClassName: traefik`). Gateway listeners bind to the entrypoint ports 8000/8443 plus TCP 22 (forgejo git-ssh `TCPRoute`) and TCP 2222 (devil ssh `TCPRoute`, LAN/tailnet only — no WAN forward); the LoadBalancer Service exposes 80/443/22/2222.
- The Gateway address `10.10.20.128` comes from the Cilium LB-IPAM pool (`network/ipam`) and is L2-announced on the worker's `end0` interface.
- Public names (`0xbf.ch`, `*.0xbf.ch`) terminate with a Let's Encrypt wildcard certificate via Cloudflare DNS-01.
- Internal names (`*.internal`) terminate with a cert-manager internal CA (self-signed bootstrap -> 10y CA -> 1y wildcard certificate).
- Traefik dashboard: `https://dashboard.internal` (chart-managed IngressRoute, LAN allowlist middleware).
- The ATProto PDS is routed at `pds.0xbf.ch` (API) and `*.pds.0xbf.ch` (handle resolution via `/.well-known/atproto-did`); custom-domain handles (e.g. the bare apex) resolve via DNS TXT records.
- Devil (kata VM pod): `devil.internal` serves the ghostty-web terminal (HTTPRoute → ttyd in the VM, a real `login` prompt is the auth) and ssh on port 2222 (TCPRoute → VM sshd, pubkey-only); LAN + tailnet only.
- Teleport is the one service NOT behind Traefik: the proxy terminates its own TLS (internal CA) on its own LB IP `10.10.20.154` (`teleport.internal`, explicit knot zone record); web UI, `tsh` and agent tunnels multiplex on 443. (Kept for a demo — teardown queued in the ROADMAP; devil's everyday doors are ssh + ghostty-web.)

### Secrets

All secrets are SOPS-encrypted with age (`.sops.yaml`); Flux decrypts in-cluster using the `sops-age` key. In-repo secrets: `ghcr-pat` (OCI artifact pull), `cloudflare-dns01` (DNS-01 solver), `operator-oauth` (Tailscale operator), `grafana-credentials` (monitoring), `agh-config` (AdGuard Home seed), `pull-secret` (apex GHCR), `forgejo-secrets` (Forgejo: SECRET_KEY, INTERNAL_TOKEN, admin bootstrap), `pds-secrets` (ATProto PDS: JWT secret, admin password, PLC rotation key), `backup-credentials` (k8up: restic repo password + Garage S3 keys), plus the Talos secrets bundle and node Tailscale patch under `talos/`.

### Access

- `kubeconfig` and `talosconfig` live in the repo root (gitignored).
- Off-LAN access runs over the tailnet: the nodes run the Tailscale system extension; advertise `10.10.20.0/24` from the worker node and approve the route in the Tailscale admin console.
- `dashboard.internal` (and every other `*.internal` name) resolves via the DNS stack: AdGuard Home (`10.10.20.153`, LAN-facing) -> the `resolver` pod on the OCI control-plane node (true recursion + DNSSEC, ClusterIP `10.96.0.53`) -> knotd in the same pod for `internal.` (authoritative zone, wildcard -> `10.10.20.128`; non-cluster devices get explicit records, e.g. `router.internal` -> `10.10.10.1`). LAN: router DHCP DNS field -> `10.10.20.153`. Off-LAN (tailnet): Tailscale split DNS, domain `internal.` -> `10.10.20.153` (requires MagicDNS; reachable via the advertised subnet routes). Until the router field is set, a hosts entry remains the stopgap.
