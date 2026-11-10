# AGENTS.md

Read this before you change the repo.

## What this is

Declarative infra for a hybrid Talos Linux cluster. One control plane in Oracle Cloud `eu-zurich-1` at `10.20.20.10` (oci). One worker at home at `10.10.20.10` (rbpi Pi 5). Flux manages all cluster state from this repo.

## Rules

Use ASD-STE100. Write short sentences. Be terse and explicit.

The cluster consumes only published OCI artifacts. To change cluster state:

```
edit manifests -> git commit -> push vX.Y.Z tag -> CI publishes to ghcr.io/bfeitknecht/infra -> Flux reconciles
```

- Do not run `kubectl apply`. Dry-run is allowed.
- OCIRepository tracks `semver >=1.0.0`. Re-tagging same commit does nothing. Check tag content with `git show <tag>:<path>`.
- A broken tag breaks reconcile until next tag.

## Layout

```
kubernetes/
├── flux/               source.yaml (OCIRepository), sync.yaml (root Kustomization)
├── cluster/            root Kustomizations
│   ├── crds.yaml       GitRepository + Kustomization for CRDs from pinned tags
│   │                   gateway-api v1.6.2, traefik chart v41.6.0, kube-prometheus-stack 91.4.1
│   ├── infrastructure.yaml  dependency tree
│   ├── applications.yaml    per-app Kustomizations
│   └── ghcr-pat.sops.yaml
├── infrastructure/
│   ├── storage/        local-path-provisioner
│   ├── backup/         k8up (restic to Garage S3 via egress relay)
│   ├── egress/         tailscale-relay (user-owned egress for shared-in targets)
│   ├── keel/           Keel updater for tier-2 :latest apps
│   ├── knative/        Knative Operator v1.23.1 + Serving 1.23.0 (net-gateway-api)
│   ├── monitoring/     kube-prometheus-stack + metrics-server + Gatus
│   ├── network/
│   │   ├── cilium/     Cilium HelmRelease
│   │   └── ipam/       CiliumLoadBalancerIPPool + L2AnnouncementPolicy
│   └── ingress/
│       ├── cert-manager/  HelmRelease + Namespace + cloudflare-dns01 secret
│       ├── traefik/       Gateway + certificates + middleware + Namespace
│       └── tailscale/     HelmRelease + Namespace + operator-oauth secret
└── applications/       one directory = one namespace
    ├── apex/           tier-2 site + SSH TUI (apex repo image, Keel-polled)
    ├── glob/           tier-2 blog at blog.0xbf.ch (glob repo image, Keel-polled)
    ├── exhib/          tier-2 gallery at gallery.0xbf.ch (exhib repo image, Keel-polled)
    ├── atuin/          tier-1 shell history (atuin.0xbf.ch, k8up)
    ├── agh/            AdGuard Home (LAN DNS edge)
    ├── ddns/           favonia/cloudflare-ddns (0xbf.ch to home IP)
    ├── dns/            knotd + kresd (internal. zone, resolver on OCI)
    ├── devil/          kata VM pod: ssh 2222, ghostty-web at devil.internal
    ├── forgejo/        tier-1 git forge at git.0xbf.ch
    ├── pds/            tier-1 ATProto PDS at pds.0xbf.ch
    └── homepage/       dashboard
```

## Kustomization dependency tree

```
storage -> cilium -> ipam
               └──> cert-manager -> traefik -> tailscale
cilium also dependsOn prometheus-crds
monitoring also dependsOn prometheus-crds, traefik
traefik also dependsOn gateway-api-crds, traefik-crds
backup dependsOn k8up-crds
```

Dry-run validates all manifests in a Kustomization before apply. A CR without its CRD fails dry-run. No manifest in that Kustomization applies. This includes the HelmRelease that would create the CRD. So:

- Do not put CRs and their CRD HelmRelease in same Kustomization. `ipam` is separate from `cilium`. Cert-manager CRs are in `traefik` dir which depends on `cert-manager`.
- Gateway API and Traefik CRDs are installed from pinned GitRepository tags in `cluster/crds.yaml` (`prune: false`).
- Cilium CRDs are created by operator at runtime. Do not vendor them.
- Bump chart version and matching CRD GitRepository tag in same commit.

## Component notes

