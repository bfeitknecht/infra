# AGENTS.md

Context for AI agents working in this repository. Read this before making changes.

## What this is

Declarative infrastructure for a hybrid Talos Linux Kubernetes cluster: one control-plane node in Oracle Cloud (eu-zurich-1, `10.20.20.10`), one Raspberry Pi 5 worker at home (`10.10.20.10`). Everything on the cluster is managed by Flux from this repository. See `README.md` for the human overview.

## The one rule

The cluster only consumes published OCI artifacts. To change anything:

```
edit manifests → git commit → push a vX.Y.Z tag → CI publishes to ghcr.io/bfeitknecht/infra → Flux reconciles
```

- Never `kubectl apply` manifests (read-only dry-runs are fine).
- The OCIRepository tracks `semver >=1.0.0`; re-tagging the same commit changes nothing. Verify a tag contains your change: `git show <tag>:<path>`.
- Tags are cheap; a broken tag means a broken reconcile loop until the next one.

## Layout

```
kubernetes/
├── flux/                       source.yaml (OCIRepository), sync.yaml (root Kustomization)
├── cluster/                    applied by the root Kustomization
│   ├── crds.yaml               GitRepository + Kustomization pairs installing CRDs from
│   │                           pinned upstream tags (gateway-api v1.6.2, traefik chart v41.6.0,
│   │                           kube-prometheus-stack 91.4.1)
│   ├── infrastructure.yaml     the Kustomization dependency tree
│   ├── applications.yaml       application Kustomizations (empty for now)
│   └── ghcr-pat.sops.yaml
├── infrastructure/
│   ├── storage/                local-path-provisioner
│   ├── monitoring/             kube-prometheus-stack + metrics-server + Gatus
│   ├── network/
│   │   ├── cilium/             Cilium HelmRelease (the operator creates its CRDs at runtime)
│   │   └── ipam/               CiliumLoadBalancerIPPool + CiliumL2AnnouncementPolicy
│   └── ingress/
│       ├── cert-manager/       HelmRelease + Namespace + cloudflare-dns01 secret
│       ├── traefik/            HelmRelease, Gateway, certificates, middleware, Namespace
│       └── tailscale/          HelmRelease + Namespace + operator-oauth secret
└── applications/               user workloads (to be populated)
```

## Kustomization dependency tree

```
storage → cilium → ipam
               └──► cert-manager → traefik → tailscale
cilium also dependsOn: prometheus-crds
monitoring also dependsOn: prometheus-crds, traefik
traefik also dependsOn: gateway-api-crds, traefik-crds
```

Hard constraint behind this shape: a Kustomization's server-side dry-run validates its entire manifest set before applying anything. A custom resource whose CRD does not exist yet fails the dry-run and nothing in that Kustomization applies — including the HelmRelease that would have created the CRD. Therefore:

- CRs never share a Kustomization with the HelmRelease that produces their CRDs (that is why `ipam` is separate from `cilium`, and why cert-manager CRs live in the `traefik` dir which `dependsOn: cert-manager`).
- Gateway API and Traefik CRDs are installed up-front from pinned upstream GitRepository tags (`cluster/crds.yaml`, `prune: false`).
- Cilium ships no CRD files anywhere — its operator creates them at runtime. Never try to vendor or fetch them.
- Upgrading a chart version means bumping the matching CRD GitRepository tag in the same commit (traefik chart ↔ traefik-crds).

## Component notes

