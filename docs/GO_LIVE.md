# Go-live: apex, glob, exhib

This document describes how to bring `apex`, `glob`, and `exhib` live on `bfeitknecht/infra`.

Scope: The branch `arena/17a7be60-infra` folds the `infra/` staging from the three app repos at commit `4e7c2e1`. Review the branch, merge it, then follow the steps below. Do not use `kubectl apply`. The cluster updates only from a `v*` tag.

## Changes in this PR

* `kubernetes/applications/exhib/*`: New gallery at `gallery.0xbf.ch`. The Deployment has three containers and a 50Gi PVC. Keel tracks `containers[2]`.
* `kubernetes/applications/glob/deployment.yaml`: Add `readinessProbe` and `runAsNonRoot` settings for parity with staging.
* `kubernetes/applications/apex/tui-deployment.yaml`, `tui-service.yaml`, `tui-tcproute.yaml`: New SSH portfolio `apex-tui`. The image is the same as the site. The server allows any username and has no client key.
* `kubernetes/applications/apex/kustomization.yaml`: List the three `tui-*` files. The file `ssh-host-key.sops.yaml` stays commented until you create it.
* `kubernetes/cluster/applications.yaml`: Add `spec.ignore` for `apex-tui` and a new Kustomization for `exhib`.
* `kubernetes/infrastructure/ingress/traefik/gateway.yaml`: Change `gitssh` port from 22 to 2223. Add `apexssh` listener on port 22.
* `kubernetes/infrastructure/ingress/traefik/traefik.yaml`: Add `apexssh` entrypoint on port 22 with `hostPort: 22`. Change `gitssh` port from 22 to 2223.
* `kubernetes/infrastructure/monitoring/gatus.yaml`: Add endpoints for `apex`, `apex-ssh`, `glob`, and `exhib`.
* `README.md` and `AGENTS.md`: Update the public app list, the tree, the gateway description, and the secrets list.

Port assignment. Do not reuse ports.

* 80 and 443: traefik web and websecure
* 22: apex SSH at `ssh 0xbf.ch`
* 2222: devil SSH via LB IP only. No WAN access.
* 2223: forgejo git-ssh at `git@git.0xbf.ch:2223`

After go-live, remove the `infra/` directory from each app repo.

## Secrets to create locally

Do these steps on your local machine. Do not do them in CI. Agents never read or write `*.sops.yaml` files.

1. Apex SSH host key. This key is the server identity. Keep it safe with the other secrets.

```
ssh-keygen -t ed25519 -N '' -f /tmp/apex_ssh_host_ed25519_key
ssh-keygen -lf /tmp/apex_ssh_host_ed25519_key.pub
kubectl create secret generic apex-ssh-host-key -n apex \
  --from-file=ssh_host_ed25519_key=/tmp/apex_ssh_host_ed25519_key \
  --dry-run=client -o yaml \
| sops --encrypt --input-type yaml /dev/stdin \
> kubernetes/applications/apex/ssh-host-key.sops.yaml
shred -u /tmp/apex_ssh_host_ed25519_key
```

Then uncomment the last line in `kubernetes/applications/apex/kustomization.yaml`.

Check the file with `sops -d kubernetes/applications/apex/ssh-host-key.sops.yaml | grep ssh_host_ed25519_key`.

2. Exhib GHCR pull secret. Create it from an existing secret.

```
sops -d kubernetes/applications/glob/ghcr.sops.yaml \
  | sed 's/namespace: glob/namespace: exhib/' \
  | sops -e > kubernetes/applications/exhib/ghcr.sops.yaml
```

Alternative: Make `ghcr.io/bfeitknecht/exhib` public. Then remove `ghcr.sops.yaml` from `kustomization.yaml`, remove `imagePullSecrets` from the Deployment, and remove `serviceaccount.yaml`.

3. Check that `sops-age` is present. Use `kubectl -n flux-system get secret sops-age`.

No other secret is necessary. Files `glob/ghcr.sops.yaml`, `apex/ghcr.sops.yaml`, `ghcr-pat`, and `cloudflare-dns01` already exist.

## Pre-flight checks

Do these checks before you push a tag.

* Check drift. Check if `master` in `infra` moved since `4e7c2e1`. If it moved, merge `cluster/applications.yaml` by hand. Do not overwrite the file.
* Check images. Each app repo must push `ghcr.io/bfeitknecht/<app>:latest` before Flux reconciles. If the image is missing, the pod stays in `ImagePullBackOff`.

