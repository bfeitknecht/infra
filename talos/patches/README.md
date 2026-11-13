# Talos patches: upgrade notes for 1.14.6

This directory holds per-layer patches merged as `all/ -> <role>/ -> node/<host>/`.

## Versions

- `talos/topf.yaml` declares `talosVersion: 1.14.6` (was 1.14.2).
- `kubernetesVersion: 1.35.3` unchanged.
- Schematics unchanged (`oci`, `rbpi`, `rzbl`) except version bump triggers new Image Factory ID. No extension rename needed (`nvidia-open-gpu-kernel-modules-lts` etc. still valid at 1.14.6).

## Document name changes (1.14.x)

Talos 1.14 splits `v1alpha1` into per-component documents. Deprecated fields remain supported but are mutually exclusive with their replacement unless noted.

- **Kubernetes**: `KubeClusterConfig`, `KubeAPIServerConfig`, `KubeletConfig`, `KubeNodeConfig`, `KubePrismConfig`, etc. See Upgrading Talos guide table.
- **Kernel/udev**: `SysctlConfig`, `SysfsConfig`, `KernelModuleConfig`, `UdevRulesConfig` — if both old and new are set, new takes precedence (not exclusive).
- **Install/files/CRI**: `UnattendedInstallConfig` (already in use), `EtcFileConfig`, `CRICustomizationConfig`.
- **Network**: `machine.network.interfaces` → `LinkConfig`/`DHCPv4Config`/`VLANConfig`; `machine.network.nameservers` → `ResolverConfig`; `machine.features.hostDNS` → `ResolverConfig.hostDNS`; `machine.features.kubePrism` → `KubePrismConfig`.

Current repo handling:

- `control-plane/02-network.yaml` and `node/*/02-network.yaml` still use `machine.network.interfaces` (DHCP) and `machine.sysctls`/`machine.certSANs`. These are deprecated but accepted in 1.14.6. No new `LinkConfig` or `SysctlConfig` document is emitted, so no conflict.
- `node/*/03-tailscale.yaml` uses `machine.env.TS_EXTRA_ARGS` — still valid.
- `node/rbpi/04-storage.yaml` uses `machine.disks` — deprecated since 1.10 in favor of `UserVolumeConfig` but still accepted. Migration to `UserVolumeConfig` is next step.

When bumping `topf` to 1.14 contract (if/when `talosctl gen config` emits new docs with mutual-exclusion validation), migrate:

- `machine.network.interfaces` → `LinkConfig` with `deviceSelector`/`DHCP`/`addresses`.
- `machine.certSANs` → `KubeAPIServerConfig` `certSANs`.
- `machine.sysctls` → `SysctlConfig` documents (or keep legacy; precedence is new).
- `machine.disks` → `UserVolumeConfig` (one doc per NVMe, `diskSelector` by `disk.dev_path` or `disk.transport`).

Do not migrate in this commit. Keep deprecated fields until every node reports 1.14.6.

## rzbl join steps

1. Boot generic Talos 1.14.6 metal image on Blade to maintenance mode.
2. Get IP (`ip addr` or DHCP lease table). Update `talos/topf.yaml` `nodes.rzbl.ip` if not `10.10.20.11`.
3. Ensure Blade NIC name matches schematic? Current `rbpi` uses `end0`; `oci` uses `eth0`; `rzbl` has no interface override (DHCP via default). Check `talosctl get links` in maintenance to confirm.
4. Run `topf apply --nodes 10.10.20.11` (or full apply when `oci` reachable over tailnet `100.73.186.19`).
5. Run `topf upgrade` if version skew.
6. Verify `talosctl health`, `kubectl get nodes`, GPU `nvidia-smi` via DaemonSet.

## Schematics

Extensions are baked into installer image. Change requires `topf upgrade` with new schematic ID. `factory.talos.dev` IDs are derived from `schematic.<node>.yaml`.

- `oci`: `tailscale` + `sd-boot`.
- `rbpi`: `rpi_5` overlay + `nvme-cli`, `tailscale`, `kata-containers`.
- `rzbl`: `tailscale`, `intel-ucode`, `nvme-cli`, `kata-containers`, `nvidia-open-gpu-kernel-modules-lts`, `nvidia-container-toolkit-lts`.

