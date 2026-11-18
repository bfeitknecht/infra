# The router of SSH usernames to SSH TUI services. One WAN port (2222) in,
# one backend per username out. Backends are reached over the cluster
# network; cluster state (users, targets, keys) lives in infra ConfigMaps
# and Secrets, not in this image.
FROM debian:trixie-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server openssh-client && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /run/sshd

COPY entrypoint.sh to-apex /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/to-apex

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
