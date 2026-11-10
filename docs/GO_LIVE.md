# Go-live — apex + glob + exhib

> **Scope:** this branch (`arena/17a7be60-infra`) folds the `infra/` staging from the three app repos into `bfeitknecht/infra` at commit `4e7c2e1`. Review it, merge, then follow the checklist below. It never `kubectl apply`s — the cluster only learns from an `v*` tag.

## What this PR changes

| Path                                                                  | Change                                                                                                                   |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `kubernetes/applications/exhib/*`                                     | **New** — Hugo gallery at `gallery.0xbf.ch` (SWS + processor + uploader, 50Gi PVC, `sws.toml`, Keel on `containers[2]`). |
| `kubernetes/applications/glob/deployment.yaml`                        | `readinessProbe` + `runAsNonRoot/runAsUser/runAsGroup` (staging parity).                                                 |
| `kubernetes/applications/apex/tui-{deployment,service,tcproute}.yaml` | **New** — SSH portfolio `apex-tui` (same image, `apex-ssh` entrypoint, `APEX_SSH_PUBLIC=1`).                             |
| `kubernetes/applications/apex/kustomization.yaml`                     | Lists the three `tui-*` files ( `ssh-host-key.sops.yaml` stays commented until you create it).                           |
| `kubernetes/cluster/applications.yaml`                                | Adds `spec.ignore` for `apex-tui` + new `exhib` Kustomization.                                                           |
| `kubernetes/infrastructure/ingress/traefik/gateway.yaml`              | `gitssh 22→2223` + `apexssh 22` listener.                                                                                |
| `kubernetes/infrastructure/ingress/traefik/traefik.yaml`              | `apexssh` entrypoint `22` (+`hostPort:22`), `gitssh 22→2223`.                                                            |
| `kubernetes/infrastructure/monitoring/gatus.yaml`                     | `apex`, `apex-ssh`, `glob`, `exhib` endpoints.                                                                           |
| `README.md`, `AGENTS.md`                                              | Public list, tree sketch, gateway table, secrets inventory, component notes.                                             |

Port ledger (final — do not reuse):

```
80/443   traefik web/websecure
22       apex   ssh 0xbf.ch
2222     devil  LB-only (no WAN)
2223     forgejo git@git.0xbf.ch:2223
```

No `infra/` directory remains in the app repos after their own go-live commits.

## Secrets / files you must create locally (never in CI)

> Owner-only. Agents never read/write `*.sops.yaml`.

1. **Apex SSH host key** — this _is_ the server identity; back it up with the other secrets.

    ```sh
    ssh-keygen -t ed25519 -N '' -f /tmp/apex_ssh_host_ed25519_key
    ssh-keygen -lf /tmp/apex_ssh_host_ed25519_key.pub   # record, commit fingerprint to note
    # 256 SHA256:t/JM/2syNEmGY4G+FFKkKHqueN+WrAmL1tqXN146b6k 0xbf.ch (ED25519)
    kubectl create secret generic apex-ssh-host-key -n apex \
      --from-file=ssh_host_ed25519_key=/tmp/apex_ssh_host_ed25519_key \
      --dry-run=client -o yaml \
    | sops --encrypt --input-type yaml /dev/stdin \
    > kubernetes/applications/apex/ssh-host-key.sops.yaml
    shred -u /tmp/apex_ssh_host_ed25519_key
    # then uncomment the last line in kubernetes/applications/apex/kustomization.yaml
    ```

    Verify: `sops -d kubernetes/applications/apex/ssh-host-key.sops.yaml | grep ssh_host_ed25519_key`.

2. **Exhib GHCR pull secret** — derive from an existing private repo (apex or glob):

    ```sh
    sops -d kubernetes/applications/glob/ghcr.sops.yaml \
      | sed 's/namespace: glob/namespace: exhib/' \
      | sops -e > kubernetes/applications/exhib/ghcr.sops.yaml
    ```

    Alternative: make `ghcr.io/bfeitknecht/exhib` public — then delete `ghcr.sops.yaml` from `kustomization.yaml`, delete `imagePullSecrets` from the deployment, and delete `serviceaccount.yaml`.

3. (Optional) Confirm `sops-age` private key is available for `flux` decryption (`kubectl -n flux-system get secret sops-age`).

No other secret is missing — `glob/ghcr.sops.yaml`, `apex/ghcr.sops.yaml`, `ghcr-pat`, `cloudflare-dns01`, etc. already exist.

## Pre-flight (do these before you tag anything)

- **G0 drift check** — `master` in infra has not moved since `4e7c2e1` (tag date 2026-11-09). If it has, hand-merge `cluster/applications.yaml` instead of blindly overwriting.
- **Images published** — each app repo must have pushed `ghcr.io/bfeitknecht/<app>:latest` _before_ Flux reconciles or pods sit `ImagePullBackOff`:

    ```sh
    # in each app repo (apex, glob, exhib) — after their go-live fixes merged to master:
    just release v0.1.0 "apex v0.1.0"   # or: git tag v0.1.0 -m "v0.1.0" && git push origin v0.1.0
    # verify: gh run list --workflow publish-image.yaml ; crane digest ghcr.io/bfeitknecht/apex:latest
    ```

    The reusable workflow lives at `bfeitknecht/infra/.github/workflows/publish-image.yaml@master`; it builds `linux/amd64,linux/arm64` (apex is `arm64`-only).

