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

## Create brew group and linuxbrew user for Homebrew installation
RUN groupadd -g 999 brew \
    && useradd -m -u 999 -g brew -s /bin/bash linuxbrew \
    && echo 'linuxbrew ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

## Install Homebrew as linuxbrew user
COPY install-scripts/install-homebrew.sh /tmp/
RUN chown linuxbrew:brew /tmp/install-homebrew.sh \
    && su - linuxbrew -c "bash /tmp/install-homebrew.sh" \
    && rm /tmp/install-homebrew.sh

## Configure Homebrew for group sharing
## - linuxbrew user owns the installation
## - brew group members can read and execute
## - brew group members can write to var/homebrew (for locks/cache)
RUN chown -R linuxbrew:brew /home/linuxbrew/.linuxbrew \
    && chmod -R g+rX /home/linuxbrew/.linuxbrew \
    && chmod -R g+w /home/linuxbrew/.linuxbrew/var/homebrew 2>/dev/null || true

## Install yq (required for tools.yaml parsing)
RUN su - linuxbrew -c "eval \"\$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\" && brew install yq"

## Setup Homebrew environment for all users
ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}" \
    HOMEBREW_NO_ENV_HINTS=1 \
    HOMEBREW_NO_AUTO_UPDATE=1 \
    HOMEBREW_NO_INSTALL_FROM_API=1

## Create directories
RUN mkdir -p /usr/local/lib/dev-tools/install-scripts \
    && mkdir -p /etc/profile.d \
    && mkdir -p /etc/sudoers.d

## Copy install scripts (including tools.yaml)
COPY install-scripts/ /usr/local/lib/dev-tools/install-scripts/
RUN chmod +x /usr/local/lib/dev-tools/install-scripts/*.sh

## Copy system scripts to /usr/local/bin
COPY scripts/create-user.sh /usr/local/bin/create-user
RUN chmod +x /usr/local/bin/create-user

## Symlink install-brew-tools.sh to /usr/local/bin for easy access
RUN ln -s /usr/local/lib/dev-tools/install-scripts/install-brew-tools.sh /usr/local/bin/install-brew-tools.sh

## Copy s6 init scripts
COPY cont-init.d/ /etc/cont-init.d/
RUN chmod +x /etc/cont-init.d/*

## Configure bashrc for root user
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
