#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
DOCKER_COMPOSE_VERSION="${DOCKER_COMPOSE_VERSION:-5.0.1}"
INSTALL_DIR="/usr/local/bin"

# Note: docker-compose is installed directly to /usr/local/bin which is already in PATH
# No need to add environment variables for PATH modification

print_header "Installing Docker Compose"
echo "Version: ${DOCKER_COMPOSE_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed with same version
if check_installed "docker-compose" "${DOCKER_COMPOSE_VERSION}"; then
  if [ -f "${INSTALL_DIR}/docker-compose" ]; then
    print_success "Docker Compose ${DOCKER_COMPOSE_VERSION} is already installed"
    "${INSTALL_DIR}/docker-compose" version || print_warning "Unable to get version"
    exit 0
  fi
fi

# Check if docker-compose exists (but different version)
if [ -f "${INSTALL_DIR}/docker-compose" ]; then
  CURRENT_VERSION=$("${INSTALL_DIR}/docker-compose" version --short 2>/dev/null || echo "unknown")
  print_info "Docker Compose is already installed: ${CURRENT_VERSION}"
  print_info "Upgrading to version ${DOCKER_COMPOSE_VERSION}..."
fi

# Download Docker Compose
print_info "Downloading Docker Compose ${DOCKER_COMPOSE_VERSION}..."
DOWNLOAD_URL="https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64"

if ! curl -fSL "${DOWNLOAD_URL}" -o "${INSTALL_DIR}/docker-compose"; then
  print_error "Failed to download Docker Compose"
  exit 1
fi

# Make executable
chmod +x "${INSTALL_DIR}/docker-compose"

# Mark as installed
mark_installed "docker-compose" "${DOCKER_COMPOSE_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${INSTALL_DIR}/docker-compose" version
echo ""
print_success "Docker Compose ${DOCKER_COMPOSE_VERSION} has been installed to: ${INSTALL_DIR}/docker-compose"
echo ""