- **cilium 1.20.2** (`network/cilium/cilium.yaml`): Set `kubeProxyReplacement: true`. Set `ipam.mode: kubernetes`. Set `gatewayAPI.enabled: false`. Traefik owns Gateway API. Set `k8sServiceHost: localhost` and `k8sServicePort: 7445` for Talos apid proxy. Enable privileged cgroup settings for Talos. Enable `prometheus.enabled` and Hubble metrics. This needs prometheus CRDs. So `cilium` depends on `prometheus-crds`. LB-IPAM pool is `10.10.20.128/25`. L2 announce is on `rbpi` `end0`. See `network/ipam/pool.yaml`. Gateway LB address is `10.10.20.128`.

- **kata-containers 3.32.0** (rbpi + rzbl): Declare in node schematic (`talos/schematic.rbpi.yaml`, `talos/schematic.rzbl.yaml`). Register only `kata-qemu` handler. Extension includes Cloud Hypervisor binary but no `clh` handler. CLH is not usable without custom extension. RuntimeClass `kata-qemu` is in `infrastructure/kata/`. It is cluster-scoped. It has no node selector. Pods with this RuntimeClass must land on kata-enabled node. That excludes tainted OCI node. `/dev/kvm` exists on Pi 5. Blade i7-9750H has VT-x.

- **traefik chart 41.6.0** (`ingress/traefik/traefik.yaml`): Values schema is strict. `globalArguments` does not exist. Use `global` block. Redirects use `http.redirections.entryPoint`. Do not use `redirectTo`. Listeners must match entrypoint ports `8000/8443/22/2222`. Do not use Service ports `80/443/22/2222`. Set `providers.kubernetesGateway.experimentalChannel: true`. TCPRoute needs this. Gateway-api v1.6.2 includes ValidatingAdmissionPolicy `safe-upgrades.gateway.networking.k8s.io`. This blocks experimental CRDs over standard CRDs. Previous switch blocked `gateway-api-crds` in retry loop. To change channel, delete VAP and binding first. Chart default Gateway is disabled. `gateway.yaml` owns Gateway. Dashboard uses IngressRoute `ingressRoute.dashboard` at `dashboard.internal` with `internal-allowlist`. This is the only IngressRoute. Chart exposes Prometheus metrics. ServiceMonitor scrapes them.

- **gateway.yaml**: Listeners are `web` `8000` HTTP and `websecure` `8443` HTTPS. `websecure` has no hostname. It matches all hostnames. It uses cert `wildcard-domain-tls`. Do not add hostname filter. Filter breaks bare domain. Other listeners: `websecure-internal` `8443` for `*.internal` with `wildcard-internal-tls`; `apexssh` `22` TCP for apex SSH with `hostPort: 22`; `devilssh` `2222` TCP for devil SSH with no hostPort and no WAN; `gitssh` `2223` TCP for forgejo SSH.

- **certificates.yaml**: Use Let's Encrypt via Cloudflare DNS-01. Create `wildcard-domain` cert for `0xbf.ch` and `*.0xbf.ch`. Internal `*.internal` cannot use Let's Encrypt. Use internal CA chain: selfsigned bootstrap to 10y CA in `cert-manager` ns to CA ClusterIssuer to 1y wildcard. See file for details.

- **tailscale operator 1.102.3**: Reads OAuth from Secret `operator-oauth`. Do not rename it. OAuth client has `tag:k8s` and `tag:k8s-operator`. Operator can mint authkeys only for tags managed by client tags. Set `tagOwners` so tags own each other. Client tags are fixed at creation. Wrong tags require new client and new sops secret. Proxy pods get `tag:k8s` via `proxyConfig.defaultTags`.

- **tailscale on nodes**: Nodes run `ext-tailscale` Talos extension. Config is in `talos/patches/all/02-tailscale.sops.yaml`. Nodes use `tag:infra`. This is different from operator identity.

- **monitoring** (`infrastructure/monitoring/`): Use kube-prometheus-stack 91.4.1, metrics-server 3.14.0, Gatus v5.36.0 at `status.internal`. Disable kubeControllerManager, kubeScheduler, kubeEtcd, kubeProxy scrapes. They are unreachable on Talos or replaced by Cilium KPR. Metrics-server needs `--kubelet-insecure-tls`. Keep Prometheus retention 7d/8GB on local-path. Grafana admin is in `monitoring-credentials.sops.yaml`. Set selectors `NilUsesHelmValues: false` so new ServiceMonitors are picked up. Alertmanager receiver is pending (ntfy/Discord/Telegram).

