#!/usr/bin/env bash
# Prepare a Firefox profile directory that talks to the in-pod Arachnidium
# mitmproxy: proxy prefs (user.js) and the mitm CA in the NSS store.
# Usage: prepare-profile <profile-dir> <ca-pem>
set -euo pipefail

dir="$1"
ca="$2"

mkdir -p "$dir"
user_js="$dir/user.js"
cat > "$user_js" <<'JS'
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "127.0.0.1");
user_pref("network.proxy.http_port", 8080);
user_pref("network.proxy.ssl", "127.0.0.1");
user_pref("network.proxy.ssl_port", 8080);
user_pref("network.proxy.share_proxy_settings", true);
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
JS

# NSS store: create if absent, then import the mitm CA. Firefox keeps a
# cert9.db per profile; `certutil -N` is idempotent-safe when it already
# exists only with --empty-password on a fresh db, so guard on the file.
if [ ! -f "$dir/cert9.db" ]; then
  certutil -N -d "sql:$dir" --empty-password
fi
certutil -A -d "sql:$dir" -n "arachnidium-mitm" -t "C,," -i "$ca"
