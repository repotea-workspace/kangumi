#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
GCM_VERSION="${GCM_VERSION:-2.6.1}"
INSTALL_DIR="/usr/local/bin"
GCM_BIN="git-credential-manager"

print_header "Installing Git Credential Manager"
echo "Version: ${GCM_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if check_installed "gcm" "${GCM_VERSION}"; then
  if [ -f "${INSTALL_DIR}/${GCM_BIN}" ]; then
    "${INSTALL_DIR}/${GCM_BIN}" --version 2>/dev/null || print_warning "Unable to get version"
    exit 0
  fi
fi

# Download GCM
print_info "Downloading Git Credential Manager ${GCM_VERSION}..."
DOWNLOAD_URL="https://github.com/git-ecosystem/git-credential-manager/releases/download/v${GCM_VERSION}/gcm-linux_amd64.${GCM_VERSION}.tar.gz"
TMP_FILE="/tmp/gcm-linux.tar.gz"

if ! curl -fsSLk "${DOWNLOAD_URL}" -o "${TMP_FILE}"; then
  print_error "Failed to download Git Credential Manager"
  exit 1
fi

# Extract GCM
echo ""
print_info "Extracting Git Credential Manager..."
tar -xzf "${TMP_FILE}" -C "${INSTALL_DIR}"

# Clean up
rm -f "${TMP_FILE}"

# Configure git to use GCM
print_info "Configuring git credential helper..."
git config --global credential.helper manager || print_warning "Failed to configure git credential helper"

# Add env variable
append_to_env ""
append_to_env "# Git Credential Manager"
append_to_env 'export GCM_CREDENTIAL_STORE=gpg'

# Mark as installed
mark_installed "gcm" "${GCM_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${INSTALL_DIR}/${GCM_BIN}" --version
echo ""
print_success "Git Credential Manager has been installed to: ${INSTALL_DIR}/${GCM_BIN}"
echo ""
echo "Git credential helper has been configured globally"
echo ""
echo "For GitHub authentication:"
echo "  git-credential-manager configure"
echo ""
