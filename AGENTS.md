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
│   ├── applications.yaml       per-app Kustomizations (dns, agh, homepage, ddns, apex, forgejo, pds)
│   └── ghcr-pat.sops.yaml
├── infrastructure/
│   ├── storage/                local-path-provisioner
│   ├── backup/                 k8up (restic → Garage S3 on the friend's NAS; no Schedule in-tree)
│   ├── keel/                   Keel image updater (poll-based, drives tier-2 :latest apps)
│   ├── knative/                Knative Operator v1.23.1 + KnativeServing CR (1.23.0, creates
│   │                           CRDs + control plane + net-gateway-api ingress at runtime),
│   │                           whimsy namespace for tier-3 whim apps (outside Flux)
│   ├── monitoring/             kube-prometheus-stack + metrics-server + Gatus
│   ├── network/
│   │   ├── cilium/             Cilium HelmRelease (the operator creates its CRDs at runtime)
│   │   └── ipam/               CiliumLoadBalancerIPPool + CiliumL2AnnouncementPolicy
│   └── ingress/
│       ├── cert-manager/       HelmRelease + Namespace + cloudflare-dns01 secret
│       ├── traefik/            HelmRelease, Gateway, certificates, middleware, Namespace
│       └── tailscale/          HelmRelease + Namespace + operator-oauth secret
└── applications/               one directory = one namespace
    ├── apex/                   tier-2: the apex site (image from the apex repo, Keel-polled)
    ├── agh/                    AdGuard Home (LAN DNS edge)
    ├── ddns/                   favonia/cloudflare-ddns (0xbf.ch + *.0xbf.ch → home IP)
    ├── dns/                    knotd + kresd (the .internal zone — resolver pod on OCI)
    ├── forgejo/                tier-1: git forge (git.0xbf.ch, git-ssh via TCPRoute, k8up backup)
    ├── pds/                    tier-1: ATProto PDS (Bluesky; handles <name>.0xbf.ch via well-known)
    └── homepage/               the dashboard
```

## Kustomization dependency tree

```
storage → cilium → ipam
               └──► cert-manager → traefik → tailscale
cilium also dependsOn: prometheus-crds
monitoring also dependsOn: prometheus-crds, traefik
traefik also dependsOn: gateway-api-crds, traefik-crds
backup dependsOn: k8up-crds
```

Hard constraint behind this shape: a Kustomization's server-side dry-run validates its entire manifest set before applying anything. A custom resource whose CRD does not exist yet fails the dry-run and nothing in that Kustomization applies — including the HelmRelease that would have created the CRD. Therefore:

- CRs never share a Kustomization with the HelmRelease that produces their CRDs (that is why `ipam` is separate from `cilium`, and why cert-manager CRs live in the `traefik` dir which `dependsOn: cert-manager`).
- Gateway API and Traefik CRDs are installed up-front from pinned upstream GitRepository tags (`cluster/crds.yaml`, `prune: false`).
- Cilium ships no CRD files anywhere — its operator creates them at runtime. Never try to vendor or fetch them.
- Upgrading a chart version means bumping the matching CRD GitRepository tag in the same commit (traefik chart ↔ traefik-crds).

## Component notes

- **cilium 1.20.2** (`network/cilium/cilium.yaml`): `kubeProxyReplacement: true`, `ipam.mode: kubernetes`, `gatewayAPI.enabled: false` (Traefik owns Gateway API), `k8sServiceHost: localhost` / `k8sServicePort: 7445` (Talos apid proxy), cgroup + privileged settings for Talos. `prometheus.enabled` + ServiceMonitors + Hubble metrics are on (requires the prometheus CRDs from the crds phase — hence `cilium` dependsOn `prometheus-crds`). LB-IPAM pool `10.10.20.128/25` and L2 announcement on node `rbpi`, interface `end0` live in `network/ipam/pool.yaml`. Gateway LB address: `10.10.20.128`.
- **traefik chart 41.6.0** (`ingress/traefik/traefik.yaml`): values schema is strict. `globalArguments` no longer exists — use the `global:` block. Port redirects use `http.redirections.entryPoint` (not `redirectTo`). Gateway listeners must match the entrypoint `port` values (8000/8443/22), not the exposed Service ports (80/443/22). `providers.kubernetesGateway.experimentalChannel: true` is on — TCPRoute (forgejo git-ssh) is experimental-channel only. Gotcha: the gateway-api v1.6.2 bundles ship a `safe-upgrades.gateway.networking.k8s.io` ValidatingAdmissionPolicy that **forbids installing experimental CRDs on top of standard-channel CRDs** — it blocked the standard → experimental switch (stuck `gateway-api-crds` in a dry-run-denied retry loop). If the channel ever flips again, delete the VAP + binding from the cluster first; the bundle re-applies them and they then guard against accidental downgrades while allowing experimental → experimental updates. The chart's built-in default Gateway is disabled (`gateway.enabled: false`) because `gateway.yaml` owns the Gateway. The dashboard is the chart-managed IngressRoute (`ingressRoute.dashboard`, host `dashboard.internal`, internal cert, `internal-allowlist` middleware) — the only IngressRoute allowed in this repo. Prometheus metrics enabled (`metrics.prometheus`), scraped by the `traefik` ServiceMonitor in `monitoring/`.
- **gateway.yaml**: listeners `web` (8000, HTTP), `websecure` (8443, no hostname — matches all hostnames so both the bare `0xbf.ch` and `*.0xbf.ch` subdomains attach; cert `wildcard-domain-tls`; do not add a hostname filter, a wildcard would stop matching the bare domain again), `websecure-internal` (8443, `*.internal`, cert `wildcard-internal-tls`), `gitssh` (22, TCP — forgejo-ssh TCPRoute; Traefik entrypoint hostPort 22 is the WAN entry, Talos runs no sshd so nothing else binds 22; no router SSH wanted, the future dev box takes WAN 2222).
- **certificates.yaml**: Let's Encrypt ClusterIssuer (Cloudflare DNS-01) + `wildcard-domain` cert for `0xbf.ch`/`*.0xbf.ch`; internal CA chain (selfsigned bootstrap → 10y CA in cert-manager ns → CA ClusterIssuer → 1y `*.internal` wildcard) because Let's Encrypt cannot issue for `.internal`.
- **tailscale operator 1.102.3**: reads OAuth credentials from Secret `operator-oauth` (chart default name; do not rename back). Gotcha: the OAuth client bears `tag:k8s` + `tag:k8s-operator`, and the operator can only mint authkeys for tags **managed by** the client's tags — so `tagOwners` must list the tags as owners of each other (cross-ownership), not just the human user. The client's tags are fixed at creation; wrong tags mean regenerating the client and re-`sops`-ing the secret. Proxy pods get `tag:k8s` via `proxyConfig.defaultTags`.
- **tailscale on the nodes**: the nodes run the `ext-tailscale` Talos system extension (config in `talos/patches/all/02-tailscale.sops.yaml`), tagged `tag:infra` — a separate identity from the operator.
- **monitoring** (`infrastructure/monitoring/`): kube-prometheus-stack 91.4.1 + metrics-server 3.14.0 + Gatus v5.36.0 (`status.internal`). Talos gotchas baked into values: kubeControllerManager/kubeScheduler/kubeEtcd/kubeProxy scraping disabled (unreachable on Talos / replaced by Cilium KPR); metrics-server needs `--kubelet-insecure-tls`. Prometheus retention 7d/8GB on local-path; Grafana admin credentials via `monitoring-credentials.sops.yaml`; all selectors set to `NilUsesHelmValues: false` so future ServiceMonitors are picked up without release labels. Alertmanager receivers: decision pending (ntfy/Discord/Telegram).
- **cert-manager 1.21.2**: `install.crds`/`upgrade.crds: CreateReplace` + `crds.enabled: true`.
- **dns (knotd + kresd on OCI)**: the whole DNS brain runs as the `resolver` pod (namespace `dns`) — the single tolerated workload on the OCI control-plane node (taint stays; clean :53 egress, which the Sunrise AX7501-B1 ISP firmware hijacks on the home segment — unconditional, no toggle; pointing the router's DNS at a LAN resolver creates a loop that kills the resolver, see the pi-hole discourse thread on this exact router). kresd recurses public names with local DNSSEC validation and stubs `internal.` to knotd over loopback (`authoritative: true, dnssec: false`); knotd is the zone authority (Service `resolver` pinned `10.96.0.53`, AGH's single upstream is this IP literal). The home segment runs only AGH. Zone data lives in `applications/dns/knot/internal.zone` (configMapGenerator hashes → pod rolls on change).
- **pihole 2026.07.2**: REMOVED — replaced by AdGuard Home (`applications/agh/`, namespace `agh`). Kept as history: FTL v6 refused to forward the reserved `.internal` TLD (RFC 9760 hardening, no toggle), returned 403 on `GET /`, and needed raw dnsmasq `address=` lines as a wildcard workaround — all reasons for the swap.
- **agh (AdGuard Home) v0.107.79**: LAN-facing DNS edge at `10.10.20.153` (static LB IP — inherited from Pi-hole; the router DHCP field and Tailscale split DNS point here and must not float). Forwards everything (including `.internal`) to kresd — AGH does not special-case the reserved TLD. Config is seeded on first boot from `agh-config.sops.yaml` (Secret `agh-config`, whole `AdGuardHome.yaml` as one `stringData` value, bcrypt admin hash inside) by an initContainer that copies it onto the PVC only if absent; afterwards AGH owns the file on the PVC and UI edits persist — the seed is the git-side intent for upstreams/filters, re-seeding requires deleting `conf/AdGuardHome.yaml` from the PVC. Admin UI at `agh.internal` (allowlisted middleware copy lives in the `agh` namespace — HTTPRoute ExtensionRef is same-namespace only).
- **forgejo 16.0.5** (`applications/forgejo/`, tier-1): git forge at `git.0xbf.ch` (public, `websecure` listener, LE wildcard cert). Image `codeberg.org/forgejo/forgejo:16.0.5` pinned — deliberate bumps only. SQLite + everything under one `/data` PVC (10Gi local-path), `Recreate` strategy. `app.ini` is seeded on first boot by an initContainer (template from the `forgejo-config` ConfigMap + `[security]` block appended from `forgejo-secrets.sops.yaml`: SECRET_KEY, INTERNAL_TOKEN) and then owned by Forgejo on the PVC — re-seeding requires deleting `/data/gitea/conf/app.ini`; the same initContainer bootstraps the admin user idempotently (runs as git via su-exec so the SQLite DB is uid-1000-owned). Registration is closed. git-over-SSH rides the Gateway `gitssh` TCP listener → `TCPRoute` (experimental channel; gateway-api CRDs switched `config/crd/standard` → `config/crd/experimental`, same v1.6.2 tag) → Traefik `gitssh` entrypoint (hostPort 22 on rbpi; advertised `SSH_PORT` 22 so clone URLs are scp-style `git@git.0xbf.ch:owner/repo.git`) — WAN SSH needs the router `22 → 10.10.20.10` forward; the future dev box takes WAN 2222 instead (no router SSH). SSH host keys live in `/data/ssh` on the PVC (stable across restarts). Mailer disabled; plan: Proton SMTP token once Proton Premium custom domain is live. k8up Schedule in-namespace (daily 03:00 + prune) — jobs fail until the NAS tailnet path is fixed.
- **pds 0.4.5034** (`applications/pds/`, tier-1): ATProto PDS (Bluesky) at `pds.0xbf.ch` (public, `websecure` listener, LE wildcard cert). Image `ghcr.io/bluesky-social/pds:0.4.5034` pinned — deliberate bumps only. SQLite + blobs under one `/pds` PVC (10Gi local-path), `Recreate` strategy. Fully env-configured (ConfigMap `pds-config` via configMapGenerator `envs` + Secret `pds-secrets` via envFrom: PDS_JWT_SECRET, PDS_ADMIN_PASSWORD, PDS_PLC_ROTATION_KEY_K256_PRIVATE_KEY_HEX) — no initContainer, no config seeding; the image creates its own data dirs. Vanity handles: `PDS_SERVICE_HANDLE_DOMAINS=.0xbf.ch` allows accounts at `<name>.0xbf.ch`; the wildcard HTTPRoute (`*.0xbf.ch` → pds) makes `https://<handle>/.well-known/atproto-did` serve the DID — the PDS reads its account DB by Host header (verified from source), so **no per-account DNS TXT records and no per-handle routes exist**; atproto clients fall back to well-known when TXT is absent. Owner-accepted tradeoff: the wildcard route is the fallback for ALL unrouted `*.0xbf.ch` subdomains — exact-match routes (apex, git, whims, future apps) win precedence; unrouted names get PDS 404s. Account creation needs no git change: `kubectl -n pds exec deploy/pds -- goat pds admin account create --handle <name>.0xbf.ch --email … --password …` (invites required; accounts are admin-created). Gotcha: the Service is named `pds-http`, not `pds` — a Service named `pds` injects `PDS_PORT`/`PDS_SERVICE_HOST` service-link env vars that clobber the image's `PDS_PORT=3000` (the PDS then binds a random port; observed live). Email deferred (PDS_EMAIL_SMTP_URL once Proton is live). k8up Schedule in-namespace (03:30 backup / 05:30 prune, staggered behind forgejo).
- **homepage v2.4.0**: dashboard at `homepage.internal` (allowlisted middleware copy in the `homepage` namespace). Config: `settings.yaml` + `kubernetes.yaml` via ConfigMap (configMapGenerator → pod rolls on change), `services.yaml` via Secret `homepage-services` (sops — contains the AGH widget credentials and the Grafana API token; re-seeding follows the agh-config pattern). Widgets: adguard (AGH stats via in-cluster Service), gatus (health overview), grafana (service-account token). Kubernetes cluster/nodes stats via the `kubernetes.yaml` config + RBAC (`rbac.yaml`: SA + ClusterRole incl. metrics.k8s.io — served by metrics-server). `HOMEPAGE_ALLOWED_HOSTS` pins the accepted Host header.
- **k8up 4.10.0** (`infrastructure/backup/k8up/`): restic backups to Garage S3 on the friend's NAS (Garage on :3900, plain HTTP — WireGuard transport, restic encrypts at rest). Endpoint is the IP literal `100.96.72.126` — the NAS's `ts.net` name is MagicDNS-only (no public DNS record; kresd and CoreDNS both NXDOMAIN it), so cluster pods can never resolve it. Access gotcha: the NAS is shared in from the friend's tailnet (`tail112719`), and shared nodes are invisible to tagged devices (`tag:k8s`, `tag:infra`) while user-owned devices connect fine — the friend's tailnet ACL must grant shared-in devices access (`src: autogroup:shared → 100.96.72.126:3900`; if tagged devices don't match autogroup:shared, allow their tailscale IPs explicitly). Whether pods can traverse the node's tailscale0 directly is untested — if the direct path fails, fall back to a Tailscale operator egress proxy (Service with `tailscale.com/tailnet-ip` annotation; the operator rewrites it to ExternalName — give the Kustomization a `spec.ignore` for `/spec/type`, `/spec/externalName`, `/metadata/finalizers` so Flux doesn't fight it). Gotcha: **PVC discovery is namespace-scoped** — k8up backs up the PVCs of the namespace a Schedule lives in, nothing else. An app opts in by adding a `k8up.io/v1` Schedule (backup + prune + retention) to its own directory; the first one lives in `applications/forgejo/` (monitoring/agh excluded by choice). The operator carries the backend as global env vars (`BACKUP_GLOBALS3ENDPOINT/BUCKET`, `BACKUP_GLOBALACCESSKEYID/SECRETACCESSKEY`, `BACKUP_GLOBALREPOPASSWORD`) sourced from `backup-credentials.sops.yaml`, so per-namespace Schedules need no backend block and no secret copies. Cron times fire in `Europe/Zurich` (`k8up.timezone`). The repo password (`k8up-password`) is the only key to the backups — never rotate it. Verification runbook: `.private/backup.md` (gitignored).

## Application tiers

Apps deploy in three tiers with different release mechanics; the public edge is shared. Status: the Tier 2/3 platform pieces (Keel, Knative Serving v1.23.0 via the Knative Operator with the net-gateway-api layer, the `{{.Name}}.0xbf.ch` domain template) are **implemented in the tree, pending the next tag deploy**.

Edge (all tiers): `0xbf.ch` + `*.0xbf.ch` are **DNS-only (grey-cloud) A records** — Cloudflare handles the DNS only, traffic goes **direct** to the home WAN IP `31.164.81.63` (no Cloudflare proxy; the owner rejects the orange cloud). The records are kept pointing at the home WAN IP by the favonia/cloudflare-ddns updater (`applications/ddns/`, Zone-scoped token in a sops Secret). The router forwards 443/80 → `10.10.20.10` (the rbpi node) — the Zyxel only NAT-forwards to DHCP-known devices and refuses the virtual LB IP `10.10.20.128`, so Traefik binds `hostPort` 80/443 on the node for the WAN entry; the LB IP keeps serving LAN clients. Traefik terminates the LE wildcard cert (`wildcard-domain-tls`, cert-manager Cloudflare DNS-01) and routes: tier-1/tier-2 via their HTTPRoutes, whims via the per-KSvc HTTPRoutes that Knative's net-gateway-api layer creates on the Traefik Gateway (no catch-all needed). Zone SSL mode must be **Full (strict)**. There are **no Flux image-automation controllers and no master artifact** — image updates are handled per-tier below; do not install the image controllers or switch the OCIRepository off semver for this.

- **Tier 1 — tree-managed apps** (forgejo, immich, anything permanent): fully described in this tree (Deployment with a pinned image tag, ConfigMaps/Secrets, HTTPRoute). Image updates are deliberate git edits + tag; the OCI artifact gate applies in full. No registry polling, no Keel.
- **Tier 2 — dual-config apps** (the apex website): the infra tree holds the plumbing — Deployment referencing `ghcr.io/bfeitknecht/apex:latest` with `imagePullPolicy: Always` + Keel annotations (`keel.sh/trigger: poll`, `keel.sh/policy: latest`, `keel.sh/match-tag: "true"`), Service, HTTPRoute for `0xbf.ch`, and the GHCR pull Secret (`pull-secret.sops.yaml`, Secret name `dockerconfigjson` — the image is private; the namespace default SA carries it, Keel's poll uses the same credentials). Pull secrets are namespace-scoped by Kubernetes design — every namespace pulling a private `bfeitknecht/*` image carries its own copy (the kubelet only reads them from the pod's own SA/namespace; Keel cannot inject them). The site code lives in its own repo whose CI pushes `:latest`. **Keel** polls the `:latest` digest and re-rolls the pod on every site push — the infra tree is never touched for site updates. The apex Kustomization MUST carry `spec.ignore` excluding the image field, otherwise Flux drift correction reverts Keel's in-cluster image updates and the two fight over the field (update flap). Never put Keel annotations on Tier 1 or Tier 3 workloads, and never on Knative Services (Keel's kubernetes implementer handles Deployment/StatefulSet/DaemonSet only — verified from source).
- **Tier 3 — whim apps** (spur-of-the-moment, scale-to-zero): the `whimsy` namespace is deliberately OUTSIDE Flux — registry-driven cluster state, no git record. Each whim is a self-contained repo: **Dockerfile + code, no k8s manifests**. Deployment via the **kn CLI** (`brew install knative/client`; reads the kubeconfig, works from home + tailnet): first run `kn service create <name> --image ghcr.io/bfeitknecht/<name>:<tag> --port <port> -n whimsy`, later pushes `kn service update <name> --image …:<new-tag>` — use the SHA/version tag, not `:latest` (an unchanged image string rolls no revision). The namespace's default ServiceAccount carries the GHCR pull Secret (`dockerconfigjson`, sops — paste the dockerconfigjson, encrypt in place), so private images pull with no per-service config. The Knative domain template is `{{.Name}}.0xbf.ch`, so the KSvc **name declares the domain** — no labels, no per-app route. A whim controller (label-driven GHCR watcher) was considered and rejected: `kn` covers it with zero custom code; revisit only if the per-push command actually annoys. Do NOT put whim manifests in this tree; do NOT manage the whimsy namespace with Flux.

Tier gotchas: Keel cannot update Knative Services (its kubernetes implementer handles Deployment/StatefulSet/DaemonSet only — verified from source), so the tiers' updaters never mix. The whims namespace is registry-push = deploy power — whim GHCR repos are personal, pushed only from your own keys. Pods are IPv4-only (single-stack cluster): the DDNS updater cannot detect the home IPv6 prefix, so no AAAA records from `applications/ddns/` until the cluster goes dual-stack. All Knative config lives in the KnativeServing CR's `spec.config` (the operator overwrites raw ConfigMap edits) — domain template `{{.Name}}.0xbf.ch` and the Traefik Gateway wiring are both set there.

## Secrets

- SOPS + age; `.sops.yaml` matches `*.sops.yaml`. Flux decrypts in-cluster with the `sops-age` Secret in `flux-system`.
- Encrypted files: `cluster/ghcr-pat.sops.yaml`, `ingress/cert-manager/cloudflare-dns01.sops.yaml`, `ingress/tailscale/operator-oauth.sops.yaml`, `monitoring/grafana-credentials.sops.yaml`, `applications/agh/agh-config.sops.yaml`, `applications/apex/pull-secret.sops.yaml`, `applications/forgejo/forgejo-secrets.sops.yaml`, `applications/pds/pds-secrets.sops.yaml`, `infrastructure/backup/k8up/backup-credentials.sops.yaml` (Kubernetes Secrets — only `data`/`stringData` values are encrypted, structural fields stay plaintext), `talos/secrets.sops.yaml`, `talos/patches/all/02-tailscale.sops.yaml` (Talos configs — fully encrypted, they are not Kubernetes Secrets).
- **Never decrypt, encrypt, or edit SOPS files as an agent.** The owner performs all secret operations locally and will ask for the exact commands if needed. If a secret's shape matters, ask; do not read values.

## Cluster access

- `kubectl --kubeconfig kubeconfig ...` (repo root, gitignored). Server is K8s 1.35.3; the local kubectl (1.33) is older — skew warnings are cosmetic.
- **Cluster endpoint: oci's tailscale IP `100.73.186.19:6443`** (kubeconfig regenerated for it). The VCN ingress list carries only UDP 41641 (tailscale WireGuard) — no cluster ports exposed; management works from any tailnet device. Requirement: key expiry must stay **disabled** for the nodes' tailscale identities in the Tailscale admin console — an expired node key takes the endpoint down with it. Fallback: flip `clusterEndpoint` to the public IP + re-open the security list, then `topf apply`.
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
- No vendored manifests anywhere. Knative Serving runs via the **Knative Operator** (`infrastructure/knative/`): the operator Deployment is pinned to v1.23.1, the `KnativeServing` CR (`kserving.yaml`) pins the Serving version (1.23.0) and creates the CRDs + control plane + net-gateway-api ingress at runtime — the Cilium pattern. The operator's own CRDs (`KnativeServing`/`KnativeEventing` types) are NOT operator-created — they come from a pinned upstream GitRepository (`cluster/crds.yaml`, knative/operator @ `knative-v1.23.1`, path `config/crd`); without them the operator can't watch its CRs and `knative-serving`'s dry-run fails. The operator Deployment has no readiness/liveness probes (upstream has none; it serves only metrics on 9090). The Istio ingress plugin is disabled in the CR (`spec.ingress.istio.enabled: false`) — without it the install fails on the missing Istio Gateway CRD. All Knative config values live in the CR's `spec.config` block (the supported mechanism — the operator overwrites raw ConfigMap edits on reconcile). Upgrades: bump the version in `kserving.yaml` (and the operator image tag when needed).
- CRDs come from pinned upstream GitRepository sources, from Helm charts themselves, or are operator-created at runtime — never vendored YAML files.
- No explanatory YAML comments except load-bearing gotchas (listener port mapping, chart collisions, internal CA rationale).
- No hardcoded IPs inside Helm values; cluster-specific values live in git-side resources (ipam pool, middlewares).
- Cluster DNS for `*.internal` names is a planned application (Knot Resolver); until then `dashboard.internal` needs a hosts entry or local DNS record pointing at `10.10.20.128`.
