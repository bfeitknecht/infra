#!/usr/bin/env python3
"""Patch Arachnidium's addon.py for in-pod proxy use.

The desktop product runs mitmproxy in wireguard mode, spawns its own bun-api,
generates a client WireGuard config (with an ipify call) and fetches the ad
blocklist on every start. In the pod: entrypoint.sh owns bun-api; mitmdump
runs in regular proxy mode; the blocklist is baked into the image.

Each patch is an exact-anchor replacement. A change in the pinned commit
fails the build instead of silently drifting.
"""

import pathlib
import sys

ADDON = pathlib.Path("/opt/arachnidium/addon.py")


def replace_once(text: str, old: str, new: str, what: str) -> str:
    count = text.count(old)
    if count != 1:
        sys.exit(f"patch: '{what}' matched {count} times, expected 1")
    return text.replace(old, new)


def main() -> None:
    text = ADDON.read_text()

    # 1. The entrypoint starts bun-api; the addon must not spawn it again.
    text = replace_once(
        text,
        """  # Start Bun API
  bun_binary_name = "bun-api/bun" if os.name == "posix" else "bun-api/bun.exe"
  if os.path.exists(bun_binary_name):
    global bun_api_process
    bun_api_process = subprocess.Popen([bun_binary_name, "run", "bun-api/index.ts"])
  else:
    print("Warning: Could not find Bun API binary - please start it manually.")
""",
        """  # Bun API runs as a sibling process; see entrypoint.sh.
""",
        "bun spawn",
    )

    # 2. No WireGuard config for this deployment; the addon is a plain proxy.
    text = replace_once(
        text,
        """  # Generate WireGuard config
  wan_ip_req = requests.get("https://api.ipify.org")
  if wan_ip_req.status_code != 200 or not wan_ip_req.text:
    wan_ip_req = requests.get("https://api.seeip.org")
  wan_ip = wan_ip_req.text
  with open("wg-keys.json", "r") as keys_file:
    wg_keys = json.loads(keys_file.read())
    config = f\"\"\"\\
# This file was automatically generated.
# To change keys, edit `wg-keys.json` instead.

[Interface]
PrivateKey = {wg_keys["client_key"]}
Address = 10.0.0.1/32
DNS = 10.0.0.53

[Peer]
PublicKey = {mitmproxy_rs.wireguard.pubkey(wg_keys["server_key"])}
AllowedIPs = 0.0.0.0/0
Endpoint = {wan_ip}:51820\"\"\"
    # Write config to file
    with open("wireguard.cfg", "w") as config_file:
      config_file.write(config)
""",
        """  # WireGuard mode is not used in the pod: main.py is replaced by
  # `mitmdump --mode regular` in entrypoint.sh.
""",
        "wireguard config",
    )

    # 3. The blocklist is baked into the image.
    text = replace_once(
        text,
        """  DNS_BLOCKLIST = requests.get("https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/wildcard/pro-onlydomains.txt").text""",
        """  DNS_BLOCKLIST = open("/etc/arachnidium/blocklist.txt").read()""",
        "blocklist fetch",
    )

    ADDON.write_text(text)
    print("patch: addon.py patched for in-pod proxy use")


if __name__ == "__main__":
    main()
