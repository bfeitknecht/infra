# Cluster Hardware Inventory: Development Repo Context (verified)

Home-lab Talos Linux Kubernetes cluster. One control plane `oci` in cloud. Two workers at home `rbpi` and `rzbl`. All nodes are provisioned with [topf](https://postfinance.github.io/topf). This file records hardware and provisioning state.

## Worker node `rbpi`: Raspberry Pi 5 (arm64)

### Host OS

- **Talos Linux 1.14.6** on Pi 5. Boot from microSD.
- **System extensions are in image:** `tailscale`, `nvme-cli`, `kata-containers`. See `talos/schematic.rbpi.yaml` with `rpi_5` overlay. See Cluster topology below.
- **NVMe support:** NVMe driver is in Talos kernel `CONFIG_BLK_DEV_NVME=y`. `nvme-cli` extension adds userspace tool. It is not a driver.
- Talos on Pi 5 is community-tested. It is not officially supported. Example is `rpi_5` imager target and community talos-rpi5 builder.
- Note: `dtparam=pciex1`, `dtparam=pciex1_gen=3`, `dtoverlay=pcie-32bit-dma-pi5` are Pi `config.txt` params. On Talos, bake them into image via imager `config.txt` mechanism or SBC overlay. Do not edit on running system.

### PCIe topology note

52Pi B12 splitter uses ASMedia PCIe switch (Gen2 variant). It supports two PCIe devices at same time. It limits link to **Gen 2**. Seeed dual M.2 HAT is PCIe 2.0 with ASM1182E switch. It can use Hailo8/8L/Coral but no accelerator is installed. Both M.2 slots hold NVMe SSDs (`/dev/nvme0n1`, `/dev/nvme1n1`). Gen 2 end-to-end is consistent. Limit is accepted by design.

## Worker node `rzbl`: Razer Blade 15 Base (2019), GTX 1660 Ti (amd64)

- **Model:** Razer Blade 15" Base – GTX 1660 Ti (2019), RZ09-03009
- **CPU:** 9th Gen Intel Core i7-9750H, 6 cores / 12 threads, 2.6 GHz base / 4.5 GHz turbo, 12 MB cache, Intel HM370 chipset
- **GPU:** NVIDIA GeForce GTX 1660 Ti, 6 GB GDDR6 (Turing, TU116. No RT cores. Full CUDA support.)
- **RAM:** 16 GB dual-channel DDR4-2667 (2x 8 GB), expandable to 32 GB
- **Storage:** M.2 NVMe PCIe 3.0 x4 SSD + 2.5" SATA slot
- **Ports:** 3x USB 3.2 Type-A, Thunderbolt 3 (USB-C), HDMI, mini-DisplayPort, Gigabit Ethernet
- **Wireless:** Intel Wireless-AC 9560 (802.11ac, Bluetooth 5)
- **Role in cluster:** Talos **worker** node `rzbl` at `10.10.20.11`. Control plane is OCI Ampere A1 `oci` at `10.20.20.10`. Pi `rbpi` is also worker. GTX 1660 Ti is the only discrete GPU in cluster. No other node has GPU.
- Note: 1660 Ti is CUDA-capable (Turing). It works with NVIDIA device plugin and GPU operator in Kubernetes. On Turing, Talos uses open-source NVIDIA modules `nvidia-open-gpu-kernel-modules-lts` + `nvidia-container-toolkit-lts` (580.x LTS). See `talos/schematic.rzbl.yaml`. Modules are baked into installer image. You cannot add extensions on running node.
- Note: `kata-containers` is also present (as on Pi). It provides `kata-qemu` handler and RuntimeClass `kata-qemu` for sandboxed workloads. Host GPU is not passed to kata VMs. That needs VFIO passthrough. It is not configured.

## Control-plane node `oci`: Oracle Cloud Ampere A1 (arm64)

- **Provider / region:** Oracle Cloud Infrastructure, `eu-zurich-1`
- **Shape:** Ampere A1 (Arm). **2 OCPU / 12 GB RAM** (as observed on running node)
- **CPU:** 2x Arm Neoverse-N1 (Ampere Altra; `CPU implementer 0x41`, `CPU part 0xd0c`), arm64
- **RAM:** 12 GB (`MemTotal` about 11.6 GiB), no swap
- **Boot disk:** 50 GB Block Volume (`/dev/sda`, virtio, model `BlockVolume`)
- **Network:** `eth0` (virtio). Private `10.20.20.10`, public `140.238.213.197`, tailnet `100.73.186.19` (cluster API endpoint)
- **Role:** control-plane node, tainted. Runs no workloads except `resolver` DNS pod (clean `:53` egress; home ISP firmware hijacks DNS on LAN segment)
- **Talos:** 1.14.6 running (declared 1.14.6); extensions: `tailscale`; `bootloader: sd-boot` (`talos/schematic.oci.yaml`)
- **Gotcha:** VCN security list allows only UDP 41641 (Tailscale WireGuard). No cluster ports are exposed. Manage over tailnet. Node tailscale key must never expire. Expired key takes API endpoint down.

## Cluster topology & Talos provisioning (verified)

Three nodes. All three are enrolled in `talos/topf.yaml` (oci, rbpi, rzbl). Applied with [topf](https://postfinance.github.io/topf).

| Node   | Role                          | Address                                 | Board                            | Talos extensions (schematic file)                                                                                                                             |
| ------ | ----------------------------- | --------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `oci`  | control-plane (tainted, none) | `10.20.20.10` (tailnet `100.73.186.19`) | Oracle Cloud Ampere A1 (arm64)   | `tailscale` (`talos/schematic.oci.yaml`, `bootloader: sd-boot`)                                                                                               |
| `rbpi` | worker                        | `10.10.20.10`                           | Raspberry Pi 5 (arm64)           | `nvme-cli`, `tailscale`, `kata-containers` + `rpi_5` overlay (`talos/schematic.rbpi.yaml`)                                                                    |
| `rzbl` | worker (planned)              | `10.10.20.11`                           | Razer Blade 15 Base 2019 (amd64) | `tailscale`, `intel-ucode`, `nvme-cli`, `kata-containers`, `nvidia-open-gpu-kernel-modules-lts`, `nvidia-container-toolkit-lts` (`talos/schematic.rzbl.yaml`) |

- Extensions are baked into installer image. They are selected by schematic ID. You cannot install them on running node. `topf` hashes each `schematic.*.yaml` to image-factory ID. Edit to schematic changes node image on next `topf upgrade`.
- Flow: Boot generic Talos media to maintenance mode. Run `topf apply` to write machine config. Run `topf upgrade` to re-image node when declared Talos version or schematic differs from running version. Custom boot media is needed only for first boot or recovery.
- Tailnet `--advertise-routes` are per node in `talos/patches/node/<host>/03-tailscale.yaml`: `oci` advertises `10.20.20.0/24`; `rbpi` advertises `10.10.10.0/24,10.10.20.0/24`.

## Parts List

| #   | Part                             | Spec/Variant                                                                                              | Qty | Total (CHF) | Ref. Number      | Date         |
| :-- | :------------------------------- | :-------------------------------------------------------------------------------------------------------- | :-- | :---------- | :--------------- | :----------- |
| 1   | Raspberry Pi 5                   | 16 GB RAM                                                                                                 | 1   | -           | -                | -            |
| 2   | Imou microSD                     | 64 GB, microSDXC, UHS-I, U3/V30 (boot, Talos Linux 1.14.6)                                                | 1   | 15.90       | -                | Delivered    |
| 3   | 52Pi Dual-FPC PCIe HAT (B12)     | ASMedia Gen2 PCIe switch, dual FPC out, bottlenecks to Gen 2 (accepted)                                   | 1   | 25.79       | 3050317770738061 | Mar 2, 2025  |
| 4   | Radxa ROCK Penta SATA HAT        | For RPi 5. 4x SATA + eSATA, JMB585 (needs `pcie-32bit-dma-pi5`), ships with its own custom FFC           | 1   | 62.49       | 3050317770718061 | Mar 2, 2025  |
| 5   | Seeed PCIe→Dual M.2 HAT          | 2x M.2 NVMe (both populated); Hailo/Coral-capable but no accelerator installed, PCIe 2.0, ASM1182E switch | 1   | 18.53       | 3052013889338061 | Mar 30, 2025 |
| 6   | SpotPear PCIE FPC cable          | PCIE-FPC-5CM-Bend, 90R differential. For Pi 5 to Seeed M.2 HAT link                                       | 1   | 2.70        | 3076228418308061 | Sep 13, 2026 |
| 7   | M.2 2280 NVMe heatsinks          | 6 mm, w/ thermal pad                                                                                      | 2   | 9.78        | 3076228418368061 | Sep 13, 2026 |
| 8   | Pi 5 Active Cooler (copper)      | Heatsink + acrylic plate, without fan                                                                     | 1   | 11.49       | 3073905593408061 | Jun 1, 2026  |
| 9   | Noctua NF-A4x20 5V PWM           | 40x40x20 mm, brown, 4-pin PWM (A2543), 5 V, max 0.1 A each. Damaged if run at 12V                        | 2   | 38.58       | -                | -            |
| 10  | ZY12PDN USB-C PD trigger         | Solder-pad ("Welding line") version, 5/9/12/15/20 V modes, set to 12V fixed                               | 1   | 1.85        | 3073944133918061 | Jun 8, 2026  |
| 11  | Molex IDE → floppy 4-pin adapter | 18 AWG, 30 cm. Alternate HAT power path (both ends female; source needs male pins)                       | 1   | 1.71        | 3073944133938061 | Jun 8, 2026  |
| 12  | 4-pin PWM Y-splitter             | 1-to-2, standard PC PWM pinout                                                                            | 1   | 1.58        | 3073944133958061 | Jun 8, 2026  |
| 13  | SH1.0 → Dupont breakout          | SH1.0 4P, 200 mm, Dupont 1P male. For the pin reorder                                                    | 1   | 2.32        | 3073944133978061 | Jun 8, 2026  |
| 14  | M2.5 brass standoffs             | 6 mm thread / 5 mm, 30 pcs                                                                                | 1   | 3.15        | 3073944134018061 | Jun 8, 2026  |
| 15  | Brass threaded rods              | M2.5 × 150 mm                                                                                             | 5   | 8.01        | 3073944133898061 | Jun 8, 2026  |
| 16  | Zyxel AX7501 router              | 10 GbE, 10G plan. Pi 5's Ethernet is 1 GbE, so throughput through the Pi caps at 1 Gb/s                  | 1   | -           | -                | -            |
| 17  | Razer Blade 15 Base (2019)       | i7-9750H, GTX 1660 Ti 6 GB, 16 GB DDR4-2667, TB3, GbE. Talos worker node                                 | 1   | -           | -                | -            |

**Known total: CHF 203.88** (plus Pi 5 16GB, AX7501, and Razer Blade. Prices not in the order data)

## Pin Layout: Pi Fan Header → Splitter (verified)

Pi 5 fan header is 4-pin, 1 mm pitch JST-SH socket. Standard PC PWM headers use different order. Use crossover via SH1.0→Dupont breakout:

| Pi 5 fan header pin | Signal        | Splitter pin (PC PWM standard) |
| :------------------ | :------------ | :----------------------------- |
| 1                   | +5V (red)     | 2 (+12V position)              |
| 2                   | PWM (blue)    | 4 (PWM)                        |
| 3                   | GND (black)   | 1 (GND)                        |
| 4                   | Tach (yellow) | 3 (Sense/Tach)                 |

- Noctua fans plug into splitter PC PWM headers (black GND / yellow Vcc / green RPM / blue PWM). They accept Pi 3.3 V / 25 kHz PWM signal.
- Two fans use 0.2 A max on fan header. This is within USB peripheral current budget. Pi is powered via HAT 40-pin feed.
- Warning: Do not feed splitter +12V pin from other source. 5 V fans are damaged at 12 V. +12 V position stays on Pi 5 V rail.
- Only one fan tach is returned on Y-splitter. CPU cooler fan must be tach master. Firmware spins fan at boot and enables 4-step auto curve (0% <50 C, 30% >=50 C, 50% >=60 C, 70% >=67.5 C, 100% >=75 C) only if tach shows rotation.

## Power Wiring: ZY12PDN → Penta SATA HAT (verified)

1. Set ZY12PDN to **12V fixed mode**: Hold button while plugging in. Rapid flash starts. Click to green. Hold about 1 s to save. Re-plug to confirm.
2. Solder **VOUT+ to barrel center pin** and **VOUT- to outer sleeve** on 5.5 x 2.5 mm plug. Penta HAT DC jack is 5.5/2.5 mm, center positive. Use 20-22 AWG wire. Heat-shrink both joints.
3. Recommended supply is **12V/5A (60 W)** for HAT + Pi + drives. 12V/3A works for SSDs. It is tight for 3.5" HDD spin-up. eSATA needs 12 V DC or ATX path. USB-C mode does not support eSATA.
4. Alternate path: Use Molex to floppy adapter into HAT D-shaped 4-pin input from ATX/SFX PSU.
5. Warning: No backfeed protection on HAT. 12 V barrel input and Molex pins are joined. Do not connect barrel and Molex at same time. Do not power Pi via own USB-C while HAT feeds it via 40-pin header.

## Build Outline

```
Zyxel AX7501 (10 GbE plan; Pi caps at 1 GbE) ── Ethernet ── Raspberry Pi 5 16GB
                                      │  Host OS: Talos Linux 1.14.6 (community port)
                                      │  Role: worker node (control plane = OCI Ampere A1)
                                      │  Extensions: tailscale, nvme-cli, kata-containers
                                      │  Boot: Imou 64GB microSD (UHS-I U3)
                                      │  config.txt params baked into Talos image:
                                      │    dtparam=pciex1, dtparam=pciex1_gen=3,
                                      │    dtoverlay=pcie-32bit-dma-pi5
                                      │
                                      ├─ Cooling (CPU):
                                      │    Copper active cooler + acrylic plate
                                      │    └─ Fan 1: Noctua NF-A4x20 5V PWM  [tach master. Required]
                                      │
                                      ├─ Cooling (secondary):
                                      │    Fan 2: Noctua NF-A4x20 5V PWM
                                      │    → NVMe heatsink / SATA HAT airflow
                                      │
                                      ├─ Fan wiring:
                                      │    Pi fan header (JST-SH 4-pin, 5V)
                                      │    └─ SH1.0→Dupont breakout (pin reorder:
                                      │         Pi1+5V→sp2, Pi2 PWM→sp4,
                                      │         Pi3 GND→sp1, Pi4 Tach→sp3)
                                      │        └─ 4-pin PWM Y-splitter
                                      │            ├─ Fan 1 (CPU cooler, tach master)
                                      │            └─ Fan 2 (drives)
                                      │    Warning: +12V splitter pin stays on Pi 5V rail
                                      │      (5V fans die at 12V)
                                      │
                                      └─ PCIe (single lane via 52Pi B12 ASMedia
                                           Gen2 switch. Gen 2 bottleneck accepted):
                                            ├─ Branch A: Radxa Penta SATA HAT
                                            │    ├─ 4x SATA drives + 1x eSATA (NAS)
                                            │    ├─ FFC: use Radxa INCLUDED custom
                                            │    │   cable (HAT-side connector differs)
                                            │    └─ Power: ZY12PDN (12V fixed, green LED)
                                            │         → 5.5/2.5mm barrel, center-positive
                                            │         (alt: ATX via Molex to floppy adapter)
                                            │         Warning: no backfeed protection. Never
                                            │           barrel + Molex at once, never Pi USB-C too
                                            └─ Branch B: Seeed Dual M.2 HAT (PCIe 2.0)
                                                 ├─ FFC: SpotPear 5cm bend cable
                                                 ├─ M.2 NVMe SSD (heatsink #1). Storage
                                                 └─ M.2 NVMe SSD #2 (heatsink #2). Storage (no AI accelerator)

Worker node rzbl (same tailnet / Talos cluster):
  Razer Blade 15 Base 2019 (RZ09-03009)
    ├─ Host OS: Talos Linux 1.14.6 (amd64)
    ├─ CPU: i7-9750H, 6C/12T, 2.6/4.5 GHz
    ├─ GPU: NVIDIA GTX 1660 Ti 6GB GDDR6 (CUDA, Turing)
    ├─ RAM: 16GB DDR4-2667 (max 32GB)
    ├─ Storage: M.2 NVMe PCIe 3.0 x4 + 2.5" SATA slot
    ├─ Network: GbE / Wi-Fi 5 (AC 9560). Joins over Tailscale
    ├─ Extensions: tailscale, intel-ucode, nvme-cli, kata-containers, nvidia-open-gpu-kernel-modules-lts, nvidia-container-toolkit-lts
    └─ Role: AI/GPU workloads (NVIDIA device plugin), heavy compute
```

## Assembly Checklist

1. **Power module first:** Set ZY12PDN to 12V fixed. Solder VOUT+ to barrel center, VOUT- to sleeve.
2. **PCIe chain:** Connect Pi 5 FFC port to 52Pi B12 to branch FFCs. Use Radxa included cable for Penta HAT. Use SpotPear cable for Seeed HAT. Seat FFCs with contacts correct. These links are fragile.
3. **Fans:** Wire per pin layout. Verify both Noctua are 4-pin PWM. Keep +12V splitter pin on Pi 5V rail. Put CPU cooler fan on tach-master branch.
4. **Stack:** Use M2.5 standoffs + threaded rods for layer spacing between Pi, B12, and HATs.
5. **Pre-power multimeter check (unverified):** Check if B12 40-pin pass-through carries Penta HAT 5V feed to Pi reliably. If not, rethink stack topology before first boot.
6. **Physical clearance (unverified):** Three-board stack (Pi + B12 + Penta HAT + back-mounted Seeed HAT with pogo pins) plus 6 mm heatsinks. Check cable routing and clearance before final assembly. Note 52Pi warning that B12 is incompatible with official Hailo AI HAT+. Your Seeed board is different. This matters only if you add AI accelerator.
7. **Talos provisioning:** Bake `dtparam=pciex1`, `dtparam=pciex1_gen=3`, `dtoverlay=pcie-32bit-dma-pi5` into image config.txt. Set machine config via boot medium. Install Tailscale extension. Use Talos disks/volumes for storage (NVMe + SATA). Fan control is automatic after tach is detected.
8. **Worker provisioning (rzbl):** Boot generic Talos media on Blade to maintenance mode. Add node to `talos/topf.yaml` with `schematicId: "@schematic.rzbl.yaml"` and node patch dir `talos/patches/node/rzbl/` (with real NIC name and NVMe `disk.dev_path`). Run `topf apply`. NVIDIA open-source driver extensions and tailscale/intel-ucode/nvme-cli come from schematic. Schedule GPU workloads via NVIDIA device plugin.
9. **Power-on order:** Power HAT barrel first. Let HAT feed Pi via 40-pin header. Do not power both.

## Bandwidth Note

All storage on Pi shares single PCIe lane. Link is limited to **Gen 2** by 52Pi B12. NVMe and SATA traffic share it. Do not expect full Gen 3 NVMe speed during heavy NAS transfers. This is accepted by design. It is fine for NAS workload. Network: AX7501 10G plan is limited to **1 GbE by Pi 5 Ethernet port**. Razer Blade GbE port has same 1 Gb/s cap. All inter-node LAN traffic is at gigabit speed. Router 10G capability does not change that.

Sources: [Razer Blade 15" Base GTX1660 Ti (2019) RZ09-03009 specs](https://mysupport.razer.com/app/answers/detail/a_id/3643), [iFixit Razer Blade 15 2019](https://www.ifixit.com/Device/Razer_Blade_15_2019), [Kingston memory compatibility RZ09-03009](https://www.kingston.com/en/memory/search/model/106608/razer-blade-15-base-gtx1660-ti-2019-rz09-03009)
