# browsh TUI over SSH. One front: sshd on 22 for the infra sshmux
# (ForceCommand browser-session; one browsh + one Firefox, one session at a
# time). Only linux/amd64: the browsh image bundles x64 Firefox. The infra
# Deployment pins the pod to rzbl.
FROM browsh/browsh@sha256:6f64eca9946b16f83a8f560093c4bde84205ea507fd55ecba50d5d728533b9b6

USER root

# procps (pkill) and util-linux (flock) for browser-session.
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server procps util-linux && \
    rm -rf /var/lib/apt/lists/*

COPY config.toml /etc/browsh/config.toml
COPY browser-session /usr/local/bin/browser-session
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /usr/local/bin/browser-session /entrypoint.sh && \
    useradd --create-home --shell /bin/bash browser && \
    mkdir -p /run/sshd

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
