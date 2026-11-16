# Agent isolation for opencode: options and recommendation

Status 2026-11-16. Research only. Nothing is implemented.

Goal: coding agents (opencode web, later others) run arbitrary commands. They must not reach the cluster, the home LAN, secrets, or other workloads. "Airtight" means two walls: a **compute wall** (the agent cannot escape to the node kernel) and a **network wall** (the agent can reach only what it needs).

## Compute wall: options

| Option | Boundary | Weight | Fits this cluster | Notes |
| --- | --- | --- | --- | --- |
| **Kata Containers (`kata-qemu`)** | Hardware VM per pod (own kernel, KVM) | ~150-300 MB RAM overhead, ~1-2 s start | **Already installed** on rbpi and rzbl (Talos extension, RuntimeClass `kata-qemu`). devil runs on it. | Strongest local option. Normal pod spec + `runtimeClassName: kata-qemu`. Known quirk: Kata pods do not get Cilium socket-LB service translation, so ClusterIP calls from inside fail; use headless Services / pod IPs (same as devil). |
| **gVisor (`runsc`)** | User-space kernel intercepts syscalls | Light, fast start, no VM | Talos has an official `gvisor` extension. Needs a schematic change + RuntimeClass. | Strong, but not a hardware boundary. Some syscalls/tools are slow or unsupported (heavy builds, some debuggers). Good middle ground. |
| **bubblewrap (bwrap)** | Linux namespaces + seccomp in the same kernel | Very light | Inside a pod it needs unprivileged user namespaces (often blocked) or extra privileges. | This is what local agent CLIs use on a laptop. Inside Kubernetes it adds little over a normal container and shares the node kernel. **Not airtight.** |
| **Plain container + hardening** | Namespaces, seccomp, no caps, read-only root | Lightest | Works today | Shares the node kernel. One kernel bug from the node. Not airtight. |
| **Daytona (self-hosted)** | Container sandboxes managed by a control plane (API, SDK, snapshots) | Heavy: control plane + DB + runners | Possible on rzbl | A platform, not a boundary: isolation depends on the runtime under it. Useful when you want an API to create one sandbox per task. Overkill for one opencode. |
| **boxd** ([docs](https://docs.boxd.sh/agents/agent-sandboxes)) | KVM microVM per sandbox, egress allowlist, fork/snapshot | No local weight | Hosted service (API key, console). Not self-hosted. | Very good isolation and features (fork before risky steps, `none` egress). But code and agent traffic leave home, and it costs money. |
| **Docker Sandboxes / E2B / Firecracker** | microVM | Medium | Docker Sandboxes is a desktop product. E2B self-host needs Firecracker infra (not on Talos without work). | Not a fit for this cluster now. |

## Network wall (needed with every option)

- **Cilium egress policy** on the agent namespace (`CiliumNetworkPolicy` with `toFQDNs`): allow DNS, the LLM endpoints (Ollama pod, `api.anthropic.com` etc.), `git.0xbf.ch` and package registries. Deny everything else: no `10.10.0.0/16` (home LAN), no `10.20.20.0/24`, no `100.64.0.0/10` (tailnet), no other namespaces, no Kubernetes API.
- **No service account token** (`automountServiceAccountToken: false`).
- **Only the secrets the agent needs** (LLM key, a Forgejo token scoped to one bot user). No sops access.
- **Own namespace, own PVC**, resource limits, no hostPath, no privileged.
- **Login in front**: authentik forward-auth on `opencode.internal` (plus opencode's own password).

## Recommendation

**Kata (`kata-qemu`) + Cilium egress allowlist + authentik in front.**

- Kata is a hardware VM boundary, the strongest option you can run at home, and it is already installed and proven (devil). No new extension, no new platform. It is a two-line change on the opencode Deployment (`runtimeClassName: kata-qemu`, Ollama reached by pod IP / headless Service).
- The Cilium policy closes the network side, which matters as much as the kernel wall: an agent in a perfect VM with open egress can still attack the LAN.
- Later, if you want one throwaway sandbox per task (fork, snapshot, parallel agents), add a sandbox manager on top of Kata. Self-hosted Daytona or a small controller fits then. boxd is the easiest hosted path if you accept that code leaves home.
- gVisor is the fallback if Kata start time or memory becomes a problem (many parallel agents).

Order when you approve: opencode `runtimeClassName: kata-qemu` + headless Ollama Service, then `CiliumNetworkPolicy` (deny-all + allowlist), then authentik forward-auth, then the opencode secret and un-suspend.
