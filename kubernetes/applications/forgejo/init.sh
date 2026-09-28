#!/bin/sh
set -e

mkdir -p /data/gitea/conf /data/git/.ssh

# Seed app.ini on first boot only; afterwards Forgejo owns the file on the
# PVC (UI edits persist). Re-seeding requires deleting
# /data/gitea/conf/app.ini from the PVC.
if [ ! -f /data/gitea/conf/app.ini ]; then
  cp /seed/app.ini /data/gitea/conf/app.ini
  {
    echo ''
    echo '[security]'
    echo 'INSTALL_LOCK = true'
    echo "SECRET_KEY = $(cat /seed-secrets/secret-key)"
    echo "INTERNAL_TOKEN = $(cat /seed-secrets/internal-token)"
  } >> /data/gitea/conf/app.ini
  # Forgejo runs as git (uid/gid 1000) inside the image; the seed and the
  # whole tree must be owned by it.
  chown -R 1000:1000 /data
fi

# Run DB migrations first — the CLI user commands do not migrate, and a
# fresh database has no tables until this runs. Idempotent (no-op when
# up to date); also the right hook after a deliberate image bump.
su-exec git:git forgejo migrate --config /data/gitea/conf/app.ini

# Bootstrap the admin user (idempotent). Runs as git via su-exec so the
# SQLite DB it creates is owned by the same uid as the server.
if ! su-exec git:git forgejo admin user list --config /data/gitea/conf/app.ini 2>/dev/null | grep -qw "$ADMIN_USER"; then
  su-exec git:git forgejo admin user create --admin \
    --config /data/gitea/conf/app.ini \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASSWORD" \
    --email "$ADMIN_EMAIL" \
    --must-change-password=false
fi
