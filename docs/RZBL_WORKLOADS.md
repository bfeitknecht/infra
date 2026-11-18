# rzbl workloads: status and owner steps

Status 2026-11-17 (evening). All apps below run on rzbl (`nodeSelector: kubernetes.io/hostname: rzbl`).

| App                                              | Dir                                      | State               | Access                                                |
| ------------------------------------------------ | ---------------------------------------- | ------------------- | ----------------------------------------------------- |
| Jellyfin 12.4 (GPU)                              | `applications/media/`                    | **live**            | `jellyfin.internal`                                   |
| Sonarr 4.0.20                                    | `applications/media/`                    | **live**            | `sonarr.internal`                                     |
| Radarr 7.0.3                                     | `applications/media/`                    | **live**            | `radarr.internal`                                     |
| Prowlarr 2.7.0                                   | `applications/media/`                    | **live**            | `prowlarr.internal`                                   |
| Lidarr 3.1.6                                     | `applications/media/`                    | **live**            | `lidarr.internal`                                     |
| Navidrome 0.64.2                                 | `applications/media/`                    | **live**            | `navidrome.internal` (public later: `music.0xbf.ch`)  |
| Immich v3.4.1 (ML on GPU, `-cuda`)               | `applications/immich/`                   | **live**            | `immich.internal`                                     |
| Dawarich 1.23.0                                  | `applications/dawarich/`                 | **live**            | `dawarich.internal`                                   |
| Copyparty 1.20.26                                | `applications/copyparty/`                | **live**            | `copyparty.internal`, public `files.0xbf.ch`          |
| Time Machine (Samba)                             | `applications/samba/`                    | **live**            | `smb://10.10.20.145`                                  |
| Forgejo runner 13.2.1                            | `applications/forgejo-runner/`           | **live**            | none                                                  |
| Ollama 0.40.16 (GPU)                             | `applications/ollama/`                   | **live**            | cluster only: `ollama.ollama.svc.cluster.local:11434` |
| opencode web 1.19.5 (Kata)                       | `applications/opencode/`                 | **live**            | `opencode.internal` (authentik, group developers)     |
| Agent sandboxes (Kata, warm pool 1)              | `applications/agents/`                   | **live** (v1.29.0)  | none (SandboxClaim, port-forward)                     |
| qBittorrent 5.3.0 + gluetun v3.41.3 (Proton VPN) | `applications/qbittorrent/` (ns `media`) | **live**            | `qbittorrent.internal`                                |

Prepared apps have a Flux Kustomization with `suspend: true` in `cluster/applications.yaml`. Each needs one sops Secret from the owner. Agents do not create sops files.

Storage classes: `local-path-nvme` (rzbl NVMe, rbpi nvme0) and `local-path-ssd` (rzbl 4 TB SSD only). `local-path` picks a random path from the node list.

## Enable a prepared app

1. Create the secret file (commands below). Encrypt it with sops.
2. In `applications/<app>/kustomization.yaml`, uncomment the `*.sops.yaml` line.
3. In `cluster/applications.yaml`, delete `suspend: true` and its comment for the app.
4. Commit, tag, push.

## Secrets (nushell)

Seeded by the agent (random values piped straight into `sops --encrypt`, never printed): `immich-secrets`, `copyparty-config`, `forgejo-runner-secrets` (token minted by the Forgejo CLI), `dawarich-secrets`, `timemachine-secrets`. Time Machine password: `sops -d kubernetes/applications/samba/timemachine-secrets.sops.yaml | from yaml | get data.PASSWORD | decode base64 | decode`. Read a value: `sops -d kubernetes/applications/copyparty/copyparty-config.sops.yaml | from yaml | get data."copyparty.conf" | decode base64 | decode`.

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

### qBittorrent over Proton VPN: `applications/qbittorrent/qbittorrent-secrets.sops.yaml`

Proton Duo includes VPN Plus (P2P servers, port forwarding).

1. account.protonvpn.com > Downloads > WireGuard configuration. Platform: Router. Options: **NAT-PMP (Port Forwarding) on**, VPN Accelerator on. Server: any **P2P** server in Switzerland. Download the file.
2. Copy `PrivateKey` from the `[Interface]` section.

```nu
let key = "<PrivateKey from the .conf>"
kubectl create secret generic qbittorrent-secrets -n media --from-literal=$"WIREGUARD_PRIVATE_KEY=($key)" --dry-run=client -o yaml
  | save -f kubernetes/applications/qbittorrent/qbittorrent-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/qbittorrent/qbittorrent-secrets.sops.yaml
```

