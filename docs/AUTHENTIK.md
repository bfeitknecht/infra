# Authentik: the one IdP

Decision 2026-11-16: authentik is the identity provider for all apps. Options and reasons are in `docs/IDENTITY.md`.

## What is in git

`applications/authentik/` (prepared, Flux Kustomization suspended):

- authentik 2026.8.5 (Helm chart, release `authentik`) on rzbl. Server + worker. No Redis (removed upstream).
- Own Postgres 17 on rzbl NVMe (`local-path-nvme`, 10Gi). k8up backs it up with `pg_dump`.
- Public at `https://auth.0xbf.ch` (route on `websecure`, wildcard cert, no DNS change).
- Blueprints in ConfigMap `authentik-blueprints` (`blueprints.yaml`). The worker applies them. Today: groups `family`, `friends`, and an invitation-only enrollment flow (slug `invite`). No open registration.

## Owner steps

1. Create the secret (nushell):

```nu
let skey = (openssl rand -base64 60 | str replace -a "\n" "")
let dbpw = (openssl rand -hex 24)
let adminpw = (openssl rand -hex 16)
(kubectl create secret generic authentik-secrets -n authentik
  --from-literal=$"AUTHENTIK_SECRET_KEY=($skey)"
  --from-literal=$"AUTHENTIK_POSTGRESQL__PASSWORD=($dbpw)"
  --from-literal=$"AUTHENTIK_BOOTSTRAP_PASSWORD=($adminpw)"
  --from-literal="AUTHENTIK_BOOTSTRAP_EMAIL=<your email>"
  --dry-run=client -o yaml)
  | save -f kubernetes/applications/authentik/authentik-secrets.sops.yaml
sops --encrypt --in-place kubernetes/applications/authentik/authentik-secrets.sops.yaml
print $"akadmin password: ($adminpw)"
```

Do not rotate `AUTHENTIK_SECRET_KEY` later. It signs sessions and tokens.

2. Uncomment `authentik-secrets.sops.yaml` in `applications/authentik/kustomization.yaml`.
3. Delete `suspend: true` (and its comment) for `authentik` in `cluster/applications.yaml`.
4. Commit, tag, push.
5. Log in at `https://auth.0xbf.ch` as `akadmin`. Then:
    - Create your own user, add it to group `authentik Admins`, set up a passkey. Deactivate `akadmin`.
    - Optional: remove `AUTHENTIK_BOOTSTRAP_*` from the secret. They only act on first start.

## Locked out (no admin can log in)

Happened 2026-11-17: `akadmin` was deactivated before the new user had a password or passkey. A recovery link logs in as a user once, with no password:

```nu
kubectl -n authentik exec deploy/authentik-server -- ak create_recovery_key 30 bf
```

`30` is minutes. The command prints a path. Open `https://auth.0xbf.ch` + that path. Then User settings > Password: set one. MFA devices: add a passkey. Check with `kubectl -n authentik exec deploy/authentik-db -- psql -U authentik -c "select username, is_active, left(password,1) from authentik_core_user"`: a password that starts with `!` is unusable.

Order for the first admin: create user, **set password**, add to `authentik Admins`, log out, log in as the new user, add a passkey, then deactivate `akadmin`.

## Invite family and friends

Admin > Directory > Invitations > Create. Flow: `invite`. Single use. Send the link. They pick a username and password, then can add a passkey. Add them to `family` or `friends`.

## Prepared apps: Forgejo and Jellyfin

Blueprints `forgejo.yaml` and `jellyfin.yaml` in `blueprints.yaml` create the OIDC provider, the application and the group bindings. After authentik runs:

**Forgejo** (group `developers`):

1. Add yourself to `developers` in authentik.
2. Admin > Providers > forgejo: copy the client secret.
3. Forgejo `https://git.0xbf.ch/-/admin/auths/new`: type **OAuth2**, provider **OpenID Connect**, name **`authentik`** (must match the redirect URL), client ID `forgejo`, client secret (pasted), auto-discovery URL `https://auth.0xbf.ch/application/o/forgejo/.well-known/openid-configuration`.
4. Link your existing Forgejo account on first SSO login (Forgejo asks).

