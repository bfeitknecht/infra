# Browsh + Arachnidium in one pod. One front: sshd on 22 for the mux
# (ForceCommand browser-session; one browsh + one Firefox, one session at a
# time).
# All Firefox traffic goes through the in-pod Arachnidium mitmproxy.
# Only linux/amd64: the browsh image bundles x64 Firefox. The infra
# Deployment pins the pod to rzbl.
FROM browsh/browsh@sha256:6f64eca9946b16f83a8f560093c4bde84205ea507fd55ecba50d5d728533b9b6

USER root

# openssh-server for the mux, libnss3-tools for certutil (mitm CA into each
# Firefox profile), tk because arachnidium imports tkinter unconditionally,
# uv and bun for the python and the minifier runtimes.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openssh-server procps util-linux libnss3-tools python3 python3-tk python3-venv ca-certificates curl git unzip && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="/usr/local/bin" sh && \
    curl -fsSL https://bun.sh/install | env BUN_INSTALL="/usr/local" bash

# Arachnidium at a pinned commit. The author does not maintain it long term;
# we vendor patches and expect ownership.
ARG ARACHNIDIUM_SHA=e9bf2fefe55ad6bf4e967ba074a009021dd3007e
RUN git clone --quiet https://github.com/p2r3/Arachnidium /opt/arachnidium && \
    git -C /opt/arachnidium checkout --quiet $ARACHNIDIUM_SHA

COPY patches/ /opt/patches/
COPY defaults.json /opt/arachnidium/defaults.json
# The patcher rewrites addon.py for in-pod proxy use and strips the parts
# that belong to the desktop WireGuard product. entrypoint.sh owns the
# process tree: bun-api, mitmdump, sshd, browsh.
RUN python3 /opt/patches/patch.py && \
    cd /opt/arachnidium && uv sync --frozen --no-dev && \
    cd /opt/arachnidium/bun-api && bun install --production && \
    mkdir -p /etc/arachnidium && \
    curl -fsSL https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/wildcard/pro-onlydomains.txt \
      -o /etc/arachnidium/blocklist.txt

COPY config.toml /etc/browsh/config.toml
COPY prepare-profile.sh /usr/local/bin/prepare-profile
COPY browser-session /usr/local/bin/browser-session
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /usr/local/bin/prepare-profile /usr/local/bin/browser-session /entrypoint.sh && \
    useradd --create-home --shell /bin/bash browser && \
    mkdir -p /config /run/sshd && chown -R user:user /config

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
