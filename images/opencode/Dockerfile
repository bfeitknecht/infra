# opencode web for the isolated agent VM (infra applications/opencode, Kata).
# Every bash command the agent runs goes through the opencode-sandbox plugin:
# bubblewrap with a read and write allowlist, plus a network proxy with a
# domain allowlist (config: OPENCODE_SANDBOX_CONFIG in the Deployment).
# amd64 only: the pod runs on rzbl.
FROM docker.io/library/node:22-bookworm

# bubblewrap, socat (the sandbox network bridge) and ripgrep (the sandbox
# scans for files it must protect) for @anthropic-ai/sandbox-runtime.
RUN apt-get update && \
    apt-get install -y --no-install-recommends bubblewrap socat ripgrep && \
    rm -rf /var/lib/apt/lists/*

# v2 ships as @opencode/cli (opencode-ai stays on the 1.x line).
ARG OPENCODE_VERSION=2.4.0
RUN npm install -g "@opencode/cli@${OPENCODE_VERSION}" && npm cache clean --force

# Claude Code: the executable behind opencode's Claude Agent provider (it
# looks up `claude` on PATH) and a direct CLI over kubectl exec. Subscription
# login (/login) lands in ~/.claude on the PVC. Root-owned, so the agent
# cannot update or replace it; the nonessential-traffic switch also stops the
# auto-updater and telemetry. Managed settings: Claude Code's own bash
# sandbox with the same deny-read list and domain allowlist as the plugin.
ARG CLAUDE_CODE_VERSION=2.1.325
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && npm cache clean --force
COPY claude-managed-settings.json /etc/claude-code/managed-settings.json
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

# The plugin lives in the image (root-owned, read-only to the agent) and is
# loaded by file URL. v2 loads plugin directories and resolves the package
# entry (dist/v2.js); a single-file path is skipped. Patch: a Kata container
# cannot mount a fresh /proc (masked paths), so the runtime binds the existing
# one (enableWeakerNestedSandbox). The build fails if the patch does not apply.
# --legacy-peer-deps: the plugin peers (@opencode/plugin, @opencode-ai/plugin)
# are types only; the v2 entry imports only @anthropic-ai/sandbox-runtime.
ARG SANDBOX_VERSION=0.7.0
WORKDIR /opt/opencode-sandbox
COPY patch.mjs ./
RUN npm init -y >/dev/null && \
    npm install --omit=dev --legacy-peer-deps "opencode-sandbox@${SANDBOX_VERSION}" && \
    node patch.mjs node_modules/opencode-sandbox/dist/v2.js && \
    npm cache clean --force

WORKDIR /home/node
USER node
# serve is the v2 server command (v1 `web` is gone); it serves the web UI.
CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "4096"]