**Jellyfin** (groups `family`, `friends`, `developers`):

1. Dashboard > Plugins > Repositories: add `https://raw.githubusercontent.com/9p4/jellyfin-plugin-sso/manifest-release/manifest.json`. Catalog: install **SSO Authentication**, restart.
2. Plugin settings, add provider name **`authentik`**: endpoint `https://auth.0xbf.ch/application/o/jellyfin/`, client ID `jellyfin`, client secret (from authentik), enabled, "Enable Authorization by Plugin" on.
3. Login link for users: `https://stream.0xbf.ch/sso/OID/start/authentik`. Web only: TV and phone apps keep Jellyfin passwords or Quick Connect.

## Who logs in where (2026-11-18)

| App | Host | How | Groups |
| --- | --- | --- | --- |
| Forgejo | git.0xbf.ch | OIDC (confidential) | developers |
| Grafana | grafana.internal | OIDC (public, PKCE) | developers; authentik Admins = Grafana Admin |
| Immich | immich.internal | OIDC (confidential, `immich-config`) | family, developers |
| Dawarich | dawarich.internal | OIDC (public, PKCE, env) | family, developers |
| Navidrome | navidrome.internal | forward auth + `X-authentik-username` (ExtAuth); `/rest` open for Subsonic apps | family, friends, developers |
| opencode, sandbox-1..3 | *.internal | forward auth | developers |
| Sonarr, Radarr, Prowlarr, Lidarr, qBittorrent, Gatus (status) | *.internal | forward auth | authentik Admins |
| Jellyfin | stream.0xbf.ch | none (SSO plugin does not support 12.x) | local users |
| copyparty, PDS, atuin, AGH, Traefik dashboard | | own login | (forward auth would break share links / no header support) |

Group meaning: `family` and `friends` get the media and photo apps, `developers` the dev tools, `authentik Admins` the admin tools. Put an invited person in the right group after they join.

## Invitations

Admin > Directory > Invitations > Create: flow `invite`, single use, optional expiry. Copy the link and send it yourself (authentik does not mail invitations). The person picks username, password, name and email. Then add them to `family` or `friends` (Directory > Users > the user > Groups).

## Forgot password

Login page > "Forgot password?" (flow `recover`): authentik mails a reset link from `noreply@0xbf.ch` (Proton SMTP, valid 30 min). Test mail: `kubectl -n authentik exec deploy/authentik-worker -- ak test_email <address>`.

## Connect an app (pattern)

One blueprint per app in `blueprints.yaml`: OAuth2 provider + application + group binding. The client secret lives in authentik and in the app's sops secret.

OAuth2 providers in a blueprint **must** set `grant_types: [authorization_code, refresh_token]`. The field defaults to empty there, and authentik then rejects every login with `invalid_request` ("Invalid grant_type for provider" in the server log). Forgejo SSO broke this way until 2026-11-17.

Forward auth (`forward_single`) serves one host per provider. A second hostname for the same app needs a second provider and application, both on the embedded outpost.

| App                       | Method                          | Notes                                                                                                                                         |
| ------------------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Forgejo                   | OIDC (native)                   | Site admin > Authentication sources > OpenID Connect, discovery `https://auth.0xbf.ch/application/o/forgejo/.well-known/openid-configuration` |
| Immich                    | OIDC (native)                   | Admin > Settings > OAuth                                                                                                                      |
| Jellyfin                  | SSO plugin (9p4)                | Web login only. TV/phone apps keep Jellyfin passwords or Quick Connect                                                                        |
| Open WebUI, Grafana       | OIDC (native)                   | env vars                                                                                                                                      |
| Copyparty, *arr, opencode | Forward auth (embedded outpost) | Traefik middleware `forwardAuth` to `http://authentik-server.authentik.svc/outpost.goauthentik.io/auth/traefik`                               |

## atproto (PDS) login

Not available yet. atproto OAuth is not OIDC. Add it as an authentik source when a bridge exists. See `docs/IDENTITY.md`.

## Open items

- Email (invitations by mail, password reset): needs SMTP (Proton). Until then, send invitation links by hand. An admin resets passwords.
- Brand: logo and title in Admin > System > Brands (or a blueprint).
