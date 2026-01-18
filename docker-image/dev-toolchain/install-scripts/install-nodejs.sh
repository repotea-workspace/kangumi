#!/usr/bin/env bash

set -euo pipefail

# Configuration
NVM_VERSION="${NVM_VERSION:-0.40.3}"
NODE_VERSION="${NODE_VERSION:-22.15.1}"
INSTALL_DIR="${HOME}/.nvm"

echo "=========================================="
echo "Installing Node.js via nvm"
echo "=========================================="
echo "NVM Version: ${NVM_VERSION}"
echo "Node Version: ${NODE_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -d "${INSTALL_DIR}" ] && [ -s "${INSTALL_DIR}/nvm.sh" ]; then
  echo "nvm is already installed at ${INSTALL_DIR}"
  source "${INSTALL_DIR}/nvm.sh"

  if nvm list | grep -q "${NODE_VERSION}"; then
    echo "Node.js ${NODE_VERSION} is already installed"
    nvm use "${NODE_VERSION}"
    node --version
    npm --version
    exit 0
  fi
fi

# Install nvm
echo "Installing nvm ${NVM_VERSION}..."
curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh" | bash

# Load nvm
export NVM_DIR="${INSTALL_DIR}"
[ -s "${NVM_DIR}/nvm.sh" ] && \. "${NVM_DIR}/nvm.sh"
[ -s "${NVM_DIR}/bash_completion" ] && \. "${NVM_DIR}/bash_completion"

# Install Node.js
echo ""
echo "Installing Node.js ${NODE_VERSION}..."
nvm install "${NODE_VERSION}"
nvm use "${NODE_VERSION}"
nvm alias default "${NODE_VERSION}"

# Configure npm
echo ""
echo "Configuring npm..."
npm config set registry https://registry.npmjs.org/

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
echo "Node version: $(node --version)"
echo "npm version: $(npm --version)"
echo ""
echo "nvm has been installed to: ${NVM_DIR}"
echo ""
echo "To use nvm in your shell, add to your profile:"
echo "  export NVM_DIR=\"${NVM_DIR}\""
echo "  [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\""
echo ""
