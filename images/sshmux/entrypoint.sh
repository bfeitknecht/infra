#!/usr/bin/env bash
# Read the mux table (/etc/ssh/mux/users: "username:password-login") and
# build the system users: key-only for password-login "no" (locked
# password), empty password for "yes" (the public apex path: press Enter).
# authorized_keys from /etc/ssh/mux/authorized_keys lands in every user's
# ~/.ssh so the owner's key always works. Then run sshd with the config
# mounted at /etc/ssh/mux/sshd_config (infra owns it, with its Match User
# ForceCommand blocks).
set -euo pipefail

[ -f /etc/ssh/mux/users ] || { echo "mux: no /etc/ssh/mux/users" >&2; exit 1; }

while IFS=: read -r name password_login; do
  case "$name" in ""|\#*) continue ;; esac
  id "$name" >/dev/null 2>&1 || useradd --create-home --shell /usr/sbin/nologin "$name"
  if [ "$password_login" = "yes" ]; then
    # Empty password: sshd only grants it when the shadow field is empty.
    usermod -p '' "$name"
  else
    usermod -p '*' "$name"
  fi
  home=$(getent passwd "$name" | cut -d: -f6)
  install -d -m 700 -o "$name" -g "$name" "$home/.ssh"
  if [ -f /etc/ssh/mux/authorized_keys ]; then
    install -m 600 -o "$name" -g "$name" /etc/ssh/mux/authorized_keys "$home/.ssh/authorized_keys"
  fi
done < /etc/ssh/mux/users

exec /usr/sbin/sshd -D -e -f /etc/ssh/mux/sshd_config
