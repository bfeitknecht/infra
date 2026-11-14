# Go-live: Talos 1.14.6 + rzbl + apex/glob/exhib — one tag

This note describes how to go from the current cluster to the target state in one tag.
The tag will ship Talos 1.14.6, the new worker `rzbl`, and the three apps `apex`, `glob`, `exhib` together.
Do this only after `thyme` is merged. `apex` and `glob` stay blocked until `thyme` is on `master` and `exemel@preview` is published. `exhib` could go live now. Wait with it and ship all three apps at once.

Use STE100. Be terse. No em dashes. No `kubectl apply`. The cluster updates only from a `v*` tag.

## Starting point

Current state before this go-live:

* `oci` at `10.20.20.10` (control plane, tainted) runs Talos 1.14.2. Declared `1.14.2` in `talos/topf.yaml` on `master`.
* `rbpi` at `10.10.20.10` (worker, Pi 5) runs Talos 1.14.2. Declared `1.14.2`. Extensions `tailscale`, `nvme-cli`, `kata-containers` plus `rpi_5` overlay.
* `rzbl` (Razer Blade 15 Base 2019, i7-9750H, GTX 1660 Ti, `10.10.20.11`) is not in `topf.yaml` on `master`. It boots a generic Talos 1.14.6 metal image to maintenance mode. No machine config applied yet.
* Kubernetes is `1.35.3`. Cilium, Traefik, cert-manager, monitoring, k8up, Knative, Keel are live through the last `v*` tag.
* App manifests for `apex`, `glob`, `exhib` are already in the repo on `master` (PR #2 merged at `924d1fe`). They are not yet live on the cluster until the next tag reconciles. `apex` and `glob` images are missing. They need `thyme@0.1.0` and `exemel@0.3.0` with `exemel` on `@preview`. `exhib` image `ghcr.io/bfeitknecht/exhib:latest` can be published now but will wait.
* Backup is not yet verified. `k8up` points to `tailscale-relay.egress.svc.cluster.local:3900` which forwards to friend NAS `100.96.72.126:3900`. See `docs/BACKUP_NAS_OUTLINE.md`. Direct tagged-device access to the shared-in NAS is not yet proven. Relay is the current path.

## Target state

Target state after this go-live:

* All nodes run Talos `1.14.6`. Declared `1.14.6` in `talos/topf.yaml`. Image Factory IDs are re-derived on `topf upgrade`.
* `rzbl` is a worker at `10.10.20.11`. Schematic `talos/schematic.rzbl.yaml` with `tailscale`, `intel-ucode`, `nvme-cli`, `kata-containers`, `nvidia-open-gpu-kernel-modules-lts`, `nvidia-container-toolkit-lts`. Patches `talos/patches/node/rzbl/*` applied. Lid close does not suspend (`04-logind.yaml` with `HandleLidSwitch=ignore` via `EtcFileConfig`). GPU is available to workloads via NVIDIA device plugin.
* `apex` is live at `https://0xbf.ch` and `ssh 0xbf.ch` on port `22`. `glob` is live at `https://blog.0xbf.ch`. `exhib` is live at `https://gallery.0xbf.ch`.
* Single tag ships both Talos config and app manifests. No second tag is needed for this cutover.

## Changes in this branch

Branch `arena/7727b2f4-infra` holds the full cutover. It is based on `924d1fe` (PR #2 merged) and adds Talos 1.14.6 work.

Talos part (see `talos/patches/README.md` for detail):

* `talos/topf.yaml`: bump `talosVersion: 1.14.2` to `1.14.6`. Add node `rzbl` `10.10.20.11` `role: worker` `schematicId: "@schematic.rzbl.yaml"`.
* `talos/schematic.{oci,rbpi,rzbl}.yaml`: no extension change at 1.14.6. File fix is newline at EOF. New factory ID is derived on upgrade.
* `talos/patches/control-plane/02-network.yaml`: migrate `machine.network.interfaces` and `machine.sysctls` to `DHCPv4Config` for `eth0` plus `SysctlConfig` for `net.ipv4.ip_forward` and `net.ipv6.conf.all.forwarding`. `machine.certSANs` stays in `v1alpha1`.
* `talos/patches/node/rbpi/02-network.yaml`: same migration for `end0`.
* `talos/patches/node/rzbl/02-network.yaml`: add `DHCPv4Config` for `eth0` plus `SysctlConfig`. Verify link name with `talosctl get links`. Blade reports `eth0` on Talos. Update if `enp*`.
* `talos/patches/node/rbpi/04-storage.yaml`: migrate `machine.disks` to `UserVolumeConfig` `storage-nvme0` and `storage-nvme1` with `disk.dev_path`, `grow: true`, `filesystem.type: xfs`. Mounts are `/var/mnt/storage-nvme0` and `/var/mnt/storage-nvme1`. Old paths were `/var/mnt/storage/nvme0|nvme1`.
* `talos/patches/node/rzbl/04-logind.yaml`: new `EtcFileConfig` `systemd/logind.conf` with `HandleLidSwitch=ignore`, `HandleLidSwitchExternalPower=ignore`, `HandleLidSwitchDocked=ignore`, `HandlePowerKey=ignore`. Lid close does not suspend or power off the Blade.
* `kubernetes/infrastructure/storage/local-path-storage.yaml`: update `nodePathMap` for `rbpi` to new `/var/mnt/storage-nvme0,nvme1` paths.
* `HARDWARE.md` and `README.md`: update version strings to `1.14.6` and topology table to three nodes.
* Docs: `docs/BACKUP_NAS_OUTLINE.md` added (friend NAS relay, tagged-device hypothesis, ACL fix options). This file is `talos/patches/README.md` companion for `exhib` etc.

App part (already on `master` via PR #2, see `docs/GO_LIVE.md` for full app detail):

* `kubernetes/applications/exhib/*`: new gallery at `gallery.0xbf.ch` with three containers and `50Gi` PVC `exhib-site`. Keel watches `containers[2]`.
* `kubernetes/applications/apex/*` and `glob/*`: site plus SSH TUI (`apex-tui` on port `22`), blog, with `readinessProbe` and `runAsNonRoot` parity fixes.
* `kubernetes/cluster/applications.yaml`: add `spec.ignore` for `apex` and `glob` images and Kustomization for `exhib`.
* `kubernetes/infrastructure/ingress/traefik/gateway.yaml` and `traefik.yaml`: move `gitssh` `22` to `2223`, add `apexssh` listener `22` with `hostPort: 22`.
* `kubernetes/infrastructure/monitoring/gatus.yaml`: endpoints for `apex`, `apex-ssh`, `glob`, `exhib`.

No new app manifests are added in this branch. App manifests are already on `master`. This branch only adds Talos and docs.

## Gate: thyme

Do not start Talos rollout until `thyme` is merged.

* `glob` and `apex` vendor `thyme@0.1.0` and `exemel@0.3.0`. `exemel` must be on `@preview` before `thyme` release. `thyme` re-vendor must land on `master` in `apex` and `glob` repos.
* After `thyme` is on `master`, tag `apex` and `glob` repos with `just release v0.1.0` so `ghcr.io/bfeitknecht/apex:latest` and `glob:latest` exist. Verify with `oras` or GHCR UI.
* Publish `exhib` image `ghcr.io/bfeitknecht/exhib:latest` at same time. Do not tag `infra` until all three `latest` images exist. Missing image causes `ImagePullBackOff`.

Short check before merge:

```
# in each app repo
git fetch origin && git log origin/master --oneline -5
# check image
crane ls ghcr.io/bfeitknecht/apex | grep latest
crane ls ghcr.io/bfeitknecht/glob | grep latest
crane ls ghcr.io/bfeitknecht/exhib | grep latest
```

## Pre-flight: secrets and checks

Do this on your local machine. Never in CI. Agents never read or write `*.sops.yaml`.

1. Apex SSH host key. Required for `apex-tui` on port `22`.

```
ssh-keygen -t ed25519 -N '' -f /tmp/apex_ssh_host_ed25519_key
kubectl create secret generic apex-ssh-host-key -n apex \
  --from-file=ssh_host_ed25519_key=/tmp/apex_ssh_host_ed25519_key \
  --dry-run=client -o yaml \
| sops --encrypt --input-type yaml /dev/stdin \
> kubernetes/applications/apex/ssh-host-key.sops.yaml
# then uncomment last line in kubernetes/applications/apex/kustomization.yaml
sops -d kubernetes/applications/apex/ssh-host-key.sops.yaml | grep ssh_host
shred -u /tmp/apex_ssh_host_ed25519_key /tmp/apex_ssh_host_ed25519_key.pub
```

2. Exhib GHCR secret. Already in this branch `kubernetes/applications/exhib/ghcr.sops.yaml` derived from `glob`. Verify it exists. If you make `ghcr.io/bfeitknecht/exhib` public, remove `ghcr.sops.yaml`, `serviceaccount.yaml`, and `imagePullSecrets`.

```
sops -d kubernetes/applications/exhib/ghcr.sops.yaml | head
kubectl kustomize kubernetes/applications/exhib | grep dockerconfigjson
```

3. Check `sops-age` in cluster: `kubectl -n flux-system get secret sops-age`.

4. Check drift: `git fetch origin && git log origin/master..HEAD --stat`. `master` may have moved since this branch was cut. Merge `cluster/applications.yaml` by hand. Do not overwrite.

5. Validate manifests: `kubectl kustomize kubernetes/applications/{apex,glob,exhib}` and `kubectl kustomize kubernetes/infrastructure/traefik` must not error.

6. Validate Talos patches: `talosctl validate --config <rendered>` or `topf plan`. Check `DHCPv4Config` link names. Blade uses `eth0`. If `talosctl get links` shows `enp*`, update `node/rzbl/02-network.yaml`.

## Step 1: Prepare rzbl

On the Blade at `10.10.20.11`:

* Boot generic Talos `1.14.6` metal image to maintenance mode. Generic image is not per-node. It has no extensions. It is only for bootstrap.
* Confirm network: `ip addr` shows `10.10.20.11` on `eth0`. Check DHCP lease table on Zyxel. If link is `enp*`, note it for patch fix.
* Confirm you can reach it from your machine over tailnet or LAN: `talosctl --nodes 10.10.20.11 version`.

No `topf apply` yet. Leave it in maintenance mode until origin nodes are upgraded.

## Step 2: Upgrade oci and rbpi to 1.14.6

Talos config changes are not yet live on `master`. This branch holds them. Apply from this branch.

Option A: apply all nodes (needs tailnet path to `oci` at `100.73.186.19` and to `rbpi` at `10.10.20.10`):

```
git checkout arena/7727b2f4-infra
topf apply
```

Option B: if `oci` is not reachable over tailnet, apply only `rzbl` first, then `oci` later. Or use `--nodes`:

```
topf apply --nodes 10.10.20.11   # rzbl only: writes machine config to maintenance mode node
topf apply --nodes 10.20.20.10    # oci
topf apply --nodes 10.10.20.10    # rbpi
```

What `topf apply` does: it renders machine config from `topf.yaml` plus `patches/*` and pushes it to the node. It does not upgrade the Talos image yet.

Then upgrade image if declared version differs from running version:

```
topf upgrade --nodes 10.20.20.10
topf upgrade --nodes 10.10.20.10
# rzbl does not need upgrade. It already runs generic 1.14.6. After apply it reboots with correct config and extensions. If schematic changed, upgrade after first boot.
```

Verify after each node:

```
talosctl --nodes 10.20.20.10 version
talosctl --nodes 10.10.20.10 version
talosctl --nodes 10.10.20.11 version
talosctl --nodes 10.10.20.10 get links
talosctl --nodes 10.10.20.11 get links
kubectl get nodes -o wide
```

`HARDWARE.md` note: `rbpi` NVMe driver is in kernel. `nvme-cli` is userspace. `rbpi` Talos image needs `rpi_5` overlay with `config.txt` params. `rzbl` needs `intel-ucode` and NVIDIA open modules `nvidia-open-gpu-kernel-modules-lts` plus toolkit.

Check lid config on `rzbl` after apply:

```
talosctl --nodes 10.10.20.11 read /etc/systemd/logind.conf
# must show HandleLidSwitch=ignore and siblings
loginctl show | grep HandleLid  # on node if you exec
```

Close lid test: node stays `Ready`. `kubectl get nodes` still shows `rzbl` `Ready` after 60 seconds with lid closed.

## Step 3: Verify cluster health before tag

Do not tag until Talos health is green.

```
talosctl health --nodes 10.20.20.10,10.10.20.10,10.10.20.11
kubectl get nodes
kubectl get pods -A | grep -v Running
flux get kustomizations -A
```

Storage check: `kubectl -n local-path-storage get pods` and `ls /var/mnt/storage-nvme0` on `rbpi` via `talosctl exec`.

Traefik check: `kubectl -n ingress get gateway traefik-gateway -o yaml` must show listeners `web 8000`, `websecure 8443`, `apexssh 22`, `devilssh 2222`, `gitssh 2223`. `kubectl -n ingress get pods` must be `Running`.

Tailnet: `tailscale status` on each node and `tailscale ping 100.96.72.126` from `tailscale-relay` pod vs tagged node. Document result in `BACKUP_NAS_OUTLINE.md` if it changes.

## Step 4: Merge and tag — one tag for Talos and apps

This step publishes `ghcr.io/bfeitknecht/infra` and lets Flux reconcile. Flux does not manage Talos. Talos is already updated via `topf`. The tag only ships Kubernetes manifests.

```
git fetch origin
git checkout master
git merge --ff-only arena/7727b2f4-infra
# resolve if master moved. Keep both Talos and app changes.
git push origin master
git tag v1.15.0 -m "talos 1.14.6 + rzbl (gpu, lid ignore) + apex/glob/exhib live"
git push origin v1.15.0
```

CI publishes `ghcr.io/bfeitknecht/infra:v1.15.0`. `OCIRepository` in `flux-system` tracks `semver >=1.0.0`. Flux reconciles in dependency order `storage -> cilium -> ipam -> cert-manager -> traefik -> apps`.

Traefik update causes about 10 seconds of downtime (`Recreate` with `hostPort: 22`). This is expected. See `docs/GO_LIVE.md`.

Do not use `kubectl apply`. Do not retag same commit. Retagging same SHA does nothing. OCI tag must be new semver.

## Step 5: Verify apps

After Flux reconciles (watch `flux get kustomizations -A` until all `Ready`):

```
kubectl -n apex get pod,svc,tcproute
kubectl -n glob get pod,svc,httproute
kubectl -n exhib get pod,svc,httproute,pvc
kubectl -n exhib logs deploy/exhib -c processor --tail=50
curl -sI https://0xbf.ch | head -1
curl -sI https://blog.0xbf.ch | head -1
curl -sI https://gallery.0xbf.ch | head -1
curl -s https://gallery.0xbf.ch/rss.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
ssh 0xbf.ch   # apex TUI, port 22
ssh git@git.0xbf.ch -p 2223
```

Expected: `apex` and `glob` pods are `Running` (images now exist). `exhib` pod `Running`, `sws` on `8080` ready, gallery returns `200`, status page shows `exhib` green.

GPU check on `rzbl`:

```
kubectl label nodes rzbl nvidia.com/gpu=true --overwrite  # if not yet labelled
kubectl get nodes -L nvidia.com/gpu
kubectl -n kube-system get pods | grep nvidia
kubectl exec -it <gpu-test-pod> -- nvidia-smi  # or via DaemonSet
```

## Router

Zyxel AX7501 must forward WAN to worker:

* Keep `22/tcp` to `10.10.20.10:22` for apex SSH. Already exists. It now reaches `apex`, not `git`.
* Add `2223/tcp` to `10.10.20.10:2223` for forgejo git-ssh if not yet added.
* No forward for `2222` (devil SSH, LAN/tailnet only). Reserved for future dev box.
* No DNS change. Wildcard `*.0xbf.ch` and `wildcard-domain-tls` already cover `blog.0xbf.ch` and `gallery.0xbf.ch`.

Traefik Gateway address stays `10.10.20.128` from Cilium LB-IPAM. No pool change.

## Troubleshooting

* `talosctl get links` wrong name: `rzbl` `02-network.yaml` uses `eth0`. If Blade reports `enp0s*`, update patch and re-apply.
* `ImagePullBackOff` for `apex`/`glob`/`exhib`: GHCR image not published or `dockerconfigjson` wrong. Check `kubectl -n <ns> get secret dockerconfigjson` and GHCR visibility. Private `exhib` needs `ghcr.sops.yaml`.
* `PVC Pending` for `exhib-site`: `flux get ks storage` must be `Ready`. Path must be `/var/mnt/storage-nvme0` etc. Check `kubernetes/infrastructure/storage/local-path-storage.yaml`.
* `404` on `gallery.0xbf.ch`: Gateway listener and HTTPRoute host must match. Check `kubectl -n ingress describe gateway traefik-gateway`.
* Tailscale relay fails: `kubectl -n egress logs deploy/tailscale-relay` and `kubectl -n egress get pods`. Tagged nodes cannot reach `100.96.72.126:3900` directly without ACL fix. Keep relay until ACL is fixed. See `docs/BACKUP_NAS_OUTLINE.md`.
* Talos upgrade stuck: `talosctl dmesg` and `talosctl service etcd status` on `oci`. Do not reboot `oci` and `rbpi` at same time.

## After go-live

* Keep `docs/GO_LIVE.md`, `docs/GO_LIVE_RZBL.md`, and `docs/BACKUP_NAS_OUTLINE.md` until `v1.15.0` is verified, then move to `.private/` or delete.
* Do not remove `infra/` from `bfeitknecht/exhib`, `bfeitknecht/apex`, `bfeitknecht/glob` until you verified uploads and `ImagePullBackOff` is gone for all three apps.
* `exhib-site` PVC holds originals at `/data/originals`. Back up before you delete the namespace. `k8up` does not cover this PVC yet.
* Next work after this tag: backup path fix, immich/photos gate, samba/SATA, ollama/Open WebUI on `rzbl` GPU. See `ROADMAP.md`.

## References

* `talos/patches/README.md` — Talos 1.14.6 document changes and `rzbl` join steps.
* `docs/GO_LIVE.md` — full app go-live detail (ports, Traefik, secrets, verification).
* `docs/BACKUP_NAS_OUTLINE.md` — friend NAS relay, tagged-device hypothesis, ACL options.
* `HARDWARE.md` — topology and provisioning flow.
* `kubernetes/infrastructure/storage/local-path-storage.yaml` — local-path paths.
* `kubernetes/infrastructure/egress/tailscale/relay.yaml` — relay Deployment.
