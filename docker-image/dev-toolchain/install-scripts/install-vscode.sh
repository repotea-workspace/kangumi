#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
INSTALL_DIR="/usr/local/bin"
VSCODE_CLI="code"

print_header "Installing VSCode CLI"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if check_installed "vscode"; then
  if [ -f "${INSTALL_DIR}/${VSCODE_CLI}" ]; then
    "${INSTALL_DIR}/${VSCODE_CLI}" --version 2>/dev/null || print_warning "Unable to get version"
    exit 0
  fi
fi

# Download VSCode CLI
print_info "Downloading VSCode CLI (latest stable)..."
DOWNLOAD_URL="https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64"
TMP_FILE="/tmp/vscode-cli.tar.gz"

if ! curl -fsSLk "${DOWNLOAD_URL}" -o "${TMP_FILE}"; then
  print_error "Failed to download VSCode CLI"
  exit 1
fi

# Extract VSCode CLI
echo ""
print_info "Extracting VSCode CLI..."
tar -xzf "${TMP_FILE}" -C "${INSTALL_DIR}"

# Clean up
rm -f "${TMP_FILE}"

# Mark as installed
mark_installed "vscode" "latest"

# Verify installation
echo ""
print_header "Installation completed!"
"${INSTALL_DIR}/${VSCODE_CLI}" --version
echo ""
print_success "VSCode CLI has been installed to: ${INSTALL_DIR}/${VSCODE_CLI}"
echo ""
echo "Usage:"
echo "  Start tunnel: code tunnel"
echo "  Get help: code --help"
echo ""
