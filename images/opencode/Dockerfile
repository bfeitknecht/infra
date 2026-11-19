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

ARG OPENCODE_VERSION=1.19.5
RUN npm install -g "opencode-ai@${OPENCODE_VERSION}" && npm cache clean --force

# The plugin lives in the image (root-owned, read-only to the agent) and is
# loaded by file URL. Patch: a Kata container cannot mount a fresh /proc
# (masked paths), so the runtime binds the existing one
# (enableWeakerNestedSandbox). The build fails if the patch does not apply.
ARG SANDBOX_VERSION=0.6.0
WORKDIR /opt/opencode-sandbox
COPY patch.mjs ./
RUN npm init -y >/dev/null && \
    npm install --omit=dev "opencode-sandbox@${SANDBOX_VERSION}" && \
    node patch.mjs node_modules/opencode-sandbox/dist/index.js && \
    npm cache clean --force

WORKDIR /home/node
USER node
CMD ["opencode", "web", "--hostname", "0.0.0.0", "--port", "4096"]
