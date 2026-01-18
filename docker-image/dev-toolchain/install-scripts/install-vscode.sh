#!/usr/bin/env bash

set -euo pipefail

# Configuration
INSTALL_DIR="/usr/local/bin"

echo "=========================================="
echo "Installing VSCode CLI"
echo "=========================================="
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -f "${INSTALL_DIR}/code" ]; then
  echo "VSCode CLI is already installed at ${INSTALL_DIR}/code"
  "${INSTALL_DIR}/code" --version 2>/dev/null || true

  echo ""
  echo "Use --force to reinstall"
  exit 0
fi

# Download VSCode CLI
echo "Downloading VSCode CLI (latest stable)..."
DOWNLOAD_URL="https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64"
TMP_FILE="/tmp/vscode-cli.tar.gz"

curl -Lk "${DOWNLOAD_URL}" -o "${TMP_FILE}"

# Extract VSCode CLI
echo ""
echo "Extracting VSCode CLI..."
tar -xzf "${TMP_FILE}" -C "${INSTALL_DIR}"

# Clean up
rm -f "${TMP_FILE}"

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
"${INSTALL_DIR}/code" --version
echo ""
echo "VSCode CLI has been installed to: ${INSTALL_DIR}/code"
echo ""
echo "Usage:"
echo "  Start tunnel: code tunnel"
echo "  Get help: code --help"
echo ""
