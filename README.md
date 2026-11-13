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
- **Backups:** k8up (restic) to Garage S3

### Network & Cluster

- **Networking & Ingress:** Cilium, Traefik, Tailscale, Cert-Manager + Cloudflare DNS-01
- **Monitoring:** kube-prometheus-stack, Metrics Server, Gatus

### Applications

- **Public:** apex site `0xbf.ch` with SSH portfolio on `22` (`ssh 0xbf.ch`), glob blog `blog.0xbf.ch`, exhib gallery `gallery.0xbf.ch` (all Keel-polled `:latest`)
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
├── .sops.yaml                       # SOPS config (age public key)
│
├── talos/                          # Talos OS config (topf)
│   ├── topf.yaml                   # TOPF cluster definition; per-node schematicId
│   ├── schematic.<node>.yaml       # Image-factory schematics
│   ├── secrets.sops.yaml           # SOPS-encrypted cluster secrets
│   └── patches/                    # merged: all/ -> <role>/ -> node/<host>/
│       ├── all/                    # cluster-wide: hostname, tailscale, CNI
│       ├── control-plane/          # oci: install disk, network, certSANs
│       └── node/                   # per-host: 01-install, 02-network, 03-tailscale, 04-storage
│
└── kubernetes/                     # Flux GitOps Manifests
    ├── flux/                       # Flux bootstrap + tag filter
    │   └── gotk-sync.yaml
    ├── cluster/                    # entrypoints
    │   ├── crds.yaml               # pinned upstream CRDs (prune: false)
    │   ├── infrastructure.yaml     # Kustomization dependency tree
    │   └── applications.yaml       # per-app Kustomizations
    ├── infrastructure/             # platform
    │   ├── storage/                # Local Path Provisioner
    │   ├── backup/                 # k8up (restic to Garage S3)
    │   ├── keel/                   # image updater for tier-2 :latest
    │   ├── knative/                # Knative operator + Serving (tier-3)
    │   ├── monitoring/             # kube-prometheus-stack, metrics-server, Gatus
    │   ├── network/                # Cilium (LB-IPAM, L2 announce), Tailscale
    │   └── ingress/                # Traefik (Gateway API), cert-manager, Tailscale
    └── applications/               # workloads (one directory = one namespace)
        ├── apex/                   # public site + SSH TUI (Keel-polled :latest)
        ├── glob/                   # blog (Keel-polled :latest)
        ├── exhib/                  # gallery (3 containers, Keel-polled :latest)
        ├── atuin/                  # shell history (atuin.0xbf.ch)
        ├── agh/                    # AdGuard Home (LAN DNS edge)
        ├── ddns/                   # favonia/cloudflare-ddns
        ├── dns/                    # knotd + kresd (internal. zone)
        ├── devil/                  # kata VM pod (ssh 2222, ghostty-web at devil.internal)
        ├── forgejo/                # git forge (git.0xbf.ch)
        ├── pds/                    # ATProto PDS (handles at <name>.pds.0xbf.ch)
        └── homepage/               # dashboard
```

### Network Model

Addressing follows `10.<location>.<function>.<host>` with `location = 10` for home and `location = 20` for cloud `eu-zurich-1`.

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
| OS            | Talos Linux                                           | 1.14.6                          |
| Kubernetes    | API server / kubelet                                  | 1.35.3                          |
| GitOps        | Flux (source, kustomize, helm, notification)          | 2.9.5                           |
| CNI           | Cilium (kube-proxy replacement, LB-IPAM, L2 announce) | 1.20.2                          |
| Ingress       | Traefik via Gateway API                               | chart 41.6.0 (v3.7)             |
| Gateway API   | standard channel CRDs                                 | 1.6.2                           |
| Certificates  | cert-manager                                          | 1.21.2                          |
| Mesh / VPN    | Tailscale (operator + extension on nodes)             | 1.102.3                         |
| Monitoring    | kube-prometheus-stack, metrics-server, Gatus          | 91.4.1 / 3.14.0 / v5.36.0       |
| Backups       | k8up (restic to Garage S3)                            | chart 4.10.0 (operator v2.16.0) |
| Whim platform | Knative Serving via operator (scale-to-zero)          | 1.23.0 (operator 1.23.1)        |

### GitOps Delivery

Manifests are packaged as OCI artifact and published to `ghcr.io/bfeitknecht/infra` by GitHub Actions on every `v*` tag. OCIRepository in `flux-system` tracks `semver >=1.0.0`. Push tag is the only deploy method. Cluster never reads working tree or plain git.

```
git tag vX.Y.Z && git push origin master vX.Y.Z   # CI publishes, Flux reconciles
flux reconcile source oci flux-system             # pull immediately (optional)
flux reconcile kustomization flux-system          # apply immediately (optional)
```

### Kustomization Topology

```
cluster/crds.yaml            gateway-api-crds (v1.6.2), traefik-crds (v41.6.0),
                             prometheus-crds (91.4.1), k8up-crds (4.10.0), knative-operator-crds (v1.23.1)
                             pinned GitRepository sources, prune: false

