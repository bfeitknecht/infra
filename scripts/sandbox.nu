# Agent sandboxes: one throwaway opencode Kata VM per task.
# See docs/AGENT_ISOLATION.md. Use from the infra root:
#
#   use scripts/sandbox.nu *
#   sandbox new            # claim a warm VM, bind it to a free slot, print the URL
#   sandbox ls             # claims and their slots
#   sandbox rm <claim>     # end the VM; its Service and route go with it
#
# A slot is one of sandbox-1..3.internal (explicit names in the internal-hosts
# certificate, authentik provider per host, group developers). The Service and
# HTTPRoute a claim gets are owned by the claim: deleting the claim deletes them.
# Like the claims, they are runtime state and not in git.
# kubectl port-forward does not work: Kata pods listen inside the VM.

const SLOTS = [sandbox-1 sandbox-2 sandbox-3]
const NS = "agents"
const CLAIM_API = "extensions.agents.x-k8s.io/v1beta1"
# The kubeconfig in the infra root, next to scripts/.
const KUBECONFIG = (path self | path dirname | path dirname | path join kubeconfig)

def --wrapped kc [...args] {
    ^kubectl --kubeconfig $KUBECONFIG -n $NS ...$args
}

def apply [manifest: record] {
    $manifest | to json | kc apply -f - | ignore
}

# Claim a warm VM and bind it to a free slot.
export def "sandbox new" [
    name?: string  # claim name (default: task-<random>)
] {
    let used = (kc get httproute -l "0xbf.ch/slot" -o json | from json | get items
        | each {|r| $r.metadata.labels."0xbf.ch/slot" })
    let free = ($SLOTS | where {|s| $s not-in $used })
    if ($free | is-empty) {
        error make { msg: $"all slots busy: ($used | str join ', '). Free one with `sandbox rm`." }
    }
    let slot = ($free | first)
    let claim = ($name | default $"task-(random chars --length 5 | str lowercase)")

    apply {
        apiVersion: $CLAIM_API, kind: SandboxClaim,
        metadata: { name: $claim, namespace: $NS },
        spec: { warmPoolRef: { name: opencode } }
    }
    kc wait $"sandboxclaim/($claim)" --for=condition=Ready --timeout=5m | ignore
    let uid = (kc get sandboxclaim $claim -o json | from json | get metadata.uid)
    let owner = [{ apiVersion: $CLAIM_API, kind: SandboxClaim, name: $claim, uid: $uid, blockOwnerDeletion: false }]

    # The claimed pod carries the claim UID as a label.
    apply {
        apiVersion: v1, kind: Service,
        metadata: { name: $claim, namespace: $NS, ownerReferences: $owner },
        spec: { selector: { "agents.x-k8s.io/claim-uid": $uid }, ports: [{ name: http, port: 80, targetPort: 4096 }] }
    }
    let ext = {|name| { type: ExtensionRef, extensionRef: { group: traefik.io, kind: Middleware, name: $name } } }
    apply {
        apiVersion: gateway.networking.k8s.io/v1, kind: HTTPRoute,
        metadata: { name: $claim, namespace: $NS, labels: { "0xbf.ch/slot": $slot }, ownerReferences: $owner },
        spec: {
            parentRefs: [{ name: traefik-gateway, namespace: ingress, sectionName: websecure-internal }],
            hostnames: [$"($slot).internal"],
            rules: [
                # authentik forward-auth callback on this host.
                {
                    matches: [{ path: { type: PathPrefix, value: /outpost.goauthentik.io } }],
                    filters: [(do $ext internal-allowlist)],
                    backendRefs: [{ name: authentik-server, namespace: authentik, port: 80 }]
                },
                {
                    filters: [(do $ext internal-allowlist), (do $ext authentik)],
                    backendRefs: [{ name: $claim, port: 80 }]
                }
            ]
        }
    }
    let url = $"https://($slot).internal"
    print $"($claim) -> ($url)"
    $url
}

# Claims, their VMs and slots.
export def "sandbox ls" [] {
    let routes = (kc get httproute -l "0xbf.ch/slot" -o json | from json | get items
        | each {|r| { claim: $r.metadata.name, slot: $r.metadata.labels."0xbf.ch/slot" } })
    kc get sandboxclaim -o json | from json | get items | each {|c|
        let slot = ($routes | where claim == $c.metadata.name | get slot.0? | default "-")
        {
            claim: $c.metadata.name,
            vm: ($c.status.sandbox.name? | default "-"),
            ready: ($c.status.conditions? | default [] | where type == Ready | get status.0? | default "-"),
            url: (if $slot == "-" { "-" } else { $"https://($slot).internal" }),
            age: ((date now) - ($c.metadata.creationTimestamp | into datetime) | format duration min)
        }
    }
}

# End a VM. Its Service and route are deleted with the claim.
export def "sandbox rm" [claim: string] {
    kc delete sandboxclaim $claim --wait=false
}