- **cert-manager 1.21.2**: Set `install.crds` and `upgrade.crds` to `CreateReplace`. Set `crds.enabled: true`.

- **dns (knotd + kresd on OCI)**: `resolver` pod in `dns` ns is the only workload on OCI control plane. Taint stays. It needs clean egress on port 53. Home ISP firmware hijacks DNS on home segment. Do not point router DNS to LAN resolver. That creates loop. See pi-hole discourse thread for router model. Kresd does public recursion with DNSSEC. It stubs `internal.` to knotd on loopback with `authoritative: true, dnssec: false`. Knotd is authority for `internal.` zone. Service `resolver` is pinned to `10.96.0.53`. AGH uses this IP as sole upstream. Home segment runs only AGH. Zone data is in `applications/dns/knot/internal.zone`. ConfigMap hash rolls pod on change.

- **pihole 2026.07.2**: Removed. Replaced by AdGuard Home. FTL v6 blocked `*.internal` (RFC 9760 hardening). AGH does not block it.

- **agh (AdGuard Home) v0.107.79**: LAN DNS edge at `10.10.20.153`. Use static LB IP from Pi-hole. Router DHCP and Tailscale split DNS use this IP. Do not let IP float. Forwards all queries to kresd. AGH handles `*.internal`. Config seed is from `agh-config.sops.yaml` Secret `agh-config`. It holds whole `AdGuardHome.yaml` as `stringData`. InitContainer copies it to PVC only if absent. AGH then owns file on PVC. UI edits persist. Seed is git intent. To re-seed, delete `conf/AdGuardHome.yaml` on PVC. Admin UI is at `agh.internal`. Middleware copy is in `agh` ns. HTTPRoute ExtensionRef is same-namespace only.

- **forgejo 16.0.5** (`applications/forgejo/`, tier-1): Git forge at `git.0xbf.ch` on `websecure` with LE wildcard cert. Image is `codeberg.org/forgejo/forgejo:16.0.5` pinned. Use one PVC at `/data` (10Gi, local-path, `Recreate`). InitContainer creates `app.ini` from `forgejo-config` ConfigMap and `[security]` block from `forgejo-secrets.sops.yaml`. File then lives on PVC. To recreate, delete `/data/gitea/conf/app.ini`. InitContainer creates admin user. Registration is closed. Git SSH uses `gitssh` listener and entrypoint on `hostPort: 2223`. Use `ssh://git@git.0xbf.ch:2223/owner/repo.git`. Router forwards `2223` to `10.10.20.10`. Dev box keeps `2222`. Apex uses `22`. SSH host keys are at `/data/ssh` on PVC. Mailer is disabled. Plan Proton SMTP token after Proton Premium domain is live. K8up Schedule is in ns (daily `03:00` + prune). Jobs fail until NAS tailnet path is fixed.

- **pds 0.4.5034** (`applications/pds/`, tier-1): ATProto PDS at `pds.0xbf.ch` on `websecure` with LE wildcard. Image `ghcr.io/bluesky-social/pds:0.4.5034` pinned. Use one PVC at `/pds` (10Gi, local-path, `Recreate`). Configure via ConfigMap `pds-config` and Secret `pds-secrets` (JWT, admin password, PLC rotation key). No initContainer. Handles: `PDS_SERVICE_HANDLE_DOMAINS` stays at default `.pds.0xbf.ch`. Accounts are `<name>.pds.0xbf.ch`. No per-account DNS is needed. `*.pds.0xbf.ch` HTTPRoute has own listener `websecure-pds` and cert `pds-handles-wildcard-tls`. Second-level wildcard is needed because `*.0xbf.ch` covers one label only. DNS `*.pds.0xbf.ch` is kept by ddns. Both routes are in one `httproute.yaml` as `---` documents. Route serves `/.well-known/atproto-did` from DB by Host header. Route is in `pds.` ns. Unrouted `*.0xbf.ch` subdomains 404 at Traefik. Custom handles (bare `0xbf.ch` or friends domains) are rejected at account creation. They require service domain. Front label must be 3-18 chars and not reserved (`admin`, `www`, `pds`, etc. fail with `Reserved handle`). They are allowed on handle update if handle resolves to DID. Add TXT `_atproto.<domain>` with `did=did:plc:...` then run `goat account login` and `goat account update-handle`. PDS updates PLC `alsoKnownAs`. Service is `pds-http`, not `pds`. Service `pds` creates `PDS_PORT` service-link env that breaks image `PDS_PORT=3000`. PDS then binds random port. Email is deferred (need Proton SMTP). K8up Schedule is `03:30` backup / `05:30` prune.

