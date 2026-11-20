# Operations: the owner's runbook

Everything a person does by hand. Facts about how the cluster is built are in
`AGENTS.md`; open tasks are in `ROADMAP.md` and the atlas (`docs/web/index.html`,
"Needs you").

Commands are nushell. Run them from the infra repo root with
`$env.KUBECONFIG = "kubeconfig"`. The kubeconfig is a 24 h certificate: renew it with
`cd talos; topf kubeconfig | save -f ../kubeconfig`.

**Rule until backups work: test data only.** Every PVC is one disk on one node, and k8up
has no working backend yet (section 9). Real photos and files go in after that.

## 1. Accounts and sign-in (authentik)

authentik at `https://auth.0xbf.ch` is the login for every app that supports it.

| App | Address | How | Who |
| --- | --- | --- | --- |
| Forgejo | git.0xbf.ch | OIDC | developers |
| Grafana | grafana.internal | OIDC (PKCE) | developers; authentik Admins = Grafana admin |
| Immich | photos.0xbf.ch, immich.internal | OIDC | family, developers |
| Jellyfin | stream.0xbf.ch | OIDC via SSO plugin; "Sign in with 0xbf" | family, friends, developers; authentik Admins = admin |
| copyparty | files.0xbf.ch | forward auth; share links `/shr/` open | family, developers |
| Gallery upload | gallery.0xbf.ch/upload | forward auth | user bf only |
| Dawarich | dawarich.internal | OIDC (PKCE) | family, developers |
| Navidrome | navidrome.internal | forward auth; `/rest` open for Subsonic apps | family, friends, developers |
| opencode | opencode.internal | forward auth | developers |
| *arr, qBittorrent, Gatus | *.internal | forward auth | authentik Admins |
| PDS, atuin, AGH, Traefik dashboard | | own login | |

Groups: `family` and `friends` get media and photos, `developers` the dev tools,
`authentik Admins` the admin tools.

**Invite someone:** Admin > Directory > Invitations > Create, flow `invite`, single use.
Use the send action (mail from `noreply@0xbf.ch`) or copy the link. After they join:
Directory > Users > the user > Groups: `family` or `friends`. Jellyfin: they click
"Sign in with 0xbf"; for the TV or phone app they use Quick Connect from a logged-in
browser.

**Forgot password:** login page > "Forgot password?" mails a reset link (30 min).
Test mail: `kubectl -n authentik exec deploy/authentik-worker -- ak test_email <address>`.

**Locked out:** a one-time login link for 30 minutes:
`kubectl -n authentik exec deploy/authentik-server -- ak create_recovery_key 30 bf`, then open
`https://auth.0xbf.ch` + the printed path and set a password and a passkey.

## 2. Going live (one-time steps)

1. **Time Machine of echo** before the move to anti (the only real backup today).
   Password: `sops -d kubernetes/applications/samba/timemachine-secrets.sops.yaml | from yaml | get data.PASSWORD | decode base64 | decode`.
   Finder > Go > Connect to Server > `smb://10.10.20.145/TimeMachine`, user `timemachine`.
   System Settings > General > Time Machine > Add Backup Disk. First run on the LAN.
2. **Router:** forward WAN `2222` to `10.10.20.10` (the sshmux). Remove the old `2223` rule.
3. **Tailscale ACL:** `autoApprovers.routes` for `tag:infra` (snippet in `AGENTS.md`,
   tailscale on nodes).
4. **Immich admin:** sign up first at `https://immich.internal` (LAN or tailnet). The first
   account becomes admin; `photos.0xbf.ch` blocks admin sign-up on purpose.
5. **ntfy on the phone:** server `https://notify.0xbf.ch`, user `bf`, topic `alerts`.
   Password: `sops -d .private/ntfy-bf.sops.yaml`.
6. **Dawarich:** log in with the rotated demo admin (`.private/dawarich-admin.sops.yaml`) and
   change the email.

## 3. Streaming: Jellyfin and the *arr apps

Jellyfin at `stream.0xbf.ch`. One-time settings at `jellyfin.internal` > Dashboard:
Playback > Transcoding = NVIDIA NVENC; Networking > Known proxies = `10.244.0.0/16`;
Libraries: Movies `/data/media/movies`, Shows `/data/media/tv`, Music `/data/media/music`.

The apps reach each other as `http://<name>` on port 80 (`sonarr`, `radarr`, `prowlarr`,
`lidarr`, `qbittorrent`, `jellyfin`); you open them at `<name>.internal`.

Once:

1. qBittorrent (`qbittorrent.internal`): set the Web UI password (the first one is in the pod
   log: `kubectl -n media logs deploy/qbittorrent -c qbittorrent`). Options > Web UI: bypass
   authentication for localhost (gluetun needs it). Check the VPN:
   `kubectl -n media exec deploy/qbittorrent -c gluetun -- wget -qO- https://ipinfo.io/ip`
   must not print the home IP.
2. Prowlarr: Indexers > Add. Settings > Apps > add Sonarr and Radarr (Prowlarr server
   `http://prowlarr`, app server `http://sonarr` / `http://radarr`, API key from the app's
   Settings > General).
3. Sonarr (and Radarr the same way): Media Management > Root Folder `/data/media/tv`
   (`/data/media/movies`); Download Clients > qBittorrent: host `qbittorrent`, port 80,
   category `sonarr` (`radarr`); Connect > Emby/Jellyfin: host `jellyfin`, port 80, API key
   from Jellyfin > Dashboard > API Keys.

