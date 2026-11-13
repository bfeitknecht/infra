# Talos patches: 1.14.6

All nodes target Talos 1.14.6. Patches use per-component documents where 1.14 deprecated the v1alpha1 fields.

## Versions

- `talos/topf.yaml` `talosVersion: 1.14.6`, `kubernetesVersion: 1.35.3`.
- Schematics (`oci`, `rbpi`, `rzbl`) unchanged. No extension rename at 1.14.6. New Image Factory ID is derived on `topf upgrade`.
- Host OS: Talos Linux 1.14.6 on all nodes (was 1.14.2).

## Document name changes (1.14.x)

Talos 1.14 splits `v1alpha1` into focused documents. Deprecated fields are still accepted but mutually exclusive with their replacement unless noted.

- **Kubernetes**: `KubeClusterConfig`, `KubeAPIServerConfig`, `KubeletConfig`, `KubeNodeConfig`, `KubePrismConfig`, etc.
- **Kernel/udev**: `SysctlConfig`, `SysfsConfig`, `KernelModuleConfig`, `UdevRulesConfig` — new doc takes precedence on conflict (not exclusive).
- **Install/files/CRI**: `UnattendedInstallConfig` (already in use), `EtcFileConfig`, `CRICustomizationConfig`.
- **Network**: `machine.network.interfaces` → `DHCPv4Config`/`LinkConfig`/`VLANConfig`; `machine.network.nameservers` → `ResolverConfig`; `machine.features.hostDNS` → `ResolverConfig.hostDNS`.
- **Storage**: `machine.disks` → `UserVolumeConfig` (deprecated since 1.10).

Repo mapping:

- `control-plane/02-network.yaml`: `DHCPv4Config` for `eth0` + `SysctlConfig` for `net.ipv4.ip_forward`/`net.ipv6.conf.all.forwarding`; `machine.certSANs` stays in v1alpha1 (not deprecated).
- `node/rbpi/02-network.yaml`: `DHCPv4Config` for `end0` + `SysctlConfig`.
- `node/rzbl/02-network.yaml`: `DHCPv4Config` for `eth0` + `SysctlConfig`. Verify link name with `talosctl get links` (update if Blade reports `enp*`).
- `node/rbpi/04-storage.yaml`: `UserVolumeConfig` for `storage-nvme0` and `storage-nvme1` with `disk.dev_path` selector, `grow: true`, `filesystem.type: xfs`.
- `node/*/03-tailscale.yaml`: `machine.env.TS_EXTRA_ARGS` — still valid, not deprecated.
- `node/rzbl/04-logind.yaml`: `EtcFileConfig` for `systemd/logind.conf` with `HandleLidSwitch=ignore` (and docked/external-power) so closing lid does not suspend; `HandlePowerKey=ignore` prevents power-button shutdown.
- `all/03-cni.yaml`: `KubeFlannelCNIConfig $patch: delete` — already per-component, disables Flannel (we use Cilium).

## rzbl join (10.10.20.11)

1. Boot generic Talos 1.14.6 metal image on Blade to maintenance mode.
2. Confirm IP is 10.10.20.11 and link name is eth0 (run `ip addr` or check DHCP lease table; `talosctl get links` shows name).
3. `topf apply` (all nodes) or `topf apply --nodes 10.10.20.11` if oci is unreachable. This writes machine config.
4. `topf upgrade` if declared version differs from running.
5. Verify `talosctl health`, `kubectl get nodes`, GPU `nvidia-smi` via plugin DaemonSet.

## Schematics

- `oci`: `tailscale` + `sd-boot`.
- `rbpi`: `rpi_5` overlay + `nvme-cli`, `tailscale`, `kata-containers`.
- `rzbl`: `tailscale`, `intel-ucode`, `nvme-cli`, `kata-containers`, `nvidia-open-gpu-kernel-modules-lts`, `nvidia-container-toolkit-lts`.