- **atuin 18.24.2** (`applications/atuin/`, tier-1): Shell history at `atuin.0xbf.ch` on `websecure` with LE wildcard. Image `ghcr.io/atuinsh/atuin:18.24.2` pinned. Image tag drops `v` from release `v18.24.2`. Use SQLite at `/config/atuin.db` on PVC (5Gi, local-path, `Recreate`). Same shape as forgejo/pds, no Postgres. Configure via `atuin-config` ConfigMap. No sops Secret. Set `ATUIN_OPEN_REGISTRATION=true` for first user, then `false`. Image entrypoint is `atuin-server`. Deployment passes `start`. Set `enableServiceLinks: false` and explicit `ATUIN_PORT`/`ATUIN_HOST`. Service `atuin` creates service-link `ATUIN_PORT=tcp://...`. Upstream ignores form with warning. Explicit env removes ambiguity. Probes use `/healthz`. History is client-side encrypted. Server stores blobs it cannot read. No server key. K8up Schedule `04:30/06:30`. Clients use `https://atuin.0xbf.ch` as `sync_address` in `~/.config/atuin/config.toml`.

- **apex 0.1.0** (`applications/apex/`, tier-2): Site + WASM app at `0xbf.ch` and SSH portfolio on `22`. Image `ghcr.io/bfeitknecht/apex:latest` multi-arch arm64. Use `imagePullPolicy: Always` and Keel. Two Deployments share image. `apex` serves HTTP `8080`. `apex-tui` serves SSH `2222`. SSH allows any username. No client key. Secret `apex-ssh-host-key` holds host key. Keep same key to avoid client warnings. HTTPRoute `apex` routes `0xbf.ch` to `apex:80` on `websecure`. TCPRoute `apex-ssh` routes `22` to `apex-tui:2222` on `apexssh`. Gatus checks both.

- **glob 0.1.0** (`applications/glob/`, tier-2): Typst blog at `blog.0xbf.ch`. Image `ghcr.io/bfeitknecht/glob:latest` multi-arch. Use `imagePullPolicy: Always` and Keel. SWS serves `8080`. HTTPRoute routes `blog.0xbf.ch` to `glob:80` on `websecure`. Probe is `GET /`. Bundle vendors `thyme` and `exemel`. Release waits for `exemel` on `@preview`.

- **exhib** (`applications/exhib/`, tier-2): Hugo gallery at `gallery.0xbf.ch`. Use 3 containers and PVC at `/data`. `sws` is `joseluisq/static-web-server:2.44.1-alpine` serving `/data/public` on `8080`. `uploader` is `busybox:1.37.0` waiting for uploads. `processor` is `ghcr.io/bfeitknecht/exhib:latest` running Hugo. PVC `exhib-site` is 50Gi local-path `Recreate`. ConfigMap `exhib-sws` is from `sws.toml` and enables health. HTTPRoute routes `gallery.0xbf.ch` to `exhib:80` on `websecure`. Uploads use `scripts/upload-item.sh` and Kubernetes API. Processor converts files and builds site.

- **homepage v2.4.0**: Dashboard at `homepage.internal` with allowlist middleware copy in `homepage` ns. Config uses `settings.yaml` + `kubernetes.yaml` via ConfigMap (rolls on change) and `services.yaml` via Secret `homepage-services` (sops, holds AGH creds and Grafana token). Widgets: adguard, gatus, grafana. Cluster stats via `kubernetes.yaml` RBAC (`rbac.yaml` with SA + ClusterRole incl. `metrics.k8s.io` from metrics-server). `HOMEPAGE_ALLOWED_HOSTS` pins Host header.

