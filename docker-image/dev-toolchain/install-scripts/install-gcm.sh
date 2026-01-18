#!/usr/bin/env bash

set -euo pipefail

# Configuration
GCM_VERSION="${GCM_VERSION:-2.6.1}"
INSTALL_DIR="/usr/local/bin"

echo "=========================================="
echo "Installing Git Credential Manager"
echo "=========================================="
echo "Version: ${GCM_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -f "${INSTALL_DIR}/git-credential-manager" ]; then
  echo "Git Credential Manager is already installed at ${INSTALL_DIR}/git-credential-manager"
  "${INSTALL_DIR}/git-credential-manager" --version 2>/dev/null || true

  echo ""
  echo "Use --force to reinstall"
  exit 0
fi

# Download GCM
echo "Downloading Git Credential Manager ${GCM_VERSION}..."
DOWNLOAD_URL="https://github.com/git-ecosystem/git-credential-manager/releases/download/v${GCM_VERSION}/gcm-linux_amd64.${GCM_VERSION}.tar.gz"
TMP_FILE="/tmp/gcm-linux.tar.gz"

curl -Lk "${DOWNLOAD_URL}" -o "${TMP_FILE}"

# Extract GCM
echo ""
echo "Extracting Git Credential Manager..."
tar -xzf "${TMP_FILE}" -C "${INSTALL_DIR}"

# Clean up
rm -f "${TMP_FILE}"

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
"${INSTALL_DIR}/git-credential-manager" --version
echo ""
echo "Git Credential Manager has been installed to: ${INSTALL_DIR}"
echo ""
echo "To configure GCM as your Git credential helper:"
echo "  git config --global credential.helper manager"
echo ""
echo "For GitHub:"
echo "  git-credential-manager configure"
echo ""
