# rzbl workloads: status and owner steps

Status 2026-11-16. All apps below run on rzbl (`nodeSelector: kubernetes.io/hostname: rzbl`).

| App | Dir | State | Access |
| --- | --- | --- | --- |
| Jellyfin 12.4 (GPU) | `applications/media/` | **live** | `jellyfin.internal` |
| Sonarr 4.0.20 | `applications/media/` | **live** | `sonarr.internal` |
| Radarr 7.0.3 | `applications/media/` | **live** | `radarr.internal` |
| Prowlarr 2.7.0 | `applications/media/` | **live** | `prowlarr.internal` |
| Immich v3.4.1 | `applications/immich/` | prepared, suspended | `immich.internal` |
| Dawarich 1.23.0 | `applications/dawarich/` | prepared, suspended | `dawarich.internal` |
| Copyparty 1.20.26 | `applications/copyparty/` | prepared, suspended | `files.internal` |
| Time Machine (Samba) | `applications/samba/` | prepared, suspended | `smb://10.10.20.145` |
| Forgejo runner 13.2.1 | `applications/forgejo-runner/` | prepared, suspended | none |
| Ollama 0.40.16 (GPU) | `applications/ollama/` | **live** | cluster only: `ollama.ollama.svc.cluster.local:11434` |
| opencode web 1.19.5 | `applications/opencode/` | prepared, suspended | `opencode.internal` |

Prepared apps have a Flux Kustomization with `suspend: true` in `cluster/applications.yaml`. Each needs one sops Secret from the owner. Agents do not create sops files.

Storage classes: `local-path-nvme` (rzbl NVMe, rbpi nvme0) and `local-path-ssd` (rzbl 4 TB SSD only). `local-path` picks a random path from the node list.

## Enable a prepared app

1. Create the secret file (commands below). Encrypt it with sops.
2. In `applications/<app>/kustomization.yaml`, uncomment the `*.sops.yaml` line.
3. In `cluster/applications.yaml`, delete `suspend: true` and its comment for the app.
4. Commit, tag, push.

## Secrets (nushell)

Generate random values with `openssl rand -hex 32`.

### Immich: `applications/immich/immich-secrets.sops.yaml`

```nu
let pw = (openssl rand -hex 24)
kubectl create secret generic immich-secrets -n immich --from-literal=$"DB_PASSWORD=($pw)" --dry-run=client -o yaml
  | save -f kubernetes/applications/immich/immich-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/immich/immich-secrets.sops.yaml
```

### Dawarich: `applications/dawarich/dawarich-secrets.sops.yaml`

```nu
let pw = (openssl rand -hex 24)
let skb = (openssl rand -hex 64)
kubectl create secret generic dawarich-secrets -n dawarich --from-literal=$"POSTGRES_PASSWORD=($pw)" --from-literal=$"SECRET_KEY_BASE=($skb)" --dry-run=client -o yaml
  | save -f kubernetes/applications/dawarich/dawarich-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/dawarich/dawarich-secrets.sops.yaml
```

### Copyparty: `applications/copyparty/copyparty-config.sops.yaml`

The whole config is the secret, because it holds account passwords. Edit accounts and volumes before you encrypt.

```nu
let pw = (openssl rand -hex 16)
let conf = $"[global]
  e2dsa, e2ts, no-robots
  hist: /w/.hist

[accounts]
  bf: ($pw)

[/]
  /w
  accs:
    A: bf
"
kubectl create secret generic copyparty-config -n copyparty --from-literal=$"copyparty.conf=($conf)" --dry-run=client -o yaml
  | save -f kubernetes/applications/copyparty/copyparty-config.sops.yaml
sops --encrypt --in-place kubernetes/applications/copyparty/copyparty-config.sops.yaml
print $"copyparty user bf password: ($pw)"
```

### Time Machine: `applications/samba/timemachine-secrets.sops.yaml`

