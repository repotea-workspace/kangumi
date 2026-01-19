##
# MAIN STAGE - Minimal base image with Homebrew
##
FROM ubuntu:24.04 AS runner

ARG DOCKER_VERSION=27.5.1
ARG S6_OVERLAY_VERSION=3.2.1.0

SHELL ["/bin/bash", "-c"]

## Install minimal base dependencies
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
    # Core utilities
    curl ca-certificates wget \
    xz-utils zstd zip unzip tar gzip bzip2 \
    # SSH server
    openssh-server \
    # Essential editors and terminal tools
    vim nano git \
    # Build tools (required by Homebrew)
    build-essential procps file \
    # Network tools (essential for debugging)
    iputils-ping iproute2 dnsutils \
    # Process tools
    procps \
    # Sudo (for linuxbrew user)
    sudo \
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

## Create linuxbrew user for Homebrew installation
RUN useradd -m -s /bin/bash linuxbrew \
    && echo 'linuxbrew ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

## Install Homebrew as linuxbrew user
COPY install-scripts/install-homebrew.sh /tmp/
RUN chown linuxbrew:linuxbrew /tmp/install-homebrew.sh \
    && su - linuxbrew -c "bash /tmp/install-homebrew.sh" \
    && rm /tmp/install-homebrew.sh

## Configure Homebrew environment and allow root access
RUN chgrp -R root /home/linuxbrew/.linuxbrew \
    && chmod -R g+rwX /home/linuxbrew/.linuxbrew
ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}" \
    HOMEBREW_NO_ENV_HINTS=1 \
    HOMEBREW_NO_AUTO_UPDATE=1 \
    HOMEBREW_NO_INSTALL_FROM_API=1 \
    HOME=/root \
    USER=root

## Create install scripts directory for custom tools
RUN mkdir -p /usr/local/lib/dev-tools/install-scripts

## Copy remaining install scripts (custom tools)
COPY install-scripts/ /usr/local/lib/dev-tools/install-scripts/
RUN chmod +x /usr/local/lib/dev-tools/install-scripts/*.sh

## Copy s6 init scripts
COPY cont-init.d/ /etc/cont-init.d/
RUN chmod +x /etc/cont-init.d/*

## Create env script directory and configure bashrc
RUN mkdir -p /etc/profile.d
COPY bashrc.d/dev-tools-env.sh /tmp/bashrc-snippet.sh
RUN cat /tmp/bashrc-snippet.sh >> /root/.bashrc && rm /tmp/bashrc-snippet.sh

## Copy s6 service definitions
COPY services.d /etc/services.d

## Set DOCKER_HOST to connect to DinD sidecar
ENV DOCKER_HOST=tcp://localhost:2375

## Create workspace directory
RUN mkdir -p /code
WORKDIR /code

## s6-overlay entrypoint
ENTRYPOINT ["/init"]