- **cilium 1.20.2** (`network/cilium/cilium.yaml`): `kubeProxyReplacement: true`, `ipam.mode: kubernetes`, `gatewayAPI.enabled: false` (Traefik owns Gateway API), `k8sServiceHost: localhost` / `k8sServicePort: 7445` (Talos apid proxy), cgroup + privileged settings for Talos. `prometheus.enabled` + ServiceMonitors + Hubble metrics are on (requires the prometheus CRDs from the crds phase — hence `cilium` dependsOn `prometheus-crds`). LB-IPAM pool `10.10.20.128/25` and L2 announcement on node `rbpi`, interface `end0` live in `network/ipam/pool.yaml`. Gateway LB address: `10.10.20.128`.
- **traefik chart 41.6.0** (`ingress/traefik/traefik.yaml`): values schema is strict. `globalArguments` no longer exists — use the `global:` block. Port redirects use `http.redirections.entryPoint` (not `redirectTo`). Gateway listeners must match the entrypoint `port` values (8000/8443), not the exposed Service ports (80/443). The chart's built-in default Gateway is disabled (`gateway.enabled: false`) because `gateway.yaml` owns the Gateway. The dashboard is the chart-managed IngressRoute (`ingressRoute.dashboard`, host `dashboard.internal`, internal cert, `internal-allowlist` middleware) — the only IngressRoute allowed in this repo. Prometheus metrics enabled (`metrics.prometheus`), scraped by the `traefik` ServiceMonitor in `monitoring/`.
- **gateway.yaml**: listeners `web` (8000, HTTP), `websecure` (8443, `*.0xbf.ch`, cert `wildcard-domain-tls`), `websecure-internal` (8443, `*.internal`, cert `wildcard-internal-tls`).
- **certificates.yaml**: Let's Encrypt ClusterIssuer (Cloudflare DNS-01) + `wildcard-domain` cert for `0xbf.ch`/`*.0xbf.ch`; internal CA chain (selfsigned bootstrap → 10y CA in cert-manager ns → CA ClusterIssuer → 1y `*.internal` wildcard) because Let's Encrypt cannot issue for `.internal`.
- **tailscale operator 1.102.3**: reads OAuth credentials from Secret `operator-oauth` (chart default name; do not rename back). Gotcha: the OAuth client bears `tag:k8s` + `tag:k8s-operator`, and the operator can only mint authkeys for tags **managed by** the client's tags — so `tagOwners` must list the tags as owners of each other (cross-ownership), not just the human user. The client's tags are fixed at creation; wrong tags mean regenerating the client and re-`sops`-ing the secret. Proxy pods get `tag:k8s` via `proxyConfig.defaultTags`.
- **tailscale on the nodes**: the nodes run the `ext-tailscale` Talos system extension (config in `talos/patches/all/02-tailscale.sops.yaml`), tagged `tag:infra` — a separate identity from the operator.
- **monitoring** (`infrastructure/monitoring/`): kube-prometheus-stack 91.4.1 + metrics-server 3.14.0 + Gatus v5.36.0 (`status.internal`). Talos gotchas baked into values: kubeControllerManager/kubeScheduler/kubeEtcd/kubeProxy scraping disabled (unreachable on Talos / replaced by Cilium KPR); metrics-server needs `--kubelet-insecure-tls`. Prometheus retention 7d/8GB on local-path; Grafana admin credentials via `monitoring-credentials.sops.yaml`; all selectors set to `NilUsesHelmValues: false` so future ServiceMonitors are picked up without release labels. Alertmanager receivers: decision pending (ntfy/Discord/Telegram).
- **cert-manager 1.21.2**: `install.crds`/`upgrade.crds: CreateReplace` + `crds.enabled: true`.
- **dns (knotd + kresd on OCI)**: the whole DNS brain runs as the `resolver` pod (namespace `dns`) — the single tolerated workload on the OCI control-plane node (taint stays; clean :53 egress, which the Sunrise AX7501-B1 ISP firmware hijacks on the home segment — unconditional, no toggle; pointing the router's DNS at a LAN resolver creates a loop that kills the resolver, see the pi-hole discourse thread on this exact router). kresd recurses public names with local DNSSEC validation and stubs `internal.` to knotd over loopback (`authoritative: true, dnssec: false`); knotd is the zone authority (Service `resolver` pinned `10.96.0.53`, AGH's single upstream is this IP literal). The home segment runs only AGH. Zone data lives in `applications/utilities/dns/knot/internal.zone` (configMapGenerator hashes → pod rolls on change).
- **pihole 2026.07.2**: REMOVED — replaced by AdGuard Home (`applications/utilities/agh/`, namespace `agh`). Kept as history: FTL v6 refused to forward the reserved `.internal` TLD (RFC 9760 hardening, no toggle), returned 403 on `GET /`, and needed raw dnsmasq `address=` lines as a wildcard workaround — all reasons for the swap.
- **agh (AdGuard Home) v0.107.79**: LAN-facing DNS edge at `10.10.20.153` (static LB IP — inherited from Pi-hole; the router DHCP field and Tailscale split DNS point here and must not float). Forwards everything (including `.internal`) to kresd — AGH does not special-case the reserved TLD. Config is seeded on first boot from `agh-config.sops.yaml` (Secret `agh-config`, whole `AdGuardHome.yaml` as one `stringData` value, bcrypt admin hash inside) by an initContainer that copies it onto the PVC only if absent; afterwards AGH owns the file on the PVC and UI edits persist — the seed is the git-side intent for upstreams/filters, re-seeding requires deleting `conf/AdGuardHome.yaml` from the PVC. Admin UI at `agh.internal` (allowlisted middleware copy lives in the `agh` namespace — HTTPRoute ExtensionRef is same-namespace only).
- **homepage v2.4.0**: dashboard at `homepage.internal` (allowlisted middleware copy in the `homepage` namespace). Config: `settings.yaml` + `kubernetes.yaml` via ConfigMap (configMapGenerator → pod rolls on change), `services.yaml` via Secret `homepage-services` (sops — contains the AGH widget credentials and the Grafana API token; re-seeding follows the agh-config pattern). Widgets: adguard (AGH stats via in-cluster Service), gatus (health overview), grafana (service-account token). Kubernetes cluster/nodes stats via the `kubernetes.yaml` config + RBAC (`rbac.yaml`: SA + ClusterRole incl. metrics.k8s.io — served by metrics-server). `HOMEPAGE_ALLOWED_HOSTS` pins the accepted Host header.

