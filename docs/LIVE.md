# Going live

The owner's steps to make the apps usable. Written 2026-11-19.

**Rule until backups work: test data only.** k8up has no backend (Garage on
the friend NAS refuses `3900`). Every PVC is one disk on one node. Nothing you
put in Immich, copyparty or Jellyfin survives a disk loss. Upload real photos
and files only after step 9.

Commands are nushell. `kubectl` needs `--kubeconfig kubeconfig` from the repo
root, or `$env.KUBECONFIG`.

## 0. Before anything: Time Machine of echo

This is the one real backup, and it comes first because echo -> anti is next.
The share is on rzbl's 4 TB SSD (3.6 TB free; echo uses about 404 GiB).

1. Get the password:
    ```nu
    sops -d kubernetes/applications/samba/timemachine-secrets.sops.yaml | from yaml | get data.PASSWORD | decode base64 | decode
    ```
2. Finder > Go > Connect to Server > `smb://10.10.20.145/TimeMachine`, user
   `timemachine`, the password from step 1. Save it in the keychain.
3. System Settings > General > Time Machine > Add Backup Disk > the share.
4. Let the first backup finish on the LAN, with a cable if you can. Over Wi-Fi
   it takes hours.

Note: this backup lives on the cluster, on one disk. It is enough for the
move to anti. It is not off-site.

## 1. Your own access

- authentik at `https://auth.0xbf.ch`: your admin user with a passkey, and
  `akadmin` deactivated (docs/AUTHENTIK.md, first steps).
- Tailscale admin console: add `autoApprovers` (AGENTS.md, tailscale on
  nodes). Then a re-joined node needs no click.
- Router: forward WAN `2222` to `10.10.20.10` for the sshmux. Remove the old
  `2223` rule.
- Phone: ntfy app, server `https://notify.0xbf.ch`, user `bf`, topic
  `alerts`. Password:
    ```nu
    sops -d .private/ntfy-bf.sops.yaml
    ```

## 2. Streaming (Jellyfin at `stream.0xbf.ch`)

Jellyfin is public already. It has no SSO (the plugin does not load on 12.x):
make local users.

1. `https://jellyfin.internal` > Dashboard:
    - Playback > Transcoding: hardware acceleration **NVIDIA NVENC**.
    - Networking > Known proxies: `10.244.0.0/16`.
    - Users: make one user per person. Turn off "show on login screen".
2. Libraries (they exist as folders on `media-files`): Movies
   `/data/media/movies`, Shows `/data/media/tv`, Music `/data/media/music`.
3. Something to watch. Copy a test file straight into the library
   (copyparty does not mount `media-files`):
    ```nu
    let pod = (kubectl get pod -n media -l app.kubernetes.io/name=jellyfin -o name | lines | first | str replace 'pod/' '')
    kubectl cp ~/Movies/test.mkv $"media/($pod):/data/media/movies/test.mkv"
    ```
    Then Dashboard > Libraries > Scan. Or use the *arr apps:
    - `prowlarr.internal`: add indexers, connect Sonarr, Radarr, Lidarr.
    - `qbittorrent.internal`: it downloads through Proton VPN only (gluetun).
    - `sonarr.internal` / `radarr.internal`: root folders `/data/media/tv`,
      `/data/media/movies`; download client qBittorrent.
4. Test from outside: phone on mobile data, `https://stream.0xbf.ch`. Play a
   file that forces a transcode (lower the quality) and watch the GPU panel on
   the Grafana home dashboard.
5. Apps: Jellyfin, Swiftfin, or Finamp for music. Navidrome
   (`navidrome.internal`, SSO) is the alternative for music.

## 3. Invite the first users

1. authentik > Directory > Invitations > Create. Flow `invite`, single use.
   Send it with the email action (from `noreply@0xbf.ch`) or copy the link.
2. After they join: Directory > Users > the user > Groups: `family` or
   `friends`.
3. What each group gets: docs/AUTHENTIK.md ("Who logs in where").
   Jellyfin is separate: make the local Jellyfin user as in step 2.

## 4. Files (copyparty at `files.0xbf.ch`)

- Public, accounts from the Secret `copyparty-config` (not SSO). Your
  password:
    ```nu
    sops -d kubernetes/applications/copyparty/copyparty-config.sops.yaml | from yaml | get data."copyparty.conf" | decode base64 | decode
    ```
    The output includes the password. Do not paste it anywhere.
- Try: upload, share links. copyparty has its own volume (`copyparty-files`),
  not the media library.
- More accounts: ask the agent. It seeds a password straight into sops, and
  you read it with the command above.

## 5. Photos (Immich at `photos.0xbf.ch`)

- **First: create the Immich admin at `https://immich.internal`** (LAN or
  tailnet). The first sign-up becomes admin; the public name blocks admin
  sign-up on purpose. Use your authentik email.
- Public at `https://photos.0xbf.ch` (also `immich.internal`). Login with
  authentik: only `family` and `developers` get in, so put relatives in
  `family` (step 3).
- The mobile app: server `https://photos.0xbf.ch`, then "Login with
  authentik". Works anywhere, no internal CA needed.
- Share links (albums, single photos) use `photos.0xbf.ch`. A link opens
  without an account.
- Upload a few test photos. Check that face and object detection run on the
  GPU.
- Do not turn on "backup all photos" in the app before step 9.

## 6. Other apps worth a look

- `https://git.0xbf.ch`: Forgejo, SSO for `developers`.
- `atuin.0xbf.ch`: shell history sync.
- `dawarich.internal`: location history (change the demo admin first, see
  the atlas NEEDS).
- `status.internal` (Gatus) and `grafana.internal`: what is up.

## 7. When something breaks

- The atlas `docs/web/index.html` lists every app, host and open task.
- Gatus sends alerts to ntfy after 3 failures.
- AGENTS.md "Debugging playbook".

## 8. The anti switch

omni `docs/MIGRATION.md`. Time Machine (step 0) must be complete before you
reset echo.

## 9. Backups (before real data)

1. The friend's NAS answers on `3900` (Gatus `garage via relay` turns green).
2. The agent runs a restic round-trip and a forgejo restore drill.
3. Schedules for `immich`, `copyparty`, `samba` (Time Machine) and the
   app databases. Media (`media-files`) can be downloaded again: decide if it
   is worth the space.
4. Then: real photos into Immich, real files into copyparty.
