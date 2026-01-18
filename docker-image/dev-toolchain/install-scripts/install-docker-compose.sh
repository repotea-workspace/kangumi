#!/usr/bin/env bash

set -euo pipefail

# Configuration
DOCKER_COMPOSE_VERSION="${DOCKER_COMPOSE_VERSION:-5.0.1}"
INSTALL_DIR="/usr/local/bin"

echo "=========================================="
echo "Installing Docker Compose"
echo "=========================================="
echo "Version: ${DOCKER_COMPOSE_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -f "${INSTALL_DIR}/docker-compose" ]; then
  CURRENT_VERSION=$("${INSTALL_DIR}/docker-compose" version --short 2>/dev/null || echo "unknown")
  echo "Docker Compose is already installed: ${CURRENT_VERSION}"

  if [ "${CURRENT_VERSION}" = "v${DOCKER_COMPOSE_VERSION}" ]; then
    echo "Version matches, skipping installation"
    exit 0
  fi

  echo "Upgrading to version ${DOCKER_COMPOSE_VERSION}..."
fi

# Download Docker Compose
echo "Downloading Docker Compose ${DOCKER_COMPOSE_VERSION}..."
DOWNLOAD_URL="https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64"

curl -SL "${DOWNLOAD_URL}" -o "${INSTALL_DIR}/docker-compose"

# Make executable
chmod +x "${INSTALL_DIR}/docker-compose"

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
"${INSTALL_DIR}/docker-compose" version
echo ""
echo "Docker Compose has been installed to: ${INSTALL_DIR}/docker-compose"
echo ""