- **Thyme / exemel unblock** — `glob` and `apex` vendor `thyme@0.1.0` + `exemel@0.3.0` via `vendor/`. The `site.typ`/`ssg/site.typ` compile needs `exemel` on the `@preview` registry before `thyme`'s `release` can be cut. **Do not tag infra until exemel is published and thyme is re-vendored.** Track at `typst/packages` PR.

## Router

Zyxel AX7501: add **WAN 2223/tcp → 10.10.20.10:2223** (new git-ssh). WAN 22 already `→ 10.10.20.10:22` now reaches apex, not git. No DNS change — `*.0xbf.ch` wildcard covers `blog.0xbf.ch` and `gallery.0xbf.ch`; `wildcard-domain-tls` cert covers them.

## Merge & tag

```sh
git fetch origin
git checkout master
git merge --ff-only arena/17a7be60-infra   # review diff first: git log origin/master..arena/17a7be60-infra -p
# create secrets from section above, uncomment kustomization line, verify kustomize dry-run:
kubectl kustomize kubernetes/applications/exhib    # needs ghcr.sops.yaml
kubectl kustomize kubernetes/applications/apex     # needs ssh-host-key.sops.yaml
kubectl kustomize kubernetes/applications/glob
git add kubernetes/applications/exhib/ghcr.sops.yaml kubernetes/applications/apex/ssh-host-key.sops.yaml kubernetes/applications/apex/kustomization.yaml
git commit -m "secrets: add apex host key + exhib ghcr"
git push origin master

# tag — Flux OCIRepository tracks semver >=1.0.0, so the tag is the deploy:
git tag v1.15.0 -m "apex ssh on 22 + glob blog + exhib gallery"
git push origin v1.15.0

# watch:
flux get kustomizations -A
kubectl -n flux-system describe kustomization traefik   # first to go — ~10s web downtime (Recreate + hostPort)
kubectl -n flux-system describe kustomization apex glob exhib
```

## Verify

```sh
kubectl -n apex get pod,svc,tcproute
kubectl -n glob get pod,svc,httproute
kubectl -n exhib get pod,svc,httproute,pvc   # PVC Bound, pod 1/1 (3 containers)
kubectl -n exhib logs deploy/exhib -c processor --tail=50

curl -sI https://0xbf.ch | head -1          # 200
curl -sI https://blog.0xbf.ch | head -1     # 200
curl -sI https://gallery.0xbf.ch | head -1  # 200
curl -s https://gallery.0xbf.ch/rss.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'
curl -s https://gallery.0xbf.ch/atom.xml | python3 -c 'import xml.etree.ElementTree as ET,sys; ET.parse(sys.stdin)'

ssh 0xbf.ch                                 # portfolio; verify fingerprint from step 1
git clone ssh://git@git.0xbf.ch:2223/bfeitknecht/infra.git /tmp/check

# gatus
curl -s https://status.internal | grep -i gatus
kubectl -n monitoring get configmap gatus-config -o yaml | grep -A2 "name: apex"
```

LAN bypass test (skip router): `ssh -p 22 10.10.20.10` reaches apex; `ssh -p 2223 10.10.20.10` reaches forgejo.

## Post-go-live cleanup

- In each app repo: `git rm -r infra/` and delete the go-live note from `README`/`docs/go-live.md`; commit.
- Back up the apex host key and fingerprint alongside `talos/secrets.sops.yaml` — losing it rotates every client's `known_hosts`.
- Exhib PVC `exhib-site` holds originals under `/data/originals` — back up before deleting the namespace; `k8up` does not cover it yet.
- Update any docs/client configs: Forgejo clone URL is `ssh://git@git.0xbf.ch:2223/...` (not `git@git.0xbf.ch:owner/repo.git`).

## Rollback / failure triage

| Symptom                                               | Cause                                                             | Fix                                                                                                     |
| ----------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `flux get ks exhib` dry-run error mentions decryption | `ghcr.sops.yaml` missing                                          | create per § Secrets                                                                                    |
| Pod `ImagePullBackOff`                                | image not yet published / bad pull secret                         | publish tag, check `kubectl -n <ns> get secret dockerconfigjson`                                        |
| `kubectl -n exhib get pvc` Pending                    | `storage` not ready                                               | `flux get ks storage` — exhib `dependsOn: storage`                                                      |
| Traefik 502 / all hosts down ~10s                     | expected `Recreate` restart with `hostPort` — old pod holds ports | wait, then `flux get ks traefik`                                                                        |
| Apex site 404 but SSH works (or vice-versa)           | one Deployment `ImagePullBackOff` / host key missing              | separate Deployments — site stays up if SSH secret missing (until you uncomment the kustomization line) |

Keep this file — it is the runbook until the `v1.15.0` tag is green. Delete it in a later commit if you prefer, or move it to `.private/`.
