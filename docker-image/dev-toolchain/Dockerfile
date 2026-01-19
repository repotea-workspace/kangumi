##
# MAIN STAGE - Minimal base image
##
FROM ubuntu:24.04 AS runner

ARG DOCKER_VERSION=27.5.1
ARG S6_OVERLAY_VERSION=3.2.1.0

SHELL ["/bin/bash", "-c"]

## Install minimal base dependencies
## Skip unminimize to save ~70MB and reduce size by ~1.2GB
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
    # Core utilities
    curl ca-certificates wget \
    xz-utils zstd zip unzip tar gzip bzip2 \
    # SSH server
    openssh-server \
    # Essential editors and terminal tools
    vim nano git \
    # Basic build tools (commonly needed)
    build-essential \
    # Network tools (essential for debugging)
    iputils-ping iproute2 dnsutils \
    # Process tools
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

## s6-overlay (process supervisor)
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp/
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp/

RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz \
    && tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz \
    && rm -rf /tmp/s6-overlay-*.tar.xz

## Docker CLI only (no daemon - will connect to DinD sidecar)
RUN curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz" -o /tmp/docker.tgz \
    && tar -xzf /tmp/docker.tgz -C /tmp \
    && install -m 755 /tmp/docker/docker /usr/local/bin/docker \
    && rm -rf /tmp/docker.tgz /tmp/docker

## SSH config
RUN mkdir -p /run/sshd \
    && echo "PasswordAuthentication no" >> /etc/ssh/sshd_config \
    && echo "PermitRootLogin prohibit-password" >> /etc/ssh/sshd_config \
    && echo "Include /etc/ssh/sshd_config.d/*.conf" >> /etc/ssh/sshd_config

## Create install scripts directory
RUN mkdir -p /usr/local/lib/dev-tools/install-scripts

## Copy install scripts
COPY install-scripts/ /usr/local/lib/dev-tools/install-scripts/
RUN chmod +x /usr/local/lib/dev-tools/install-scripts/*.sh

## Create s6 init script to run init-env.sh
RUN mkdir -p /etc/cont-init.d && \
    echo '#!/usr/bin/with-contenv bash' > /etc/cont-init.d/01-init-env && \
    echo '/usr/local/lib/dev-tools/install-scripts/init-env.sh' >> /etc/cont-init.d/01-init-env && \
    chmod +x /etc/cont-init.d/01-init-env

## Create env script directory
RUN mkdir -p /etc/profile.d

## Copy s6 service definitions
COPY services.d /etc/services.d

## Set DOCKER_HOST to connect to DinD sidecar
ENV DOCKER_HOST=tcp://localhost:2375

## Create workspace directory
RUN mkdir -p /code
WORKDIR /code

## s6-overlay entrypoint
ENTRYPOINT ["/init"]
