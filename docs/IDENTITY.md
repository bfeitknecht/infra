# Identity provider: options and recommendation

Draft 2026-11-16 for the owner. No decision is made. Nothing is deployed.

## Needs

1. The PDS (`pds.0xbf.ch`) is the central identity. The owner likes atproto.
2. Family and friends get access to some apps: Jellyfin first, then Immich, Copyparty.
3. Future apps should plug in the same way. OIDC is the common interface (Forgejo, Immich, Jellyfin plugin, Grafana, Open WebUI all speak OIDC).
4. Low effort for guests. They must not need to understand atproto.

## Facts that shape the choice

- **atproto OAuth is not OIDC.** It is OAuth 2.1 with DPoP and PAR. It gives a DID and a handle, no `id_token`, no email claim. Apps that want OIDC cannot use the PDS directly.
- So we need **one bridge**: an IdP that speaks OIDC to apps and accepts atproto login upstream.
- **Jellyfin has no native OIDC.** It needs the SSO plugin (9p4/jellyfin-plugin-sso). Native Jellyfin apps (TV, phone) log in with a Jellyfin password, not with SSO. For TV clients, local Jellyfin users stay useful anyway (Quick Connect helps).
- **Immich, Forgejo, Open WebUI, Grafana** have native OIDC.
- **Copyparty** uses its own accounts or a trusted header from a proxy (forward auth).

## Options

### A. Authentik as hub, PDS as one upstream source

- Authentik is the OIDC provider for all apps. Users live in Authentik.
- Sources (how a user logs in): atproto via a small bridge (see below), plus local password + passkey for guests.
- Guests: you **invite** them (Authentik invitation link, enrollment flow). They set a password or passkey. No atproto needed.
- atproto users: they log in with their handle. The bridge maps DID to an Authentik user.
- Pro: one admin UI, groups per app (`jellyfin-users`, `immich-users`), invitations, passkeys, forward-auth for apps without OIDC (copyparty, *arr).
- Con: heavy (server + worker + Postgres + Redis, about 1 GB RAM). One more critical service.

### B. Lighter hub: Pocket ID or Kanidm

- **Pocket ID**: passkey-only OIDC provider. Very small. Users are created by you or by signup links. No upstream sources, so no atproto login.
- **Kanidm**: small, strong, CLI-first. Users created by admin. No upstream federation.
- Pro: little to run. Con: atproto is not part of the flow.

### C. atproto-first bridge only

- A small OIDC provider whose only login is atproto OAuth (examples to evaluate: an "atproto OIDC" bridge; none is mature as of 2026-11).
- Guests create an account on **your PDS** (`name.pds.0xbf.ch`), then log in everywhere with it.
- Pro: pure, cool, one identity type. Con: guests must have an atproto account. PDS account creation needs invite codes and email (not set up yet). Immature software in the auth path.

### D. No IdP, local accounts per app

- You create Jellyfin users by hand. Same for Immich.
- Pro: zero new services. Fine for 3-5 family members and 1-2 apps. Con: does not scale, no single logout, password per app.

## Recommendation

1. **Now: D for Jellyfin.** Create local Jellyfin users for family. TV and phone apps need local users anyway. This unblocks sharing today.
2. **Next: A (Authentik)** when the second shared app (Immich) goes live. Invite family by link. Local password + passkey for them. Bind Jellyfin with the SSO plugin for the web UI. Immich, Forgejo, Open WebUI via OIDC. Forward-auth for copyparty and *arr.
3. **Add atproto as an Authentik source** when a bridge is good enough. Your login is then "sign in with pds.0xbf.ch". Guests keep passwords/passkeys. They never need atproto, but they can link one later.

This keeps the PDS as your central identity, gives guests the easiest path, and abstracts every app behind OIDC.

## Do guests sign up on the PDS?

Not as the default. A PDS account is a public social identity (handle, DID in the PLC directory). That is a big step for "watch a movie". Offer it as an option for people who want an atproto account.

## Open questions for the owner

- Hostname for the IdP: `auth.0xbf.ch` or `id.0xbf.ch`.
- Email for invitations and resets: needs Proton SMTP (also blocks PDS email).
- Run Authentik on rbpi or rzbl? rzbl has the RAM. rbpi has the critical apps.
