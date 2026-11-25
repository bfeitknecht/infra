# Guide: using the homelab day to day

How to _use_ things. One-time setup and maintenance are in `docs/OPERATIONS.md`, how the cluster
is built is in `AGENTS.md` and `docs/COMPONENTS.md`, the map of where everything runs is in `README.md`.

## 1. Signing in (authentik)

One account, `bf`, for everything: `https://auth.0xbf.ch`. Apps with SSO show "Login with 0xbf"
or "Sign in with authentik".

- **Forgejo is the same account.** Your Forgejo user `bf` is linked to authentik. Use "Sign in with
  authentik" on `git.0xbf.ch`. The local Forgejo password (and its own passkey from 2026-09-29) is
  only the emergency fallback for the Forgejo admin.
- **The login asks for the password, then a passkey** (your second factor). The passkey must be the
  one registered _at authentik_ (`auth.0xbf.ch`, made 2026-11-17). Apple Passwords can confuse it
  with Forgejo's passkey for `git.0xbf.ch`.

### Passkey trouble: get back in and make it solid

1. One-time login link, valid 30 minutes (on a Mac with the kubeconfig):
    ```nu
    $env.KUBECONFIG = "kubeconfig"
    kubectl -n authentik exec deploy/authentik-server -- ak create_recovery_key 30 bf
    ```
    Open `https://auth.0xbf.ch` + the printed path.
2. In authentik: avatar > Settings > MFA Devices. Delete the old "Apple Passwords" passkey.
   Enroll a new passkey and give it a clear name (e.g. `apple-passwords-2026-11`).
3. Make it solid with a second way in:
    - **TOTP**: enroll an authenticator app (Proton Pass or Apple Passwords codes).
    - **Static recovery codes**: enroll "Static tokens" and keep them in Proton Pass.
4. In the Passwords app: search `0xbf`. For `auth.0xbf.ch` keep the password and the _new_ passkey
   only. For `git.0xbf.ch` you may delete the passkey (you sign in through authentik); keep the
   Forgejo password as a break-glass entry, ideally in Proton Pass.

## 2. Streaming

Watch at `https://stream.0xbf.ch` ("Sign in with 0xbf"). TV and phone apps (Jellyfin, Swiftfin,
Finamp for music): open the app, choose Quick Connect, approve the code in a logged-in browser
(Jellyfin > avatar > Quick Connect).

**Request a show or movie:** search in Jellyfin. Titles you don't have yet appear below your
library with a **Request** button (also whole seasons). The request goes through Seerr to
Sonarr/Radarr; the title shows up in Jellyfin when the download is done. Nothing seeds: a torrent
stops the moment it is complete. Admin view of all requests: `seerr.internal`.

By hand, in the *arr apps (after the one-time setup in `docs/OPERATIONS.md` section 3):

1. **Shows:** `sonarr.internal` > Add New > search > root folder `/data/media/tv`, monitor what you
   want, a quality profile, "start search" > Add.
2. **Movies:** `radarr.internal`, the same with `/data/media/movies`.
3. **Music:** `lidarr.internal` > `/data/media/music`; listen in Jellyfin or Navidrome
   (`music.0xbf.ch`, any Subsonic app).
4. Downloads run in qBittorrent through Proton VPN only (`qbittorrent.internal` shows progress).
   When done, the *arr app moves the file into the library and Jellyfin shows it within a minute.

## 3. Rex (persistent terminals on devil)

Rex keeps terminal sessions alive on devil, your NixOS VM in the cluster: start something, close
the laptop, pick it up from another device.

- **ssh:** `ssh bf@devil` (Tailscale SSH: no key, no port; the tailnet policy lets your own Macs
  and phones in). Zed remote and ish use the same host. devil has no sshd since 2026-11-24.
- **Mac:** open Rex. Add Remote Host > `https://deviler.tailac5960.ts.net` (devil's Rex server runs
  its own Tailscale node `deviler`, owned by your account, so only your devices get in). The Rex
  CLI's `devil` entry (`~/.config/rex/init.lua`, from omni) goes over `ssh://devil`.
- **iPhone:** the same `https://deviler.tailac5960.ts.net` (or scan the QR from
  `rex server tailscale pair` on devil). After a Rex reinstall: `ssh bf@devil rex server status`
  prints the sign-in link; open it, then disable key expiry for `deviler` in the admin console.
- No browser terminal: devil is SSH and Rex only.

## 4. Agentic development (opencode)

```
 browser ──> opencode.internal ──authentik──┐
 devil: oc ─────────────── direct ──────────┤
 Mac:  oc = ssh -t devil oc ──────────────┘
                                            v
                 opencode web server (Kata VM on rzbl, its own disk)
                   every bash command: bubblewrap sandbox
                   git: bot `opencode` ──HTTPS──> git.0xbf.ch (bf/*)
                                                     │ push mirror
                                                     v
                                                 github.com (CI, images)
```

- **One server, many clients.** The browser, `oc` on devil and `oc` on a Mac all show the same
  sessions. Sessions run in the server, so closing the laptop stops nothing.
- **Models:** `/connect` once in any client; the key stays on the server. Local fallback: Qwen 2.5
  Coder 7B on the GPU (Ollama).
- **Code lives on the server's disk** (`/home/node/Projects`). The agent clones `bf/<repo>` from Forgejo,
  works on a branch and pushes as the bot `opencode`. You review and merge on `git.0xbf.ch`; the
  mirror carries it to GitHub, where CI builds images.
- **What the agent can reach:** the model APIs, package registries, GitHub and Forgejo, nothing else.
  It cannot see the cluster, your LAN, devil or your keys. Each bash command also runs in its own
  bubblewrap sandbox: it may write only to the project directory and `/tmp`, cannot read secret
  paths or opencode's stored API keys, and gets only an allowlist of domains.
- **Where you do your own work:** devil (`~/src`, your keys, Rex sessions). The agent never touches
  devil's files.

## 5. Gallery and files

- **Gallery editor:** `https://gallery.0xbf.ch/upload` (only you). The `just manifest` editor in
  the browser: open any item or make a new one, add or delete files, set order, cover, crop,
  captions; **save** keeps a draft, **publish** puts it live (deleted files go to a trash folder).
  Monthly album: kind collection, sort "date".
- **Files:** `https://files.0xbf.ch` (your folder `/u/bf`, family folder `/shared`, share links
  open for anyone).
- **Photos:** `https://photos.0xbf.ch` and the Immich app (server `https://photos.0xbf.ch`).

## 6. What is `/.within.website/`?

The URL prefix that Anubis, the bot check in front of `0xbf.ch/cv`, reserves for itself: its
challenge script, its stylesheet (replaced by our monochrome one) and the endpoint that checks the
solved puzzle. The route sends that prefix to Anubis; everything else on the site goes straight to
apex. You need it as long as `/cv` is guarded: without it the check page cannot load its script
and nobody gets through. Remove Anubis and the prefix goes with it.
