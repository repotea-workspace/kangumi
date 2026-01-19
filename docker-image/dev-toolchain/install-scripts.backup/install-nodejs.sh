#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
NVM_VERSION="${NVM_VERSION:-0.40.3}"
NODE_VERSION="${NODE_VERSION:-22.15.1}"
INSTALL_DIR="${HOME}/.nvm"

# Environment variable block
ENV_BLOCK='# Node.js (nvm)
export NVM_DIR="/root/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"'

print_header "Installing Node.js via nvm"
echo "NVM Version: ${NVM_VERSION}"
echo "Node Version: ${NODE_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed with same version
if check_installed "nodejs" "${NODE_VERSION}"; then
  if [ -d "${INSTALL_DIR}" ] && [ -s "${INSTALL_DIR}/nvm.sh" ]; then
    source "${INSTALL_DIR}/nvm.sh"
    if nvm list | grep -q "${NODE_VERSION}"; then
      # Ensure env vars are present even if already installed
      ensure_env_block "# Node.js (nvm)" "${ENV_BLOCK}"
      print_success "Node.js environment variables ensured in ${ENV_SCRIPT}"
      nvm use "${NODE_VERSION}"
      echo "Node version: $(node --version)"
      echo "npm version: $(npm --version)"
      exit 0
    fi
  fi
fi

# Check if nvm is already installed (but maybe different node version)
if [ -d "${INSTALL_DIR}" ] && [ -s "${INSTALL_DIR}/nvm.sh" ]; then
  print_info "nvm is already installed at ${INSTALL_DIR}"
  source "${INSTALL_DIR}/nvm.sh"

  if nvm list | grep -q "${NODE_VERSION}"; then
    print_success "Node.js ${NODE_VERSION} is already installed"
    nvm use "${NODE_VERSION}"
    node --version
    npm --version
    mark_installed "nodejs" "${NODE_VERSION}"
    exit 0
  fi
fi

# Install nvm
print_info "Installing nvm ${NVM_VERSION}..."
if ! curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh" | bash; then
  print_error "Failed to install nvm"
  exit 1
fi

# Load nvm
export NVM_DIR="${INSTALL_DIR}"
[ -s "${NVM_DIR}/nvm.sh" ] && \. "${NVM_DIR}/nvm.sh"
[ -s "${NVM_DIR}/bash_completion" ] && \. "${NVM_DIR}/bash_completion"

# Install Node.js
echo ""
print_info "Installing Node.js ${NODE_VERSION}..."
nvm install "${NODE_VERSION}"
nvm use "${NODE_VERSION}"
nvm alias default "${NODE_VERSION}"

# Configure npm
echo ""
print_info "Configuring npm..."
npm config set registry https://registry.npmjs.org/

# Add to PATH via env script
ensure_env_block "# Node.js (nvm)" "${ENV_BLOCK}"

# Mark as installed
mark_installed "nodejs" "${NODE_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
echo "Node version: $(node --version)"
echo "npm version: $(npm --version)"
echo ""
print_success "nvm has been installed to: ${NVM_DIR}"
print_success "Node.js ${NODE_VERSION} is set as default"
echo ""
echo "To use nvm in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export NVM_DIR=\"${NVM_DIR}\""
echo "  [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\""
echo ""