- **tailscale-relay** (`infrastructure/egress/tailscale/`, ns `egress`): User-owned egress for shared-in targets. Tailscale link shares are user-scoped. Shared-in machine is visible only to recipient user devices. Tagged machines cannot reach shared-in machines. Tags are stripped across shares. Node `tag:infra` and operator `tag:k8s` cannot reach shared-in targets. Relay uses untagged authkey. Device is owned by user and is inside share scope. TUN mode uses `/dev/net/tun` hostPath and `NET_ADMIN`. Socat sidecar forwards listeners to tailnet targets (now `3900` to `100.96.72.126:3900` for Garage). Add targets with extra `TCP-LISTEN` args in `relay.yaml`. State is on 1Gi local-path PVC. Key survives restart. Authkey needed only on first join `TS_AUTH_ONCE`. Disable key expiry on `k8s-relay` device after join. Authkey is in `relay-authkey.sops.yaml` (`tailscale-relay-authkey`). It must stay untagged. Workloads reach target via `tailscale-relay.egress.svc.cluster.local:<port>`. For non-shared tailnet targets, use operator egress Services with `tag:k8s`.

- **devil (kata VM, `applications/devil/`)**: NixOS VM image is from omni flake. This repo owns pod, routing, terminal page. Access via one hostname `devil.internal` (knot wildcard to gateway LB). No DNS record. **ssh 2222** via `devilssh` entrypoint/listener (no hostPort, LAN + tailnet only; WAN `2222` reserved for dev box) to TCPRoute `ssh` to headless Service to VM sshd (pubkey-only, host keys on PVC). **ghostty-web** via HTTPRoute `devil` (`websecure-internal` with `internal-allowlist` copy in `devil` ns; only middleware, no basic-auth) to headless Service `7681` to ttyd in VM (`-I /srv/ghostty-web/index.html login`). Page is `ghostty-web/index.html` (ConfigMap `devil-ghostty-web`, hash-rolled; ghostty-web from esm.sh CDN, ttyd wire protocol). Auth is `login` prompt. PAM checks bf password (omni sops `login/devil`). Shell has full home config. Service must be headless. Kata VM bypasses Cilium service translation both ways. ClusterIP dial times out. Clients use pod IP via Endpoints. State is on `devil-pvc` (subPaths `home`/`ssh`; was `devil-state`, see ROADMAP migration runbook).

- **k8up 4.10.0** (`infrastructure/backup/k8up/`): Restic to Garage S3 on friend NAS (Garage on `3900` plain HTTP; WireGuard transport, restic encrypts at rest). Endpoint is relay Service `http://tailscale-relay.egress.svc.cluster.local:3900`. NAS `ts.net` name is MagicDNS only. Kresd and CoreDNS NXDOMAIN it. IP literal is unreachable from pods. See tailscale-relay note for why. Friend prerequisites (verified 2026-10-15): Garage `s3_api.bind_addr = "[::]:3900"`, NAS firewall allows `3900` on tailscale0, ACL `src: autogroup:shared -> 100.96.72.126:3900`. PVC discovery is namespace-scoped. K8up backs up PVCs in Schedule namespace only. App opts in by adding `k8up.io/v1` Schedule to its dir. First Schedule is in `applications/forgejo/` (monitoring/agh excluded). Operator holds backend as global env in `backup-credentials.sops.yaml` (`BACKUP_GLOBALS3ENDPOINT/BUCKET`, `BACKUP_GLOBALACCESSKEYID/SECRETACCESSKEY`, `BACKUP_GLOBALREPOPASSWORD`). Per-namespace Schedules need no backend. Times use `Europe/Zurich`. Repo password `k8up-password` is only key to backups. Do not rotate it. Verify with `.private/backup.md`.

- **teleport (removed 2026-10-24)**: CE access plane (`infrastructure/teleport/`, LB `10.10.20.154`, `teleport.internal`, devil agent) was removed after friend demo. Dir and Kustomization gone. Devil agent wiring gone. `dependsOn: teleport` gone. Devil now uses ssh `2222` and ghostty-web.

## Application tiers

Apps deploy in 3 tiers with different release flows. Public edge is shared. Tier 2/3 platform (Keel, Knative Serving v1.23.0 via Operator with net-gateway-api, `{{.Name}}.0xbf.ch` template) is implemented, pending next tag.