## Secrets

- SOPS + age; `.sops.yaml` matches `*.sops.yaml`. Flux decrypts in-cluster with the `sops-age` Secret in `flux-system`.
- Encrypted files: `cluster/ghcr-pat.sops.yaml`, `ingress/cert-manager/cloudflare-dns01.sops.yaml`, `ingress/tailscale/operator-oauth.sops.yaml`, `monitoring/grafana-credentials.sops.yaml`, `applications/utilities/agh/agh-config.sops.yaml` (Kubernetes Secrets — only `data`/`stringData` values are encrypted, structural fields stay plaintext), `talos/secrets.sops.yaml`, `talos/patches/all/02-tailscale.sops.yaml` (Talos configs — fully encrypted, they are not Kubernetes Secrets).
- **Never decrypt, encrypt, or edit SOPS files as an agent.** The owner performs all secret operations locally and will ask for the exact commands if needed. If a secret's shape matters, ask; do not read values.

## Cluster access

- `kubectl --kubeconfig kubeconfig ...` (repo root, gitignored). Server is K8s 1.35.3; the local kubectl (1.33) is older — skew warnings are cosmetic.
- `talosctl --talosconfig talosconfig -e 10.20.20.10 -n <node-ip>` for node-level work.
- Nodes: `oci` (control-plane, tainted, no workloads), `rbpi` (worker, runs everything). Talos 1.14.0.

## Debugging playbook

1. `flux get kustomizations` — the first red/Unknown link in the chain is where to look.
2. `kubectl -n flux-system describe kustomization <name>` — conditions and events say whether it is build, dry-run, apply, or health-check that failed.
3. HelmRelease problems: `kubectl -n <namespace> describe helmrelease <name>` — chart values schema violations appear verbatim in the message and name the offending key.
4. All Flux controllers in CrashLoopBackOff with `dial tcp 10.96.0.1:443: no route to host` means in-cluster service routing is down (typically right after a Cilium restart). Fix the datapath first, then `kubectl -n flux-system rollout restart deployment` — long-running pods can lose their Cilium endpoint when the agent restarts and stay detached from the datapath.
5. Validate locally before tagging: `kubectl kustomize <dir>` for each changed directory; `kubectl apply --dry-run=server -f <file>` for `cluster/*.yaml`.
6. After bumping a chart version, diff its `values.yaml` against the pinned values — renamed keys fail the values schema at install time.

## Conventions

- Gateway API for all routing; the Traefik dashboard IngressRoute is the sole exception.
- No vendored CRDs; CRDs come from pinned upstream GitRepository sources or from Helm charts themselves.
- No explanatory YAML comments except load-bearing gotchas (listener port mapping, chart collisions, internal CA rationale).
- No hardcoded IPs inside Helm values; cluster-specific values live in git-side resources (ipam pool, middlewares).
- Cluster DNS for `*.internal` names is a planned application (Knot Resolver); until then `dashboard.internal` needs a hosts entry or local DNS record pointing at `10.10.20.128`.
