##
# MAIN STAGE
##
FROM alpine:3

ARG HELM_DIFF_VERSION=v3.1.3

# Install dependencies
RUN apk add --no-cache \
    ca-certificates \
    curl \
    wget \
    bash \
    git \
    make \
    colordiff \
    moreutils

# Copy install script
COPY install-k8s-tools.sh /tmp/install-k8s-tools.sh
RUN chmod +x /tmp/install-k8s-tools.sh

# Install all k8s tools using the script
RUN /tmp/install-k8s-tools.sh && rm -f /tmp/install-k8s-tools.sh

# Install helm-diff plugin (already done in script, but keep for compatibility)
# RUN helm plugin install https://github.com/databus23/helm-diff \
#       --version=${HELM_DIFF_VERSION} \
#       --verify=false

WORKDIR /workspace