```nu
let pw = (openssl rand -hex 16)
kubectl create secret generic timemachine-secrets -n samba --from-literal=$"PASSWORD=($pw)" --dry-run=client -o yaml
  | save -f kubernetes/applications/samba/timemachine-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/samba/timemachine-secrets.sops.yaml
print $"timemachine password: ($pw)"
```

On each Mac: System Settings > General > Time Machine > Add Backup Disk > Other. Or in Finder: Go > Connect to Server > `smb://10.10.20.145/TimeMachine`, user `timemachine`. Then pick the share in Time Machine. No mDNS: the share does not show up on its own. Keep the IP. Over Tailscale it works too (rbpi routes `10.10.20.0/24`).

### opencode web: `applications/opencode/opencode-secrets.sops.yaml`

Basic auth user is `opencode`.

```nu
let pw = (openssl rand -hex 16)
kubectl create secret generic opencode-secrets -n opencode --from-literal=$"OPENCODE_SERVER_PASSWORD=($pw)" --dry-run=client -o yaml
  | save -f kubernetes/applications/opencode/opencode-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/opencode/opencode-secrets.sops.yaml
print $"opencode web user opencode password: ($pw)"
```

Model: `ollama/qwen2.5-coder:7b` (local, GPU). Add cloud providers in the web UI (`/connect`). Keys are stored on the PVC in `~/.local/share/opencode`.

### Forgejo runner: `applications/forgejo-runner/forgejo-runner-secrets.sops.yaml`

Get a registration token: `https://git.0xbf.ch/-/admin/actions/runners` > Create new runner.

```nu
let token = "<paste token>"
kubectl create secret generic forgejo-runner-secrets -n forgejo-runner --from-literal=$"RUNNER_TOKEN=($token)" --dry-run=client -o yaml
  | save -f kubernetes/applications/forgejo-runner/forgejo-runner-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/forgejo-runner/forgejo-runner-secrets.sops.yaml
```

Also enable Actions in Forgejo: `[actions] ENABLED = true` in `app.ini` (the live file is on the PVC). Runner labels: `docker` (node:22) and `ubuntu-latest` (catthehacker act image). Jobs run in a privileged docker:dind sidecar on rzbl.

GitHub as mirror: per repo on Forgejo, Settings > Repository > Mirror settings > Push mirror to `https://github.com/bfeitknecht/<repo>.git` with a GitHub fine-grained PAT (contents: write).

## Public access (decision for the owner)

All apps are internal (`*.internal`, LAN + tailnet allowlist). Public needs an HTTPRoute on listener `websecure` with a `*.0xbf.ch` host. No DNS change (wildcard).

- **Jellyfin**: finish the setup wizard at `jellyfin.internal` first. The wizard creates the admin with no auth, so a public wizard is open to anyone. Then add a public route, for example `media.0xbf.ch` or `jellyfin.0xbf.ch`.
- **Immich**: first sign-up becomes admin. Same rule: sign up internal, then go public (`photos.0xbf.ch`).
- **Copyparty**: accounts come from the config, so it is safe to go public at once (`files.0xbf.ch`).
- **\*arr, Prowlarr, Dawarich**: keep internal.

Public route example (put into the app dir, add to `kustomization.yaml`):

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: jellyfin-public
  namespace: media
spec:
  parentRefs:
    - name: traefik-gateway
      namespace: ingress
      sectionName: websecure
  hostnames:
    - media.0xbf.ch
  rules:
    - backendRefs:
        - name: jellyfin
          port: 80
```

## Not done yet

- No download client (qBittorrent). Torrent traffic from the home IP needs a VPN decision.
- No k8up Schedules for the new apps. Add them when the backup path works. Immich originals must have backups before real use.
- GPU time-slicing: `nvidia.com/gpu: 4`. Jellyfin and Ollama use 2 slots. Immich ML can take a third: image tag `v3.4.1-cuda`, `runtimeClassName: nvidia`, limit `nvidia.com/gpu: 1`. Slots share 6 GB VRAM with no isolation.
