#!/usr/bin/env bash
# sshd is the only process. The infra sshmux ForceCommands into
# browser-session: one browsh + one Firefox, one session at a time (browsh
# hard-codes Marionette 2828 and refuses to start beside another headless
# Firefox).
set -euo pipefail

mkdir -p /run/sshd
exec /usr/sbin/sshd -D -e
