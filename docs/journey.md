---
title: "GENESIS: a homelab journey"
sub_title: "From one Pi to a three-node Talos cluster, in 73 days"
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
| days         | **69** calendar, **40** active               |
| repositories | **6**: infra, apex, exhib, glob, thyme, omni |
| commits      | **530** (plus **123** merged pull requests)  |
| releases     | **208** tags, **163** of them infra          |
| lines        | **+173,813 / −118,345**                      |
| roadmap      | **56** items done, **19** open               |

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
- every bash command in a
  **bubblewrap** sandbox inside it
- pushes as the Forgejo bot `opencode`
- per-task sandbox VMs tried,
  then removed: one VM is enough

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

Phase 7: one SSH port (Nov 18 to 19)
===

<!-- font_size: 2 -->

- git on the clean **22**: `ssh://git@git.0xbf.ch/owner/repo.git`
- one WAN port **2222** for every SSH TUI, routed by **username**
- `ssh -p 2222 0xbf.ch` is the apex TUI
- browsh over SSH tried, then removed: it looked bad and cost RAM
- thyme **0.1.2** to Typst Universe: reading time on entry cards

<!-- end_slide -->

Phase 8: own the git (Nov 19 to 20)
===

<!-- font_size: 2 -->

- **Forgejo is primary** for all six repos; push mirrors keep GitHub for CI
- Renovate moved to Forgejo, with its own bot
- SSO for Jellyfin (maintained plugin fork) and copyparty
- gallery **uploader**: drag and drop at `gallery.0xbf.ch/upload`, one user only
- **Anubis** proof-of-work in front of `/cv`, restyled plain monochrome
- one runbook (`OPERATIONS.md`), one guide (`GUIDE.md`), one diagram

<!-- end_slide -->

Phase 9: real use (Nov 21 to 23)
===

<!-- font_size: 2 -->

- **identities** split: personal `bf` everywhere, native `admin` where an app keeps one
- **Immich** set up, **ntfy** on the phone: alerts reach me anywhere
- devil to **rzbl**; the "freeze" was a hung `nix-store --load-db`, not Kata
- Garage on the friend's NAS answers again (the bucket, it turned out, did not)
- **Bazarr** for subtitles, `music.0xbf.ch` public behind SSO
- **Claude Code** in the opencode VM: my subscription, same two walls
- `glry` on narrow screens, not `gal`

<!-- end_slide -->

Phase 10: polish and ghosts (Nov 24)
===

<!-- font_size: 2 -->

- thyme **0.2.0**: one CSS layer, design tokens, `nav` and `footer`, a table fade that follows the scroll
- the blog wears the gallery's chrome; a post on **the perfect prompt**
- one `agents.md` in omni for every agent: tools from flakes, nothing global
- a **ghost devil**: the old VM outlived its pod and answered for devil in Rex
- backups found: Garage lost the bucket; one manual run showed it
- authentik tidied: one entry per app, and why the passkey kept vanishing

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
- sshd refuses world-readable keys, and Secret volumes are world-writable dirs
- browsh hard-codes its Firefox port: two in one pod cannot work
- a Kata container cannot mount a fresh `/proc`: patch the sandbox to nest weaker
- static-web-server will not follow ConfigMap symlinks: mount by `subPath`
- one hung systemd unit blocks the job queue: the VM is up, but nothing new starts
- eleven alerts in one group were too big for ntfy: the phone stayed silent
- "bundled" was not bundled: check the binary is on PATH before you write it down
- a copied home copies identities: two VMs, one tailnet name, the wrong one answered
- iCloud keeps one passkey per site: enrolling again replaces it everywhere
- k8up deletes failed pods: start one run by hand and read its log live

<!-- end_slide -->

Next
===

<!-- font_size: 2 -->

1. **backups**: the bucket back on the NAS, a green night, then a restore drill
2. **opencode**: a caged NixOS pod and a trusted tier, each with the right MCP servers
3. thyme 0.2.0 on Universe, then glob 0.1.8
4. Time Machine, the real photos and files, and the move from echo to anti

<!-- pause -->

Thank you.

`git.0xbf.ch` · `0xbf.ch` · `ssh -p 2222 0xbf.ch`
