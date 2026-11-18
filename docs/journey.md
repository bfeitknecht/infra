---
title: "GENESIS: a homelab journey"
sub_title: "From one Pi to a three-node Talos cluster, in 66 days"
author: Basil Feitknecht
theme:
  override:
    intro_slide:
      title:
        font_size: 3
    slide_title:
      font_size: 2
---

<!--
Present: `presenterm docs/journey.md`. Sizes (font_size, title sizes) work in
kitty >= 0.40 only. Elsewhere, present in a window with a large font, e.g.
`ghostty --font-size=26 -e presenterm docs/journey.md`.
-->

The idea
===
<!-- font_size: 2 -->

<!-- column_layout: [3, 2] -->
<!-- column: 0 -->

A personal platform that I own end to end:

- my **site**, **blog**, **gallery** and **git** on my own hardware
- **identity** for family and friends in one place
- **media**, **photos** and **files** without a cloud subscription
- coding **agents** that cannot hurt anything
- everything **declared in git**, nothing clicked together

<!-- column: 1 -->

```
edit -> commit -> tag vX.Y.Z
  -> CI publishes OCI artifact
  -> Flux reconciles
```

The cluster only runs published tags.
A broken tag breaks reconcile until the next one.

<!-- end_slide -->

By the numbers
===
<!-- font_size: 2 -->

|              |                                              |
| ------------ | -------------------------------------------- |
| days         | **66** calendar, **38** active               |
| repositories | **6**: infra, apex, exhib, glob, thyme, omni |
| commits      | **449** (plus **107** merged pull requests)  |
| releases     | **153** tags, **122** of them infra          |
| lines        | **+166,725 / −114,750**                      |
| roadmap      | **52** items done, **17** open               |

Source: `python3 scripts/journey.py` -> `docs/web/journey.html`

<!-- end_slide -->

The machines
===
<!-- font_size: 2 -->

<!-- column_layout: [1, 1, 1] -->
<!-- column: 0 -->

## oci

Oracle Cloud, free tier, arm64

- control plane
- DNS: knotd + kresd
- reached only over Tailscale
- one open port: UDP 41641

<!-- column: 1 -->

## rbpi

Raspberry Pi 5, 16 GB, 2x NVMe

- the edge: Traefik, AGH
- forgejo, pds, atuin
- apex, blog, gallery
- monitoring, Flux, cert-manager

<!-- column: 2 -->

## rzbl

Razer Blade 15, GTX 1660 Ti, 4 TB SSD

- GPU: Jellyfin, Ollama, Immich ML
- media, photos, files
- authentik + Postgres
- Kata VMs for agents

<!-- end_slide -->

Phase 1: the foundation (Sep 13 to 30)
===
<!-- font_size: 2 -->

- **v1.0.0** on Sep 16: Talos, Flux, an OCI artifact as the only source
- Flannel out, **Cilium** in (kube-proxy replacement, L2 announcements)
- **Gateway API** with Traefik, Let's Encrypt wildcard over DNS-01
- SOPS + age for every secret
- DNS: pi-hole, then **AdGuard Home**; kresd moved to OCI because the ISP router hijacks port 53
- Forgejo, the ATProto PDS, Knative, k8up, **Kata Containers**

> 60 tags in 15 days, many of them `fix:`. The CRD ordering rule was learned here:
> a CR and its CRD never share a Kustomization.

<!-- end_slide -->

Phase 2: the dev box and the quiet month (Oct)
===
<!-- font_size: 2 -->

- **devil**: a NixOS VM in a Kata pod, ssh on 2222, ghostty-web in the browser
- the **tailscale-relay**: a user-owned device, because tagged nodes cannot see shared-in machines
- **atuin** server for shell history
- **omni**: nix for every machine (44 commits in two weeks)
- **apex** begins: a Ratatui portfolio that runs in the terminal, over SSH and as WASM

<!-- end_slide -->

Phase 3: the sites (Nov 8 to 15)
===
<!-- font_size: 2 -->

- **thyme**: a Typst static-site package, published on Typst Universe
- **glob**: the blog, built with thyme
- **exhib**: the Hugo gallery with an upload processor
- **apex** goes live at 0xbf.ch, plus `ssh 0xbf.ch`
- tier 2 apps: `:latest` images, polled by Keel

The busiest day: **Nov 9**, 66 commits across five repos (thyme 23, apex 21).

<!-- end_slide -->

Phase 4: the second worker (Nov 15 to 16)
===
<!-- font_size: 2 -->

- **rzbl** joins: Talos boots from a USB stick, NVMe and SSD as user volumes
- VXLAN through the Pi's SNAT fails: rzbl gets its own `/32` route and a routing rule
- NVIDIA extensions, GPU **time-sliced into 4 slots**
- the media stack, Ollama, and prepared apps waiting for secrets
- a naming convention for every PVC, Secret and hostname

<!-- end_slide -->

Phase 5: identity and isolation (Nov 17)
===
<!-- font_size: 2 -->

<!-- column_layout: [1, 1] -->
<!-- column: 0 -->

## authentik

- one IdP, invitation-only
- OIDC for Forgejo, Jellyfin, Grafana
- forward auth for internal tools
- lesson: blueprint providers need
  `grant_types`, or every login fails

<!-- column: 1 -->

## agents

- opencode in a **Kata VM**
- Cilium egress allowlist, no SA token
- **Agent Sandbox**: a warm pool,
  one throwaway VM per task
- `sandbox new` binds a claim to
  `sandbox-N.internal`

<!-- end_slide -->

Phase 6: one place to look (Nov 17)
===
<!-- font_size: 2 -->

- Grafana home dashboard **0xbf**: health, status checks, nodes, disks, GPU, traffic, Flux
- curated dashboards instead of the stock forty
- Gatus status page, checks through the real edge
- everything that watches lives on the always-on Pi
- placement rule: **one node failure takes down one role**

<!-- end_slide -->

Then the rest of the night
===
<!-- font_size: 2 -->

- copyparty at **files.0xbf.ch**
- Immich with machine learning on the GPU
- Forgejo Actions with a runner on rzbl
- Kubernetes **1.35 -> 1.36 -> 1.37**, with an etcd snapshot before each step
- secrets seeded straight into `sops --encrypt`, never printed

<!-- end_slide -->

What went wrong (and what it taught)
===
<!-- font_size: 2 -->

- a CR next to its CRD: dry-run fails, nothing applies
- `kubectl port-forward` cannot reach a Kata VM
- `window.open` while a `RefCell` is borrowed: Firefox froze the site
- copyparty printed its config, password included, on a parse error: rotate
- an arm64-only image scheduled on an amd64 node
- `0xbf` unquoted in YAML is a hex number

<!-- end_slide -->

Next
===
<!-- font_size: 2 -->

1. **backups**: Garage on a friend's NAS, then restore drills
2. qBittorrent over Proton VPN
3. Renovate on the Forgejo runner
4. alerts to the phone (ntfy)
5. the MacBook reset to omni

<!-- pause -->

Thank you.

`git.0xbf.ch` · `0xbf.ch` · `ssh 0xbf.ch`
