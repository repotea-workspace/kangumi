##
# MAIN STAGE - Minimal base image with Homebrew
##
FROM ubuntu:24.04 AS runner

ARG DOCKER_VERSION=27.5.1
ARG S6_OVERLAY_VERSION=3.2.1.0

SHELL ["/bin/bash", "-c"]

## Install minimal base dependencies (only Homebrew requirements + SSH/sudo)
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y \
    # Core utilities (required by Homebrew and container basics)
    curl ca-certificates wget \
    xz-utils zstd zip unzip tar gzip bzip2 \
    # SSH server
    openssh-server \
    # Build tools (required by Homebrew)
    build-essential procps file \
    # Git (too fundamental, keep in base)
    git \
    # Sudo (for multi-user access)
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

## Homebrew will be installed at runtime to /home/linuxbrew/.linuxbrew (PVC persistent)
## Using standard Linux Homebrew path for x86_64 compatibility
## Using root for simplified access (requires HOMEBREW_ALLOW_ROOT=1)

## Setup Homebrew environment for all users
## Homebrew will be installed by postStart to /home/linuxbrew/.linuxbrew
ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}" \
    HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew" \
    HOMEBREW_CELLAR="/home/linuxbrew/.linuxbrew/Cellar" \
    HOMEBREW_REPOSITORY="/home/linuxbrew/.linuxbrew" \
    HOMEBREW_ALLOW_ROOT=1 \
    HOMEBREW_NO_ENV_HINTS=1 \
    HOMEBREW_NO_AUTO_UPDATE=1 \
    HOMEBREW_NO_INSTALL_FROM_API=1

## Create directories
RUN mkdir -p /usr/local/lib/dev-tools/install-scripts \
    && mkdir -p /usr/local/lib/dev-tools/user-scripts \
    && mkdir -p /etc/profile.d \
    && mkdir -p /etc/sudoers.d

## Copy install scripts (including tools.yaml)
COPY install-scripts/ /usr/local/lib/dev-tools/install-scripts/
RUN chmod +x /usr/local/lib/dev-tools/install-scripts/*.sh

## Symlink install-brew-tools.sh to /usr/local/bin for easy access
RUN ln -s /usr/local/lib/dev-tools/install-scripts/install-brew-tools.sh /usr/local/bin/install-brew-tools.sh

## Copy s6 init scripts
COPY cont-init.d/ /etc/cont-init.d/
RUN chmod +x /etc/cont-init.d/*

## Configure bashrc for root user to source profile.d script
RUN echo '' >> /root/.bashrc && \
    echo '# Source dev-tools environment from profile.d' >> /root/.bashrc && \
    echo 'if [ -f /etc/profile.d/99-dev-tools-env.sh ]; then' >> /root/.bashrc && \
    echo '    source /etc/profile.d/99-dev-tools-env.sh' >> /root/.bashrc && \
    echo 'fi' >> /root/.bashrc

## Copy s6 service definitions
COPY services.d /etc/services.d

## Set DOCKER_HOST to connect to DinD sidecar
ENV DOCKER_HOST=tcp://localhost:2375

## Create container marker file for Homebrew
## Homebrew checks for /.dockerenv to allow running as root in containers
RUN touch /.dockerenv

## Create workspace directory
RUN mkdir -p /code
WORKDIR /code

## s6-overlay entrypoint
ENTRYPOINT ["/init"]
