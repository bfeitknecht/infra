# Agent isolation for opencode: options and recommendation

Status 2026-11-17. **Implemented** (steps 1-4): opencode in a Kata VM, CiliumNetworkPolicy `agent-isolation`, authentik forward auth (group `developers`), and Agent Sandbox v1.0.11 with template `opencode` and a warm pool of 1 in ns `agents` (infra v1.29.0). Next: a way to reach a claimed sandbox (per-claim route behind authentik, or the sandbox router). Prerequisite found on the way: Cilium needed `socketLB.hostNamespaceOnly: true`, otherwise Kata VMs cannot reach ClusterIPs.

Goal: coding agents (opencode web, later others) run arbitrary commands. They must not reach the cluster, the home LAN, secrets, or other workloads. "Airtight" means two walls: a **compute wall** (the agent cannot escape to the node kernel) and a **network wall** (the agent can reach only what it needs).

## Compute wall: options

| Option                                                                                                                    | Boundary                                                                                    | Weight                                 | Fits this cluster                                                                                         | Notes                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Kata Containers (`kata-qemu`)**                                                                                         | Hardware VM per pod (own kernel, KVM)                                                       | ~150-300 MB RAM overhead, ~1-2 s start | **Already installed** on rbpi and rzbl (Talos extension, RuntimeClass `kata-qemu`). devil runs on it.     | Strongest local option. Normal pod spec + `runtimeClassName: kata-qemu`. Known quirk: Kata pods do not get Cilium socket-LB service translation, so ClusterIP calls from inside fail; use headless Services / pod IPs (same as devil).                                                                 |
| **gVisor (`runsc`)**                                                                                                      | User-space kernel intercepts syscalls                                                       | Light, fast start, no VM               | Talos has an official `gvisor` extension. Needs a schematic change + RuntimeClass.                        | Strong, but not a hardware boundary. Some syscalls/tools are slow or unsupported (heavy builds, some debuggers). Good middle ground.                                                                                                                                                                   |
| **bubblewrap (bwrap)**                                                                                                    | Linux namespaces + seccomp in the same kernel                                               | Very light                             | Inside a pod it needs unprivileged user namespaces (often blocked) or extra privileges.                   | This is what local agent CLIs use on a laptop. Inside Kubernetes it adds little over a normal container and shares the node kernel. **Not airtight.**                                                                                                                                                  |
| **Plain container + hardening**                                                                                           | Namespaces, seccomp, no caps, read-only root                                                | Lightest                               | Works today                                                                                               | Shares the node kernel. One kernel bug from the node. Not airtight.                                                                                                                                                                                                                                    |
| **Kubernetes Agent Sandbox** ([kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox), v1.0.11) | Orchestrator, not a boundary. Runs each sandbox as a pod on a RuntimeClass (Kata or gVisor) | One controller + CRDs                  | Fits directly: we have `kata-qemu`. CRDs come from the pinned upstream release (repo rule).               | SIG Apps project. CRDs: `Sandbox` (one stateful pod with stable identity and storage), `SandboxTemplate`, `SandboxWarmPool` (pre-started sandboxes hide Kata start time), `SandboxClaim` (take one from the pool). Python SDK. This is the Kubernetes-native version of what Daytona or boxd give you. |
| **Daytona (self-hosted)**                                                                                                 | Container sandboxes managed by a control plane (API, SDK, snapshots)                        | Heavy: control plane + DB + runners    | Possible on rzbl                                                                                          | A platform, not a boundary: isolation depends on the runtime under it. Useful when you want an API to create one sandbox per task. Overkill for one opencode.                                                                                                                                          |
| **boxd** ([docs](https://docs.boxd.sh/agents/agent-sandboxes))                                                            | KVM microVM per sandbox, egress allowlist, fork/snapshot                                    | No local weight                        | Hosted service (API key, console). Not self-hosted.                                                       | Very good isolation and features (fork before risky steps, `none` egress). But code and agent traffic leave home, and it costs money.                                                                                                                                                                  |
| **Docker Sandboxes / E2B / Firecracker**                                                                                  | microVM                                                                                     | Medium                                 | Docker Sandboxes is a desktop product. E2B self-host needs Firecracker infra (not on Talos without work). | Not a fit for this cluster now.                                                                                                                                                                                                                                                                        |

## Network wall (needed with every option)

- **Cilium egress policy** on the agent namespace (`CiliumNetworkPolicy` with `toFQDNs`): allow DNS, the LLM endpoints (Ollama pod, `api.anthropic.com` etc.), `git.0xbf.ch` and package registries. Deny everything else: no `10.10.0.0/16` (home LAN), no `10.20.20.0/24`, no `100.64.0.0/10` (tailnet), no other namespaces, no Kubernetes API.
- **No service account token** (`automountServiceAccountToken: false`).
- **Only the secrets the agent needs** (LLM key, a Forgejo token scoped to one bot user). No sops access.
- **Own namespace, own PVC**, resource limits, no hostPath, no privileged.
- **Login in front**: authentik forward-auth on `opencode.internal` (plus opencode's own password).

## Recommendation

**Kata (`kata-qemu`) as the boundary, Kubernetes Agent Sandbox as the manager, Cilium egress allowlist as the network wall, authentik in front.**

- **Kata** is a hardware VM boundary, the strongest option at home, and it is already installed and proven (devil). rzbl and rbpi are bare metal, so there is no nested-virtualization problem.
- **Agent Sandbox** adds what Daytona or boxd would give you, but native to Kubernetes and in git: a `SandboxTemplate` for "opencode agent on kata-qemu", a `SandboxWarmPool` with 1-2 started sandboxes so a new task does not wait for a VM boot, and a `SandboxClaim` per task or session. No extra platform, database or hosted service. Install = upstream CRDs (pinned release) + controller, like the other CRD sources in `cluster/crds.yaml`.
- **Cilium policy** closes the network side: deny all, allow DNS, Ollama, LLM APIs, `git.0xbf.ch`, package registries. No LAN, no tailnet, no other namespaces, no Kubernetes API, no service account token.
- **gVisor** stays the fallback if many parallel agents make Kata memory a problem (Agent Sandbox works with both).
- **boxd** stays the hosted option if you ever want sandboxes off your hardware.

Order when you approve:

1. opencode on `kata-qemu` + headless Ollama Service (single long-lived sandbox, simplest start).
2. `CiliumNetworkPolicy` for the agent namespace (deny-all + allowlist).
3. authentik forward-auth on `opencode.internal`.
4. Agent Sandbox (CRDs + controller) with a template and a small warm pool, when you want one sandbox per task.

## Step 4 as built (2026-11-17)

- Controller: `infrastructure/agent-sandbox/` (chart from the pinned GitRepository, extensions on). CRDs: `agent-sandbox-crds` in `cluster/crds.yaml`.
- `applications/agents/`: `SandboxTemplate opencode` (Kata, rzbl, emptyDir HOME, no SA token, restricted PodSecurity), `SandboxWarmPool opencode` (1), CNP `agent-isolation` (copy of opencode's).
- `networkPolicyManagement: Unmanaged`. The Managed default allows all public egress, and Cilium adds that to the allowlist.
- Take a sandbox with `scripts/sandbox.nu` (nushell, from the infra root):

```nu
use scripts/sandbox.nu *
sandbox new          # claims a warm VM, binds it to a free slot, prints https://sandbox-N.internal
sandbox ls
sandbox rm task-ab12c
```

- Slots: `sandbox-1..3.internal`, explicit names in `internal-hosts`, one authentik `forward_single` provider each (group `developers`), plus the LAN/tailnet allowlist. The helper creates a Service (selector `agents.x-k8s.io/claim-uid`) and an HTTPRoute labelled `0xbf.ch/slot`, both owned by the claim, so `sandbox rm` removes them.
- `kubectl port-forward` does not work: it dials localhost in the pod network namespace, and opencode listens inside the Kata VM.

Claims are runtime state, like whims: not in git. Delete the claim to end the VM.
