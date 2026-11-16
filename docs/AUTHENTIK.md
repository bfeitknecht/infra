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

## Invite family and friends

Admin > Directory > Invitations > Create. Flow: `invite`. Single use. Send the link. They pick a username and password, then can add a passkey. Add them to `family` or `friends`.

## Connect an app (pattern)

One blueprint per app in `blueprints.yaml`: OAuth2 provider + application + group binding. The client secret lives in authentik and in the app's sops secret.

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