Each show: Sonarr > Add New > search > root folder `/data/media/tv`, monitor, quality profile,
"start search" > Add. qBittorrent downloads through the VPN, Sonarr moves the episode into
the library and tells Jellyfin. Watch at `stream.0xbf.ch`.

## 4. Photos, files, gallery, Time Machine

- **Immich** (`photos.0xbf.ch`): phone app server `https://photos.0xbf.ch`, "Login with 0xbf".
  Share links use the public name. No "back up all photos" before section 9.
- **copyparty** (`files.0xbf.ch`): login through authentik. Your folder `/u/bf`, the family's
  `/shared`. Share links (`/shr/...`) open without an account. `copyparty.internal` still takes
  the password of `bf` (in `copyparty-config`).
- **Gallery upload** (`gallery.0xbf.ch/upload`, only you): drag and drop photos and videos, or
  tap to pick from the iPhone. For a monthly album: kind collection, order "by capture date".
  Per-photo titles, crops and the cover: `just manifest` + `just upload` in the exhib repo.
- **Time Machine** for another Mac: as in section 2, step 1.

## 5. Remote development

- **devil** (`devil.internal`, LAN and tailnet): your NixOS VM. Repos in `~/src`, omni in
  `~/.config/omni` (`nh os switch` there). SSH: `ssh devil.internal` (port 2223 in the ssh
  config). Browser terminal: `https://devil.internal` (login prompt).
- **Rex on a Mac:** the Rex app lists `devil` (from `~/.config/rex/init.lua`; omni writes it on
  anti, echo has a copy). Or Add Remote Host > `ssh://devil.internal`. The server runs on devil
  as your user and keeps sessions while you are away.
- **Rex on the iPhone:** the iOS app is for enrolled testers only (enroll on the Rex Discord).
  Then: the phone on Tailscale, Add Remote Host > `ssh://bf@devil.internal:2223` with a key made
  in the app. devil accepts only listed keys: give the agent the app's public key and it adds it
  in omni. Until then: `https://devil.internal` in Safari.
- **opencode:** the server runs isolated in the cluster (`opencode.internal` in the browser).
  Terminal: `oc` on devil, or `ssh -t devil.internal oc` on a Mac (anti has `oc`). Sessions keep
  running when you close the laptop. Add a model provider once with `/connect`. Every bash
  command of the agent runs in a bubblewrap sandbox; it pushes as the Forgejo bot `opencode`
  to `bf/*` only.

## 6. Git hosting

Forgejo (`git.0xbf.ch`) holds `bf/{apex,infra,thyme,glob,exhib,omni}`. Clone and push over
SSH on the clean port: `ssh://git@git.0xbf.ch/bf/<repo>.git`.

GitHub mirror (GitHub keeps CI, GHCR images and the Typst Universe flow): a fine-grained
GitHub token for the six repos with **Contents** and **Workflows** read and write. Save it with
`input -s | save -f .private/github-mirror-token`; the agent sets up the push mirrors, moves
the remotes and Renovate to Forgejo. Then delete the two `repo-migration` tokens in Forgejo >
Settings > Applications.

## 7. Secrets

SOPS + age; Flux decrypts. Rules and the full list: `AGENTS.md`, Secrets. Patterns:

- Read one value (example): `sops -d <file> | from yaml | get data.<KEY> | decode base64 | decode`.
- A new secret from a value you have (never echoed):
  ```nu
  let v = (input -s "value: ")
  let f = "kubernetes/applications/<app>/<app>-secrets.sops.yaml"
  kubectl create secret generic <app>-secrets -n <app> --from-literal=$"KEY=($v)" --dry-run=client -o yaml
    | sops --encrypt --filename-override $f --input-type yaml --output-type yaml /dev/stdin | save -f $f
  ```
- Random values: the agent seeds them straight into sops (allowed since 2026-11-17).

## 8. Favicons look wrong

Every site uses the round mark (SVG, `favicon.ico`, `apple-touch-icon.png`). Old icons are
browser cache. Safari (quit it first):

```nu
for d in ["Favicon Cache" "Touch Icons Cache" "Template Icons"] { let p = ($env.HOME | path join "Library/Safari" $d); if ($p | path exists) { rm -r $p } }
```

Firefox (quit it first): `glob ~/Library/"Application Support"/Firefox/Profiles/*/favicons.sqlite | each { rm $in }`.
iPhone: Settings > Apps > Safari > Clear History and Website Data. Jellyfin, Immich and ntfy
keep their own icons.

## 9. Backups

k8up (restic) to Garage on a friend's NAS, through the `tailscale-relay` (details in
`AGENTS.md`). **Blocked:** the tailnet path works, the NAS answers on 80/443, but `3900` is
refused. The friend checks: the Garage container runs; `3900` is published from Docker;
`ss -ltnp` shows a listener on `0.0.0.0` or `[::]`; the NAS firewall allows `3900` on
`tailscale0`. When Gatus `garage via relay` turns green, the agent runs a restic round-trip
and a forgejo restore drill and adds Schedules for immich, copyparty, samba and the app
databases.

## 10. Workspace conventions

Every repo: a `justfile` with `fmt` / `fmt --check`, `check` (everything CI runs), `release`
(reads the version from the manifest, gates, tags, pushes; never commits) and `image` where
it applies. CI runs the format check and the lint on every push. Open gaps: no per-repo nix
dev shell yet; glob formats only its justfile and has no CI lint; omni has no justfile or CI.
