FROM ubuntu:24.04

ARG DOCKER_COMPOSE_VERSION=2.37.3
ARG S6_OVERLAY_VERSION=3.2.1.0

SHELL ["/bin/bash", "-c"]


## unminimize
RUN yes | unminimize

## install dependencies
RUN \
  apt-get update -y \
  && apt-get install --no-install-recommends -y \
    curl ca-certificates xz-utils zstd zip unzip \
    openssh-server \
    python3-pip python3-dev \
    wget vim nano git htop \
    sudo \
    mtr iperf3 nload ncdu gnupg jq \
    iproute2

## link python
RUN \
  ln -s /usr/bin/python3 /usr/bin/python


## s6-overlay

# RUN curl -fSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" -o /tmp/s6-overlay-noarch.tar.xz || \
#     (echo "Failed to download s6-overlay tarball!" && exit 1)
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN [ -f /tmp/s6-overlay-noarch.tar.xz ] || (echo "Failed to download s6-overlay tarball!" && exit 1)
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz

# RUN curl -fSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz" -o /tmp/s6-overlay-x86_64.tar.xz || \
#     (echo "Failed to download s6-overlay tarball!" && exit 1)
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN [ -f /tmp/s6-overlay-x86_64.tar.xz ] || (echo "Failed to download s6-overlay tarball!" && exit 1)
RUN tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz

COPY services.d /etc/services.d


## docker
RUN curl -fsSL https://get.docker.com | sh && \
  curl -SL https://github.com/docker/compose/releases/download/v$DOCKER_COMPOSE_VERSION/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && \
  chmod +x /usr/local/bin/docker-compose


## ssh config
RUN \
  mkdir -p /run/sshd && \
  echo "PasswordAuthentication no" >> /etc/ssh/sshd_config && \
  echo "PermitRootLogin prohibit-password" >> /etc/ssh/sshd_config

## init-scripts
COPY init-scripts /init-scripts

RUN \
  bash -f /init-scripts/init-ssh.sh \
  && rm -rf /init-scripts

## workdir
RUN mkdir /data
WORKDIR /data

## entrypoint
ENTRYPOINT ["/init"]