```
# In each app repo after fixes are on master:
just release v0.1.0 "apex v0.1.0"
# Or: git tag v0.1.0 -m "v0.1.0" && git push origin v0.1.0
```

The workflow is at `bfeitknecht/infra/.github/workflows/publish-image.yaml@master`. It builds `linux/amd64,linux/arm64`. Apex builds `linux/arm64` only.

* Check thyme and exemel. `glob` and `apex` use `thyme@0.1.0` and `exemel@0.3.0` from `vendor/`. The build needs `exemel` on the `@preview` registry before the `thyme` release. Do not tag `infra` until `exemel` is published and `thyme` is re-vendored.

## Router

The Zyxel AX7501 router must forward WAN ports to the worker.

* Add WAN `2223/tcp` to `10.10.20.10:2223` for forgejo git-ssh.
* WAN `22/tcp` to `10.10.20.10:22` already exists. It now reaches apex, not git.

No DNS change is necessary. The wildcard `*.0xbf.ch` and the cert `wildcard-domain-tls` already cover `blog.0xbf.ch` and `gallery.0xbf.ch`.

## Merge and tag

```
git fetch origin
git checkout master
git merge --ff-only arena/61403a01-infra
# Check the diff first: git log origin/master..arena/61403a01-infra -p
# Create secrets as described above and uncomment the kustomization line
kubectl kustomize kubernetes/applications/exhib
kubectl kustomize kubernetes/applications/apex
kubectl kustomize kubernetes/applications/glob
git add kubernetes/applications/exhib/ghcr.sops.yaml kubernetes/applications/apex/ssh-host-key.sops.yaml kubernetes/applications/apex/kustomization.yaml
git commit -m "secrets: add apex host key and exhib ghcr"
git push origin master
git tag v1.15.0 -m "apex ssh on 22, glob blog, exhib gallery"
git push origin v1.15.0
flux get kustomizations -A
kubectl -n flux-system describe kustomization traefik
kubectl -n flux-system describe kustomization apex glob exhib
```

Traefik uses `Recreate` and `hostPort`. The update causes about 10 seconds of downtime.

## Verify

```
kubectl -n apex get pod,svc,tcproute
kubectl -n glob get pod,svc,httproute
kubectl -n exhib get pod,svc,httproute,pvc
kubectl -n exhib logs deploy/exhib -c processor --tail=50
curl -sI https://0xbf.ch | head -1
curl -sI https://blog.0xbf.ch | head -1
curl -sI https://gallery.0xbf.ch | head -1
curl -s https://gallery.0xbf.ch/rss.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
curl -s https://gallery.0xbf.ch/atom.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
ssh 0xbf.ch
git clone ssh://git@git.0xbf.ch:2223/bfeitknecht/infra.git /tmp/check
curl -s https://status.internal | grep -i gatus
kubectl -n monitoring get configmap gatus-config -o yaml | grep -A2 "name: apex"
```

To test without the router, use `ssh -p 22 10.10.20.10` for apex and `ssh -p 2223 10.10.20.10` for forgejo.

## Cleanup after go-live

* In each app repo, run `git rm -r infra/` and update the README. Commit the change.
* Keep the apex host key and its fingerprint with `talos/secrets.sops.yaml`. If you lose the key, clients see a warning.
* The PVC `exhib-site` stores originals at `/data/originals`. Back up this data before you delete the namespace. `k8up` does not back up this PVC yet.
* Update clone URLs to `ssh://git@git.0xbf.ch:2223/...`.

## Troubleshooting

* `flux get ks exhib` shows decryption error: `ghcr.sops.yaml` is missing. Create the file as described in Secrets.
* Pod shows `ImagePullBackOff`: The image is not published or the pull secret is wrong. Publish the image and check `kubectl -n <ns> get secret dockerconfigjson`.
* PVC shows `Pending`: Check `flux get ks storage`. Exhib needs `storage`.
* Traefik shows 502 for 10 seconds: This is normal. The pod uses `Recreate` and holds the ports during restart. Wait and check `flux get ks traefik`.
* Apex site is 404 but SSH works, or the opposite: One Deployment has an error. The site and SSH use separate Deployments. Check the pod status.

Keep this file until tag `v1.15.0` is active. You can delete it after that or move it to `.private/`.