3. After the first start: qBittorrent Web UI at `qbittorrent.internal`. The temporary admin password is in the pod log (`kubectl -n media logs deploy/qbittorrent -c qbittorrent`). Set a password. Options > Web UI: enable **Bypass authentication for clients on localhost** (gluetun pushes the forwarded port through it). Options > Downloads: default path `/data/torrents`, category paths `/data/torrents/movies` and `/data/torrents/tv`.
4. In sonarr and radarr: Settings > Download Clients > qBittorrent, host `qbittorrent.media.svc.cluster.local`, port 80.
5. Check the tunnel: `kubectl -n media exec deploy/qbittorrent -c gluetun -- wget -qO- https://ipinfo.io/ip` must not print the home IP `31.164.81.63`.

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

### Renovate: `applications/renovate/renovate-secrets.sops.yaml`

GitHub > Settings > Developer settings > Fine-grained tokens > Generate. Resource owner `bfeitknecht`, repository access: `infra` (add more later), expiry 1 year. Permissions: Contents, Pull requests, Issues, Workflows: read and write; Metadata: read. Then, in the infra root (the token is read hidden and never echoed):

```nu
let tok = (input -s "GitHub token: ")
let f = "kubernetes/applications/renovate/renovate-secrets.sops.yaml"
kubectl create secret generic renovate-secrets -n renovate --from-literal=$"RENOVATE_TOKEN=($tok)" --dry-run=client -o yaml
  | sops --encrypt --filename-override $f --input-type yaml --output-type yaml /dev/stdin | save -f $f
```

Done 2026-11-18 (owner created the token; agent enabled Renovate in v1.39.0). Renovate runs Mondays 05:00 on rzbl and opens pull requests on `bfeitknecht/infra` (config `renovate.json5`).

### Dawarich admin

Dawarich creates `demo@dawarich.app` (admin) with the documented password `password` on first start. Rotated by the agent on 2026-11-18; the new value is in `.private/dawarich-admin.sops.yaml`: `sops -d .private/dawarich-admin.sops.yaml | from yaml | get data.password | decode base64 | decode`. Log in at `dawarich.internal`, change the email to yours. Dawarich supports OIDC with PKCE (authentik) later.

### ntfy on the phone

Install ntfy (App Store / F-Droid / Play). Settings > Default server: `https://notify.0xbf.ch`. Users: add `bf` with the password from `sops -d .private/ntfy-bf.sops.yaml | from yaml | get stringData.password`. Subscribe to topic `alerts`. Alertmanager and Gatus publish there.

## Media folder layout (TRaSH Guides)

One volume `media-files`, mounted at `/data` in jellyfin, sonarr, radarr and qbittorrent:

```
/data/torrents/{movies,tv,music}   qBittorrent downloads (categories radarr, sonarr, lidarr)
/data/media/{movies,tv,music}      Jellyfin libraries, *arr root folders
```

Jellyfin libraries: Movies `/data/media/movies`, Shows `/data/media/tv`. Sonarr root folder `/data/media/tv`, Radarr `/data/media/movies`. Lidarr root folder `/data/media/music`, Jellyfin library Music `/data/media/music`.

## Music streaming (next)

Lidarr fills `/data/media/music`. Two ways to stream it, both on rzbl over the same volume:

- **Jellyfin music library** (no new app): add library Music at `/data/media/music`. Phone apps: Finamp (iOS/Android) or Symfonium against `stream.0xbf.ch`.
- **Navidrome** (live at `navidrome.internal` since v1.37.0; public later `music.0xbf.ch`): a Subsonic server made for music (smart playlists, scrobbling, many clients: Symfonium, play:Sub, Feishin, Supersonic). Read-only mount of `media-files`.

Recommendation: start with the Jellyfin library (zero setup). Add Navidrome if the Subsonic clients are better for you.

## Public access (decision for the owner)

All apps are internal (`*.internal`, LAN + tailnet allowlist). Public needs an HTTPRoute on listener `websecure` with a `*.0xbf.ch` host. No DNS change (wildcard).

- **Jellyfin**: finish the setup wizard at `jellyfin.internal` first. The wizard creates the admin with no auth, so a public wizard is open to anyone. Then uncomment `httproute-public.yaml` in `applications/media/kustomization.yaml`: public at `stream.0xbf.ch`. Server name in Jellyfin: `0xbf`.
- **Immich**: first sign-up becomes admin. Same rule: sign up internal, then go public (`photos.0xbf.ch`).
- **Copyparty**: accounts come from the config, so it is public at once at `files.0xbf.ch` (route `copyparty-public`, live on un-suspend).
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

- No k8up Schedules for the new apps. Add them when the backup path works. Immich originals must have backups before real use.
- GPU time-slicing: `nvidia.com/gpu: 4`. Jellyfin, Ollama and Immich ML use 3 slots. Slots share 6 GB VRAM with no isolation. The GPU exporter (monitoring) takes no slot.