Edge (all tiers): `0xbf.ch` + `*.0xbf.ch` are DNS-only (grey-cloud) A records. Cloudflare handles DNS only. Traffic goes direct to WAN IP `31.164.81.63`. No Cloudflare proxy. Owner rejects orange cloud. Records are kept by favonia/cloudflare-ddns updater (`applications/ddns/`, Zone token in sops Secret). Router forwards `443/80` to `10.10.20.10` (rbpi). Zyxel only NAT-forwards to DHCP-known devices and rejects LB IP `10.10.20.128`. So Traefik binds `hostPort` `80/443` on node for WAN. LB IP serves LAN clients. Traefik terminates LE wildcard cert `wildcard-domain-tls` (Cloudflare DNS-01) and routes: tier-1/tier-2 via HTTPRoutes, whims via per-KSvc HTTPRoutes from Knative net-gateway-api layer on Gateway. No catch-all is needed. Zone SSL mode must be `Full (strict)`. No Flux image-automation controllers. Do not install them. Do not switch OCIRepository off semver.

- **Tier 1. Tree-managed apps** (forgejo, pds, atuin; future immich): Define fully in this tree (Deployment with pinned image tag, ConfigMap/Secret, HTTPRoute). Update image with git edit + tag. OCI artifact gate applies. No polling. No Keel.
- **Tier 2. Dual-config apps** (apex `0xbf.ch`, glob `blog.0xbf.ch`, exhib `gallery.0xbf.ch`): Infra tree holds Deployment, Service, HTTPRoute, GHCR Secret. Deployment uses `ghcr.io/bfeitknecht/<app>:latest` with `imagePullPolicy: Always` and Keel annotations `keel.sh/trigger: poll`, `keel.sh/policy: force`, `keel.sh/match-tag: "true"`. Keel polls `latest` digest and restarts pod on new push. Infra tree does not change for site updates. Kustomization must ignore image field. If you do not ignore, Flux reverts Keel updates. Do not use Keel on tier 1 or tier 3. Do not use Keel on Knative Services. Keel handles only Deployment, StatefulSet, DaemonSet. Apex also has SSH frontend. `apex-tui` Deployment runs `/usr/local/bin/apex-ssh` via Service `apex-tui:2222`. It allows any username with no client key. It has no exec and no SFTP. It uses Gateway `apexssh` on port `22`. Use `ssh 0xbf.ch`. Forgejo git-ssh uses `2223`. Use `ssh://git@git.0xbf.ch:2223/...`. Dev box keeps `2222`. SOPS Secret `apex-ssh-host-key` holds host key. Keep same key to avoid client warnings. Exhib has 3 containers and 50Gi PVC. Keel watches `containers[2]` (processor).
- **Tier 3. Whim apps** (scale-to-zero): `whimsy` ns is outside Flux. Registry state, no git record. Each whim is self-contained repo: Dockerfile + code, no manifests. Deploy with `kn`: `brew install knative/client`; `kn service create <name> --image ghcr.io/bfeitknecht/<name>:<tag> --port <port> -n whimsy`, then `kn service update <name> --image ...:<new-tag>` (use SHA or version tag, not `:latest`; same image string rolls no revision). Default ServiceAccount holds GHCR Secret `dockerconfigjson` (sops), so private images pull with no per-service config. Domain template is `{{.Name}}.0xbf.ch`, so KSvc name sets domain. No labels needed. Whim controller was considered and rejected. `kn` is enough with zero custom code. Revisit only if per-push command annoys. Do not put whim manifests in this tree. Do not manage `whimsy` ns with Flux.

Note: Keel cannot update Knative Services (it handles Deployment/StatefulSet/DaemonSet only). Whims ns is registry-push power. Whim repos are personal. Pods are IPv4-only. DDNS cannot detect IPv6 prefix, so no AAAA until dual-stack. Knative config is in `KnativeServing` CR `spec.config` (operator overwrites ConfigMap edits). Domain template and Gateway wiring are there.

## Secrets

- SOPS + age. `.sops.yaml` matches `*.sops.yaml`. Flux decrypts with `sops-age` Secret in `flux-system`.
- Encrypted files: `cluster/ghcr-pat.sops.yaml`, `ingress/cert-manager/cloudflare-dns01.sops.yaml`, `ingress/tailscale/operator-oauth.sops.yaml`, `monitoring/grafana-credentials.sops.yaml`, `applications/agh/agh-config.sops.yaml`, `applications/apex/ghcr.sops.yaml`, `applications/apex/apex-ssh-host-key.sops.yaml`, `applications/glob/ghcr.sops.yaml`, `applications/exhib/ghcr.sops.yaml`, `applications/forgejo/forgejo-secrets.sops.yaml`, `applications/pds/pds-secrets.sops.yaml`, `infrastructure/backup/k8up/backup-credentials.sops.yaml` (Secrets with encrypted `data`/`stringData` only; plain structural fields), `talos/secrets.sops.yaml`, `talos/patches/all/02-tailscale.sops.yaml` (Talos configs, fully encrypted).
- Do not decrypt, encrypt, or edit SOPS files as agent. Owner does secrets locally.

