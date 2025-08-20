FROM debian:bullseye

ARG NODE_LIVENESS_PROBE_VERSION='v0.6.1'

RUN set -xe && \
  apt update && \
  apt install curl unzip -y && \
  curl -L -o /bin/node-liveness-probe "https://github.com/darwinia-network/node-liveness-probe/releases/download/${NODE_LIVENESS_PROBE_VERSION}/node-liveness-probe_linux_amd64" && \
  chmod +x /bin/node-liveness-probe

CMD node-liveness-probe
