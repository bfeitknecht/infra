#!/usr/bin/env bash
# The pod's process tree:
#   1. bun-api   (arachnidium minifier, localhost:3000)
#   2. mitmdump  (arachnidium addon, regular proxy mode, 127.0.0.1:8080;
#      generates the mitm CA on first start)
#   3. sshd      (22; the infra sshmux ForceCommands into browser-session)
#   4. browsh --http-server-mode (4333, the public web front; launches the
#      shared Firefox through the proxy profile prepared below)
set -euo pipefail

export HOME=/config
export XDG_CONFIG_HOME=/config/.config
mkdir -p "$HOME" "$XDG_CONFIG_HOME/browsh"
install -m 644 /etc/browsh/config.toml "$XDG_CONFIG_HOME/browsh/config.toml"

# --- bun-api ---------------------------------------------------------------
cd /opt/arachnidium/bun-api
bun run index.ts &

# bun-api must answer before mitmdump starts minifying through it. GET /
# is a 404 on purpose (only /api/minify/* serve); any HTTP answer proves
# the port is up.
waited=0
until curl -s -o /dev/null --max-time 1 http://127.0.0.1:3000/ 2>/dev/null; do
  waited=$((waited + 1))
  [ "$waited" -gt 30 ] && { echo "bun-api did not come up" >&2; exit 1; }
  sleep 1
done

# --- mitmdump (regular proxy mode, no WireGuard, no device VPN; the pod's
# own Firefoxes are the only clients) ---------------------------------------
# The venv is synced at build time; run its mitmdump directly. `uv run` at
# runtime re-resolves and stalls the proxy start. The addon reads
# defaults.json relative to its working directory: stay in /opt/arachnidium.
cd /opt/arachnidium
./.venv/bin/mitmdump --mode regular@127.0.0.1:8080 -s /opt/arachnidium/addon.py --set http3=false &

# The CA appears once mitmdump is up; sessions import it later.
waited=0
until [ -f "$HOME/.mitmproxy/mitmproxy-ca-cert.pem" ]; do
  waited=$((waited + 1))
  [ "$waited" -gt 30 ] && { echo "no mitm CA" >&2; exit 1; }
  sleep 1
done

# --- the shared Firefox profile for the HTTP front --------------------------
# Browsh makes its own Firefox profile at XDG_CONFIG_HOME/browsh/firefox_profile
# (verified against browsh v1.8.3: the webext reports moz:profile there). Write
# the proxy prefs and the mitm CA into exactly that directory. Firefox itself
# recreates profiles.ini content inside its own profile dir; nothing shared.
profile_root="$XDG_CONFIG_HOME/browsh"
prepare-profile "$profile_root/firefox_profile" "$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

# Firefox runs as `user` and must own everything it writes: the profile
# (prepared above as root), the config dir, and HOME.
chown -R user:user /config

# --- sshd -------------------------------------------------------------------
mkdir -p /run/sshd
/usr/sbin/sshd -D -e &

# --- the public HTTP front ---------------------------------------------------
# Firefox refuses to run as root. browsh runs as `user` (uid 1000), the owner
# of /config and the shared profile.
exec su -s /bin/bash user -c 'cd /config && HOME=/config XDG_CONFIG_HOME=/config/.config exec browsh --http-server-mode'