## Cluster access

- `kubectl --kubeconfig kubeconfig ...` (repo root, gitignored). Server is K8s 1.35.3; local kubectl 1.33 is older. Skew warning is cosmetic.
- Endpoint is oci tailscale IP `100.73.186.19:6443` (kubeconfig for it). VCN allows only UDP `41641` (Tailscale WireGuard). No cluster ports are exposed. Manage from tailnet device only. Disable key expiry for node tailscale identities in admin console. Expired key takes endpoint down. Fallback: change `clusterEndpoint` to public IP, open security list, run `topf apply`.
- `talosctl --talosconfig talosconfig -e 10.20.20.10 -n <node-ip>` for node work.
- Nodes: `oci` control-plane tainted; no workloads except resolver; `rbpi` worker runs all workloads. Talos 1.14.2.

## Debugging playbook

1. `flux get kustomizations` Check first red/Unknown link.
2. `kubectl -n flux-system describe kustomization <name>` Shows build, dry-run, apply, or health error.
3. `kubectl -n <namespace> describe helmrelease <name>` Shows chart values schema error and bad key.
4. All Flux controllers in CrashLoopBackOff with `dial tcp 10.96.0.1:443: no route to host` means in-cluster service routing is down (often after Cilium restart). Fix datapath, then `kubectl -n flux-system rollout restart deployment`. Pods can lose Cilium endpoint after agent restart and stay detached.
5. Validate before tag: `kubectl kustomize <dir>` per dir; `kubectl apply --dry-run=server -f <file>` for `cluster/*.yaml`.
6. After chart bump, diff `values.yaml` against pinned values. Renamed key fails schema at install.
7. Node upgrades (`topf upgrade`): drain deadlocks on knative-serving PDBs (`webhook-pdb`/`activator-pdb` with `minAvailable: 80%` on 1-replica Deployment). That allows zero disruptions. PDBs are in Serving release manifest. Operator recreates them. No CR disables them (`high-availability.replicas` does not help: 80% rounds up, activator is HPA-managed). Flux-patching fights operator. Use `topf upgrade --delete-if-eviction-fails` or `TOPF_DELETE_IF_EVICTION_FAILS=true`. Topf retries blocked evictions as deletes and bypasses PDBs.

## Conventions

- Use Gateway API for all routing. Traefik dashboard IngressRoute is the only exception.
- Do not vendor manifests. Knative Serving uses Knative Operator (`infrastructure/knative/`): operator Deployment pinned to v1.23.1, `KnativeServing` CR (`kserving.yaml`) pinned to Serving 1.23.0. It creates CRDs, control plane, and net-gateway-api ingress at runtime. This follows Cilium pattern. Operator CRDs `KnativeServing`/`KnativeEventing` are NOT operator-created. They come from pinned upstream GitRepository in `cluster/crds.yaml` (knative/operator `knative-v1.23.1`, path `config/crd`). Without them, operator cannot watch CRs and dry-run fails. Operator Deployment has no probes. Upstream has none; it serves metrics on `9090`. Disable Istio plugin in CR (`spec.ingress.istio.enabled: false`). Without disable, install fails on missing Istio Gateway CRD. Keep all Knative config in CR `spec.config` block. Operator overwrites raw ConfigMap edits.
- CRDs come from pinned upstream GitRepository, from Helm charts, or from operator runtime. Do not vendor YAML files.
- Keep YAML comments only for load-bearing facts (listener port mapping, chart collisions, internal CA reason).
- Do not put hardcoded IPs in Helm values. Keep cluster-specific values in git resources (ipam pool, middlewares).
- Cluster DNS for `*.internal` is planned as Knot Resolver. Until then, `dashboard.internal` needs hosts entry or local DNS record at `10.10.20.128`.
- Owner runs nushell. Write all owner-facing commands in nushell syntax, not POSIX sh (`let` for session-local, `$env.X` only for export, `http get`/`http post` not curl, `from json` not `jq`, quoted `"@nameserver"` args).
