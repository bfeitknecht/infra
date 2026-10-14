# Cluster Hardware Inventory — Development Repo Context (verified)

Home-lab Talos Linux Kubernetes cluster: one cloud control-plane node (`oci`) plus two home worker nodes (`rbpi`, `rzbl`), provisioned declaratively with [topf](https://postfinance.github.io/topf). This file records the hardware and provisioning state of every node.

## Worker node `rbpi` — Raspberry Pi 5 (arm64)

### Host OS

- **Talos Linux 1.14.2** running on the Pi 5, booted from the microSD
- **System extensions (baked into the image):** `tailscale` (mesh networking/remote access), `nvme-cli`, `kata-containers` — declared in `talos/schematic.rbpi.yaml` (with the `rpi_5` overlay). See "Cluster topology & Talos provisioning" below.
- **NVMe support:** the NVMe driver is built into the Talos kernel (`CONFIG_BLK_DEV_NVME=y`); the `nvme-cli` extension adds the `nvme` userspace tool on top (not a driver)
- Talos on Pi 5 is **community-tested, not officially supported** (e.g. via the `rpi_5` imager target / community talos-rpi5 builder)
- Note: `dtparam=pciex1`, `dtparam=pciex1_gen=3`, `dtoverlay=pcie-32bit-dma-pi5` are Raspberry Pi `config.txt` parameters — on Talos they must be **baked into the image** via the imager's config.txt mechanism (or the SBC overlay), not edited on a running system

### PCIe topology note

The 52Pi B12 splitter uses an ASMedia PCIe switch (Gen2 variant), explicitly supports connecting two PCIe devices simultaneously, and bottlenecks the link to **Gen 2**. The Seeed dual M.2 HAT is PCIe 2.0 (ASM1182E switch) and is Hailo8/8L/Coral-capable, **but no AI accelerator is installed** — both M.2 slots hold NVMe SSDs (`/dev/nvme0n1`, `/dev/nvme1n1`). Gen 2 end-to-end is consistent and the bottleneck is accepted by design.

## Worker node `rzbl` — Razer Blade 15 Base (2019), GTX 1660 Ti (amd64)

- **Model:** Razer Blade 15" Base – GTX 1660 Ti (2019), RZ09-03009
- **CPU:** 9th Gen Intel Core i7-9750H, 6 cores / 12 threads, 2.6 GHz base / 4.5 GHz max turbo, 12 MB cache, Intel HM370 chipset
- **GPU:** NVIDIA GeForce GTX 1660 Ti, 6 GB GDDR6 (Turing, TU116 — no RT cores, but full CUDA compute support)
- **RAM:** 16 GB dual-channel DDR4-2667 (2× 8 GB), expandable to 32 GB
- **Storage:** M.2 NVMe PCIe 3.0 x4 SSD + 2.5" SATA slot
- **Ports:** 3× USB 3.2 Type-A, Thunderbolt 3 (USB-C), HDMI, mini-DisplayPort, Gigabit Ethernet
- **Wireless:** Intel Wireless-AC 9560 (802.11ac, Bluetooth 5)
- **Role in the cluster:** Talos **worker** node (`rzbl`, IP `10.10.20.11`). The cluster's control plane is the **OCI Ampere A1** node (`oci`, `10.20.20.10`) — the Pi (`rbpi`) is a worker too. The GTX 1660 Ti is the cluster's only discrete GPU / AI-compute accelerator; neither the Pi nor the OCI node has one.
- Note: the 1660 Ti is CUDA-capable (Turing architecture), so it works with the NVIDIA device plugin / GPU operator patterns in Kubernetes. On Turing, Talos uses the **open-source** NVIDIA kernel modules — `nvidia-open-gpu-kernel-modules-lts` + `nvidia-container-toolkit-lts` (driver branch 580.x LTS) — declared in `talos/schematic.rzbl.yaml` and baked into the installer image (extensions can't be added to a running node).
- Note: `kata-containers` is included too (as on the Pi) — the `kata-qemu` containerd handler / RuntimeClass `kata-qemu` for sandboxed workloads. The host GPU is **not** passed into kata VMs (that needs VFIO passthrough, which isn't configured).

## Control-plane node `oci` — Oracle Cloud Ampere A1 (arm64)

- **Provider / region:** Oracle Cloud Infrastructure, `eu-zurich-1`
- **Shape:** Ampere A1 (Arm) — **2 OCPU / 12 GB RAM** (as observed on the running node)
- **CPU:** 2× Arm Neoverse-N1 (Ampere Altra; `CPU implementer 0x41`, `CPU part 0xd0c`), arm64
- **RAM:** 12 GB (`MemTotal` ≈ 11.6 GiB), no swap
- **Boot disk:** 50 GB Block Volume (`/dev/sda`, virtio, model `BlockVolume`)
- **Network:** `eth0` (virtio) — private `10.20.20.10`, public `140.238.213.197`, tailnet `100.73.186.19` (the cluster API endpoint)
- **Role:** control-plane node, tainted — runs no workloads except the `resolver` DNS pod (clean `:53` egress; the home ISP firmware hijacks DNS on the LAN segment)
- **Talos:** 1.14.0 running (declared 1.14.2); extensions: `tailscale`; `bootloader: sd-boot` (`talos/schematic.oci.yaml`)
- **Gotcha:** the VCN security list opens only UDP 41641 (Tailscale WireGuard) — no cluster ports exposed; management is over the tailnet, and the node's tailscale key must never expire (an expired key takes the API endpoint down)

## Cluster topology & Talos provisioning (verified)

Three nodes. `oci` and `rbpi` are enrolled in `talos/topf.yaml`; `rzbl`'s patches are drafted (`talos/patches/node/rzbl/`) but the node is not yet in the roster — an unreachable node aborts `topf apply`, so it's added only once the Blade is online. Applied with [topf](https://postfinance.github.io/topf).

| Node   | Role                          | Address                                 | Board                            | Talos extensions (schematic file)                                                                                                                             |
| ------ | ----------------------------- | --------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `oci`  | control-plane (tainted, none) | `10.20.20.10` (tailnet `100.73.186.19`) | Oracle Cloud Ampere A1 (arm64)   | `tailscale` (`talos/schematic.oci.yaml`, `bootloader: sd-boot`)                                                                                               |
| `rbpi` | worker                        | `10.10.20.10`                           | Raspberry Pi 5 (arm64)           | `nvme-cli`, `tailscale`, `kata-containers` + `rpi_5` overlay (`talos/schematic.rbpi.yaml`)                                                                    |
| `rzbl` | worker (planned)              | `10.10.20.11`                           | Razer Blade 15 Base 2019 (amd64) | `tailscale`, `intel-ucode`, `nvme-cli`, `kata-containers`, `nvidia-open-gpu-kernel-modules-lts`, `nvidia-container-toolkit-lts` (`talos/schematic.rzbl.yaml`) |

- Extensions are **baked into the installer image**, selected by a schematic ID — they cannot be installed on a running node. `topf` hashes each `schematic.*.yaml` to the image-factory ID; editing a schematic changes the node's image on the next `topf upgrade`.
- Flow: boot generic Talos media → maintenance mode → `topf apply` writes the machine config; `topf upgrade` re-images a node only when its declared Talos version **or** schematic differs from what is running. Custom (schematic-built) boot media is only needed for the first boot or recovery.
- Tailnet `--advertise-routes` are per node (`talos/patches/node/<host>/03-tailscale.yaml`): `oci` → `10.20.20.0/24`; `rbpi` → `10.10.10.0/24,10.10.20.0/24`.

## Parts List

| #   | Part                             | Spec/Variant                                                                                              | Qty | Total (CHF) | Ref. Number      | Date         |
| :-- | :------------------------------- | :-------------------------------------------------------------------------------------------------------- | :-- | :---------- | :--------------- | :----------- |
| 1   | Raspberry Pi 5                   | 16 GB RAM                                                                                                 | 1   | —           | —                | —            |
| 2   | Imou microSD                     | 64 GB, microSDXC, UHS-I, U3/V30 (boot, Talos Linux 1.14.2)                                                | 1   | 15.90       | —                | Delivered    |
| 3   | 52Pi Dual-FPC PCIe HAT (B12)     | ASMedia Gen2 PCIe switch, dual FPC out, bottlenecks to Gen 2 (accepted)                                   | 1   | 25.79       | 3050317770738061 | Mar 2, 2025  |
| 4   | Radxa ROCK Penta SATA HAT        | For RPi 5 — 4× SATA + eSATA, JMB585 (needs `pcie-32bit-dma-pi5`), ships with its own custom FFC           | 1   | 62.49       | 3050317770718061 | Mar 2, 2025  |
| 5   | Seeed PCIe→Dual M.2 HAT          | 2× M.2 NVMe (both populated); Hailo/Coral-capable but no accelerator installed, PCIe 2.0, ASM1182E switch | 1   | 18.53       | 3052013889338061 | Mar 30, 2025 |
| 6   | SpotPear PCIE FPC cable          | PCIE-FPC-5CM-Bend, 90R differential — for Pi 5 ↔ Seeed M.2 HAT link                                       | 1   | 2.70        | 3076228418308061 | Sep 13, 2026 |
| 7   | M.2 2280 NVMe heatsinks          | 6 mm, w/ thermal pad                                                                                      | 2   | 9.78        | 3076228418368061 | Sep 13, 2026 |
| 8   | Pi 5 Active Cooler (copper)      | Heatsink + acrylic plate, without fan                                                                     | 1   | 11.49       | 3073905593408061 | Jun 1, 2026  |
| 9   | Noctua NF-A4x20 5V PWM           | 40×40×20 mm, brown, 4-pin PWM (A2543), 5 V, max 0.1 A each — damaged if run at 12V                        | 2   | 38.58       | —                | —            |
| 10  | ZY12PDN USB-C PD trigger         | Solder-pad ("Welding line") version, 5/9/12/15/20 V modes, set to 12V fixed                               | 1   | 1.85        | 3073944133918061 | Jun 8, 2026  |
| 11  | Molex IDE → floppy 4-pin adapter | 18 AWG, 30 cm — alternate HAT power path (both ends female; source needs male pins)                       | 1   | 1.71        | 3073944133938061 | Jun 8, 2026  |
| 12  | 4-pin PWM Y-splitter             | 1-to-2, standard PC PWM pinout                                                                            | 1   | 1.58        | 3073944133958061 | Jun 8, 2026  |
| 13  | SH1.0 → Dupont breakout          | SH1.0 4P, 200 mm, Dupont 1P male — for the pin reorder                                                    | 1   | 2.32        | 3073944133978061 | Jun 8, 2026  |
| 14  | M2.5 brass standoffs             | 6 mm thread / 5 mm, 30 pcs                                                                                | 1   | 3.15        | 3073944134018061 | Jun 8, 2026  |
| 15  | Brass threaded rods              | M2.5 × 150 mm                                                                                             | 5   | 8.01        | 3073944133898061 | Jun 8, 2026  |
| 16  | Zyxel AX7501 router              | 10 GbE, 10G plan — Pi 5's Ethernet is 1 GbE, so throughput through the Pi caps at 1 Gb/s                  | 1   | —           | —                | —            |
| 17  | Razer Blade 15 Base (2019)       | i7-9750H, GTX 1660 Ti 6 GB, 16 GB DDR4-2667, TB3, GbE — Talos worker node                                 | 1   | —           | —                | —            |

**Known total: CHF 203.88** (plus Pi 5 16GB, AX7501, and Razer Blade — prices not in the order data)

## Pin Layout — Pi Fan Header → Splitter (verified)

Pi 5 fan header is a 4-pin, 1 mm pitch JST-SH socket; standard PC PWM headers use a different order, hence the crossover via the SH1.0→Dupont breakout:

| Pi 5 fan header pin | Signal        | Splitter pin (PC PWM standard) |
| :------------------ | :------------ | :----------------------------- |
| 1                   | +5V (red)     | 2 (+12V position)              |
| 2                   | PWM (blue)    | 4 (PWM)                        |
| 3                   | GND (black)   | 1 (GND)                        |
| 4                   | Tach (yellow) | 3 (Sense/Tach)                 |

- Noctua NF-A4x20 5V PWM fans plug directly into the splitter's PC PWM headers (black GND / yellow Vcc / green RPM / blue PWM); they accept the Pi's 3.3 V / 25 kHz PWM signal.
- Two fans = 0.2 A max on the fan header, comfortably within the USB peripheral current budget (Pi is powered via the HAT's 40-pin feed).
- Warning: the splitter's +12V pin must never be fed from anything else — the 5V Noctua fans will be damaged at 12V. The +12V position stays on the Pi's 5V rail.
- Only one fan's tach is passed back on the Y-splitter — the **CPU cooler fan must be the tach master**; the firmware spins the fan at boot and enables the 4-step auto curve (0% <50 °C, 30% ≥50 °C, 50% ≥60 °C, 70% ≥67.5 °C, 100% ≥75 °C) only if tach shows rotation.

## Power Wiring — ZY12PDN → Penta SATA HAT (verified)

1. ZY12PDN set to **12V fixed mode**: hold button while plugging in → rapid flash → click to green → hold ~1 s to save; re-plug to confirm.
2. Solder **VOUT+ → barrel center pin**, **VOUT− → outer sleeve** on a 5.5 × 2.5 mm plug; the Penta HAT's DC jack is 5.5/2.5 mm, **center positive**. 20–22 AWG wire, heat-shrink both joints.
3. Recommended supply: **12V/5A (60 W)** for HAT + Pi + drives; 12V/3A works for SSDs but is tight for 3.5″ HDD spin-up. eSATA requires the 12V DC or ATX path (not USB-C mode).
4. Alternate path: Molex→floppy adapter into the HAT's D-shaped 4-pin input from an ATX/SFX PSU.
5. Warning: **no backfeed protection on the HAT** — the 12V barrel input and Molex pins are electrically joined. Never connect barrel and Molex simultaneously, and never power the Pi via its own USB-C while the HAT feeds it through the 40-pin header.

## Build Outline

```
Zyxel AX7501 (10 GbE plan; Pi caps at 1 GbE) ── Ethernet ── Raspberry Pi 5 16GB
                                      │  Host OS: Talos Linux 1.14.2 (community port)
                                      │  Role: worker node (control plane = OCI Ampere A1)
                                      │  Extensions: tailscale, nvme-cli, kata-containers
                                      │  Boot: Imou 64GB microSD (UHS-I U3)
                                      │  config.txt params baked into Talos image:
                                      │    dtparam=pciex1, dtparam=pciex1_gen=3,
                                      │    dtoverlay=pcie-32bit-dma-pi5
                                      │
                                      ├─ Cooling (CPU):
                                      │    Copper active cooler + acrylic plate
                                      │    └─ Fan 1: Noctua NF-A4x20 5V PWM  [tach master — required]
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
                                           Gen2 switch — Gen 2 bottleneck accepted):
                                            ├─ Branch A: Radxa Penta SATA HAT
                                            │    ├─ 4× SATA drives + 1× eSATA (NAS)
                                            │    ├─ FFC: use Radxa's INCLUDED custom
                                            │    │   cable (HAT-side connector differs)
                                            │    └─ Power: ZY12PDN (12V fixed, green LED)
                                            │         → 5.5/2.5mm barrel, center-positive
                                            │         (alt: ATX via Molex→floppy adapter)
                                            │         Warning: no backfeed protection — never
                                            │           barrel + Molex at once, never Pi USB-C too
                                            └─ Branch B: Seeed Dual M.2 HAT (PCIe 2.0)
                                                 ├─ FFC: SpotPear 5cm bend cable
                                                 ├─ M.2 NVMe SSD (heatsink #1) — storage
                                                 └─ M.2 NVMe SSD #2 (heatsink #2) — storage (no AI accelerator)

Worker node rzbl (same tailnet / Talos cluster):
  Razer Blade 15 Base 2019 (RZ09-03009)
    ├─ Host OS: Talos Linux 1.14.2 (amd64)
    ├─ CPU: i7-9750H, 6C/12T, 2.6/4.5 GHz
    ├─ GPU: NVIDIA GTX 1660 Ti 6GB GDDR6 (CUDA, Turing)
    ├─ RAM: 16GB DDR4-2667 (max 32GB)
    ├─ Storage: M.2 NVMe PCIe 3.0 x4 + 2.5" SATA slot
    ├─ Network: GbE / Wi-Fi 5 (AC 9560) — joins over Tailscale
    ├─ Extensions: tailscale, intel-ucode, nvme-cli, kata-containers, nvidia-open-gpu-kernel-modules-lts, nvidia-container-toolkit-lts
    └─ Role: AI/GPU workloads (NVIDIA device plugin), heavy compute
```

## Assembly Checklist

1. **Power module first:** set ZY12PDN to 12V fixed mode, then solder VOUT+ → barrel center, VOUT− → sleeve.
2. **PCIe chain:** Pi 5 FFC port → 52Pi B12 → branch FFCs — **Radxa's included cable for the Penta HAT** (its HAT-side connector differs from a plain Pi 5 FFC), **SpotPear cable for the Seeed M.2 HAT**. Seat FFCs with contacts facing correctly; these are the most fragile links.
3. **Fans:** wire per the pin layout above; verify both Noctua units are the 4-pin PWM version; keep the +12V splitter pin on the Pi's 5V rail; CPU-cooler fan on the tach-master branch.
4. **Stack:** M2.5 standoffs + threaded rods for layer spacing between Pi, B12, and HATs.
5. **Pre-power multimeter check (unverified by any documentation):** whether the B12's 40-pin pass-through reliably carries the Penta HAT's 5V feed down to the Pi. If it doesn't pass power cleanly, the stack topology needs rethinking before first boot.
6. **Physical clearance (unverified):** three-board stack (Pi + B12 + Penta HAT floating at standoff height + back-mounted Seeed HAT with pogo pins) plus 6 mm heatsinks — check cable routing and clearance before final assembly. Note 52Pi's warning that the B12 is incompatible with the _official_ Hailo AI HAT+ (your Seeed board is a different product) — relevant only if you ever add an AI accelerator.
7. **Talos provisioning:** bake `dtparam=pciex1`, `dtparam=pciex1_gen=3`, `dtoverlay=pcie-32bit-dma-pi5` into the image's config.txt; machine config via the boot medium; Tailscale extension installed; storage (NVMe + SATA) consumed through Talos disks/volumes. Fan control is automatic once tach is detected.
8. **Worker node provisioning (rzbl):** boot generic Talos media on the Blade → maintenance mode → add it to `talos/topf.yaml` with `schematicId: "@schematic.rzbl.yaml"` plus a node patch dir (`talos/patches/node/rzbl/`, with the real NIC name and NVMe `disk.dev_path`) → `topf apply`. The NVIDIA open-source driver extensions (and tailscale/intel-ucode/nvme-cli) come from the schematic; schedule GPU workloads via the NVIDIA device plugin.
9. **Power-on order:** HAT barrel power first, then let the HAT feed the Pi via the 40-pin header — never both.

## Bandwidth Note

All storage on the Pi shares the single PCIe lane, bottlenecked to **Gen 2** by the 52Pi B12 splitter — NVMe and SATA traffic split it, so don't expect full Gen 3 NVMe speed during heavy NAS transfers. Accepted by design; fine for the NAS workload. Network side: the AX7501's 10G plan is bottlenecked to **1 GbE by the Pi 5's Ethernet port** — the Razer Blade's GbE port has the same 1 Gb/s cap, so all inter-node traffic over the LAN runs at gigabit speed regardless of the router's 10G capability.

Sources: [Razer Blade 15" Base GTX1660 Ti (2019) RZ09-03009 specs](https://mysupport.razer.com/app/answers/detail/a_id/3643), [iFixit Razer Blade 15 2019](https://www.ifixit.com/Device/Razer_Blade_15_2019), [Kingston memory compatibility RZ09-03009](https://www.kingston.com/en/memory/search/model/106608/razer-blade-15-base-gtx1660-ti-2019-rz09-03009)