cluster/infrastructure.yaml  storage -> cilium -> ipam
                             cilium -> cert-manager -> traefik -> tailscale
                             k8up-crds -> backup
                             knative-operator-crds -> knative-operator -> knative-serving
                             keel, monitoring (dependsOn prometheus-crds + traefik)
```

Dry-run validates all manifests in a Kustomization before apply. So CRs must not share Kustomization with HelmRelease that creates their CRDs. Cilium CRDs are created by operator at runtime (no upstream files). So LB pool and L2 policy are in separate `ipam` Kustomization that depends on `cilium`.

### Ingress & Certificates

- Traefik is Gateway API implementation (`gatewayClassName: traefik`). Gateway listeners use `8000/8443` plus TCP `22` for apex SSH, `2222` for devil SSH (LAN/tailnet only), `2223` for forgejo git-ssh. LoadBalancer Service exposes `80/443/22/2222/2223`.
- Gateway address `10.10.20.128` is from Cilium LB-IPAM pool in `network/ipam`. It is L2-announced on worker `end0`.
- Public names `0xbf.ch` and `*.0xbf.ch` use Let's Encrypt wildcard via Cloudflare DNS-01.
- Internal names `*.internal` use cert-manager internal CA. Chain is selfsigned bootstrap to 10y CA to 1y wildcard. Let's Encrypt cannot issue for `internal`.
- Traefik dashboard is at `https://dashboard.internal`. It is IngressRoute with LAN allowlist middleware.
- ATProto PDS is at `pds.0xbf.ch` (API) and `*.pds.0xbf.ch` (handle via `/.well-known/atproto-did`). Custom handles use DNS TXT.
- Devil kata VM: `devil.internal` serves ghostty-web terminal via HTTPRoute to ttyd in VM. Login uses real `login` prompt and PAM password. SSH is on `2222` via TCPRoute to VM sshd. LAN + tailnet only.

### Secrets

All secrets are SOPS-encrypted with age (`.sops.yaml`). Flux decrypts with `sops-age` key. Repo secrets: `ghcr-pat`, `cloudflare-dns01`, `operator-oauth`, `grafana-credentials`, `agh-config`, `apex/ghcr`, `glob/ghcr`, `exhib/ghcr`, `apex/apex-ssh-host-key`, `forgejo-secrets`, `pds-secrets`, `backup-credentials`, plus Talos secrets bundle and node Tailscale patch in `talos/`.

### Access

- `kubeconfig` at repo root and `talos/talosconfig` (both gitignored).
- Off-LAN access is over tailnet. Nodes run Tailscale extension. Worker advertises `10.10.20.0/24`. Approve route in Tailscale admin console.
- `dashboard.internal` and all `*.internal` names resolve via DNS stack: AdGuard Home `10.10.20.153` (LAN-facing) to `resolver` pod on OCI (recursion + DNSSEC, ClusterIP `10.96.0.53`) to knotd for `internal.` (wildcard to `10.10.20.128`; explicit records for LAN devices like `router.internal` to `10.10.10.1`). LAN: router DHCP DNS to `10.10.20.153`. Off-LAN via Tailscale split DNS `internal.` to `10.10.20.153` (needs MagicDNS via advertised subnet routes). Use hosts entry as stopgap until router field is set.
