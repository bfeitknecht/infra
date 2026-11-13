# Backup to friend NAS over shared tailnet (outline)

Scope: back up k8up data (forgejo, pds, etc.) to friend NAS via Tailscale that he shares into local tailnet.

## Current setup

- Friend shares his tailnet into local tailnet. No restrictive ACL.
- NAS address `100.96.72.126:3900` is shared-in node. It is Tailscale Garage / S3 gateway.
- Local cluster uses relay workaround `egress/tailscale/relay.yaml`:
  - Deployment `tailscale-relay` (untagged, authenticates with `TS_AUTHKEY`).
  - socat forwarder to `100.96.72.126:3900`.
  - Service `tailscale-relay.egress.svc.cluster.local:3900`.
  - k8up global backend points to `http://tailscale-relay.egress.svc.cluster.local:3900` (see `kubernetes/infrastructure/backup/k8up/k8up.yaml`).
- Direct PodIP dial works if pod bypasses kube-proxy (eg Cilium eBPF). Service VIP may not (conntrack path).

## Key finding: tagged devices and shared-in nodes

Hypothesis: tagged tailnet devices cannot see shared-in nodes.

- Talos overlay and operator are tagged (infra tags).
- Tags need ACL that grants shared-in access explicitly.
- Friend share with permissive ACL but no tag-aware rule, so tagged members see no route.
- Current relay works because relay pod is untagged.
- Verify in Tailscale admin console:
  - List shared-in devices, check visibility per tag.
  - Check ACL `autogroup:shared` or per-tag allow.

## Options

### 1. Keep relay (current workaround)

- Pros: no ACL change, no node tailnet reconfig, verified restic round-trip.
- Cons: extra hop, socat single point, needs auth key rotation, not native Tailscale.

### 2. Fix ACL so tagged nodes see NAS directly

- Add ACL rule that allows `tag:infra` (Talos nodes and operator) to reach `100.96.72.126:3900` or `autogroup:shared`.
- Example fragment (consult `tailscale.com/kb/1018`):

  ```json
  {
    "acls": [
      {"action": "accept", "src": ["tag:infra", "tag:k8s", "tag:k8s-operator"], "dst": ["100.96.72.126:3900"]}
    ],
    "tagOwners": {
      "tag:infra": ["autogroup:members"],
      "tag:k8s": ["autogroup:members"],
      "tag:k8s-operator": ["autogroup:members"]
    }
  }
  ```

- Pros: direct path, no relay pod, k8up can point to `100.96.72.126:3900` without in-cluster forwarder.
- Cons: needs admin console edit, re-approve shared prefix, test visibility with `tailscale ping` from Talos nodes.

### 3. Tailnet operator sidecar or egress proxy

- Tailscale operator can expose external tailnet target as Kubernetes Service via egress proxy or via `tailscale.com/tailnet-ip` externalName trick.
- Operator Helm chart supports `proxyConfig`, `ACLs` for operator proxies.
- Map `100.96.72.126` as external service so pods reach it via tailnet without host relay.

### 4. Garage on friend NAS vs local Garage replica

- Evaluate latency, egress cost, restore drills.
- Consider secondary copy to local volume for fast restore, NAS for off-site.

## Decision outline

1. Reproduce tag visibility:
   - Run `tailscale status` and `tailscale ping 100.96.72.126` from `oci`, `rbpi` (Talos nodes) and from relay pod.
   - Confirm relay pod (untagged) succeeds, tagged fails.
2. If confirmed, choose path:
   - Short term: keep relay to unblock backups (Gate for immich/photos).
   - Long term: add ACL rule for `tag:infra` to shared-in host and remove relay once validated.
3. Document final k8up endpoint and credentials (`garage-s3-credentials`, `k8up-password`) in `backup/k8up/`.

## Related docs

- `talos/topf.yaml` nodes carry `tailscale` extension.
- `talos/patches/all/02-tailscale.sops.yaml` holds node auth key.
- `kubernetes/infrastructure/egress/tailscale/relay.yaml` is the workaround relay.
- `kubernetes/infrastructure/backup/k8up/k8up.yaml` points k8up to relay service.
- See Tailscale KB 1018 ACLs and shared-node docs.

