# Go-live shortlist: exhib only

Scope: Only `exhib` can go live now. `apex` and `glob` are blocked. They need `exemel@preview` and `thyme` re-vendor. This list shows the minimum steps to bring `gallery.0xbf.ch` live.

## 1. Review the PR

Branch `arena/61403a01-infra` is at `fc2136f` (2 commits ahead of `master@40c0a9b`). PR #2: https://github.com/bfeitknecht/infra/pull/2

Contents:

* `kubernetes/applications/exhib/*`: gallery at `gallery.0xbf.ch`, 3 containers (`sws` on `2.44.1-alpine`, `uploader` on `busybox:1.37.0`, `processor` on `ghcr.io/bfeitknecht/exhib:latest`), PVC `exhib-site` 50Gi local-path, health on `/livez|/readyz`, Keel on `containers[2]`
* `kubernetes/applications/apex/*` + `glob/*` + `traefik/gateway.yaml|traefik.yaml` + `gatus.yaml` + docs: already in PR, will deploy but stay in `ImagePullBackOff` until `exemel` is on `@preview`. This does not block `exhib`. No extra action now.
* Style sweep `fc2136f`: remove all em dashes repo-wide, use STE100 short sentences. No functional change.

Action: Review diff, merge PR with `--ff-only` or squash on GitHub.

## 2. Secrets: nothing to create for exhib

* `kubernetes/applications/exhib/ghcr.sops.yaml` already exists in the PR. It was derived from `glob/ghcr.sops.yaml` and encrypted with `sops-age`. No new secret is required.
* Verify after merge: `kubectl -n exhib get secret dockerconfigjson` exists. Flux decrypts `ghcr.sops.yaml` with `sops-age` in `flux-system`.
* Apex secret `apex-ssh-host-key.sops.yaml` is not required for exhib. Create it later when `apex` is unblocked.
* If you make `ghcr.io/bfeitknecht/exhib` public, you can remove `ghcr.sops.yaml`, `serviceaccount.yaml`, and `imagePullSecrets` later. Keep it private for now.

## 3. Publish the exhib image

Do this before you tag `infra`. Flux will otherwise start a pod that stays in `ImagePullBackOff`.

In `bfeitknecht/exhib` repo on `master`:

```
just release v0.1.0 "exhib v0.1.0"
# Or: git tag v0.1.0 -m "v0.1.0" && git push origin v0.1.0
```

Check: `ghcr.io/bfeitknecht/exhib:latest` exists and is multi-arch. The workflow is `publish-image.yaml`.

Do not proceed until the image is visible in GHCR.

## 4. Merge and tag infra

On your local machine:

```
git fetch origin
git checkout master
git merge --ff-only arena/61403a01-infra
git push origin master
git tag v1.15.0 -m "exhib gallery on gallery.0xbf.ch"
git push origin v1.15.0
```

CI publishes `ghcr.io/bfeitknecht/infra:v1.15.0`. Flux `OCIRepository` tracks `semver >=1.0.0` and reconciles.

No router change is required. `*.0xbf.ch` and `wildcard-domain-tls` already cover `gallery.0xbf.ch`.

## 5. Verify

```
flux get kustomizations -A
kubectl -n exhib get pod,svc,httproute,pvc
kubectl -n exhib logs deploy/exhib -c processor --tail=50
curl -sI https://gallery.0xbf.ch | head -1
curl -s https://gallery.0xbf.ch/rss.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
curl -s https://gallery.0xbf.ch/atom.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
curl -s https://status.internal | grep exhib
kubectl kustomize kubernetes/applications/exhib
```

Expected: Pod `exhib` in `Running`, `sws` on `8080` ready, `gallery.0xbf.ch` returns `200`, status page shows `exhib` green.

Upload test: `scripts/upload-item.sh <file>` then check `kubectl -n exhib logs deploy/exhib -c processor`.

## 6. Troubleshooting

* `exhib` pod `ImagePullBackOff`: image not published or `dockerconfigjson` wrong. Check GHCR visibility and `kubectl -n exhib get secret dockerconfigjson`.
* `PVC Pending`: `flux get ks storage` must be Ready. `exhib-site` needs `storage` Kustomization.
* `404` on `gallery.0xbf.ch`: `gateway.yaml` listener `websecure` and `httproute.yaml` host `gallery.0xbf.ch` must match. Check `kubectl -n ingress describe gateway traefik-gateway`.
* Traefik 502 for 10s after tag: normal. `Recreate` holds ports. Wait and check `flux get ks traefik`.

## 7. After go-live

* Keep `docs/GO_LIVE.md` until `v1.15.0` is active, then move to `.private/` or delete.
* Do not remove `infra/` from `bfeitknecht/exhib` until you verified uploads and builds.
* `exhib-site` PVC stores originals at `/data/originals`. Back up before you delete the namespace. `k8up` does not cover this PVC yet.
* When `exemel@preview` is live, re-vendor `thyme` in `apex`/`glob`, publish their images, then tag `v1.16.0` for their go-live. No new infra changes are required for them except `apex-ssh-host-key.sops.yaml`.
