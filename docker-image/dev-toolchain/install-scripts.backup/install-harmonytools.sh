#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
HARMONY_VERSION="${HARMONY_VERSION:-5.0.3.500}"
BASE_DIR="/opt/harmony"
INSTALL_DIR="${BASE_DIR}/current"
DOWNLOAD_URL="https://github.com/0xfe10/dynamic-actions/releases/download/v0.0.1-ohtools/commandline-tools-linux-x64-5.0.3.500.tar.gz"

# Environment variable block
ENV_BLOCK='# HarmonyOS Command-Line Tools
if [ -d "/opt/harmony/current" ]; then
  export HARMONYOS_HOME="/opt/harmony/current"
  export PATH="$HARMONYOS_HOME/bin:$PATH"
fi'

print_header "Installing HarmonyOS Command-Line Tools"
echo "Version: ${HARMONY_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo ""

# Check if already installed
if [ -d "${INSTALL_DIR}" ] && [ -d "${INSTALL_DIR}/bin" ]; then
  print_success "HarmonyOS tools are already installed at: ${INSTALL_DIR}"
  # Ensure env vars are present
  ensure_env_block "# HarmonyOS Command-Line Tools" "${ENV_BLOCK}"
  print_success "HarmonyOS environment variables ensured in ${ENV_SCRIPT}"
  exit 0
fi

# Create installation directory
mkdir -p "${BASE_DIR}"

# Download the tarball
TMP_FILE="/tmp/commandline-tools-linux-x64-${HARMONY_VERSION}.tar.gz"
print_info "Downloading HarmonyOS command-line tools..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract to temporary directory
echo ""
print_info "Extracting command-line tools..."
TMP_EXTRACT="/tmp/harmony_extract_$$"
mkdir -p "${TMP_EXTRACT}"
tar -xzf "${TMP_FILE}" -C "${TMP_EXTRACT}"

# Clean up tarball
rm -f "${TMP_FILE}"

# Find the extracted directory (usually commandline-tools-linux-x64-VERSION)
EXTRACTED_DIR=$(find "${TMP_EXTRACT}" -maxdepth 1 -type d ! -path "${TMP_EXTRACT}" | head -1)

if [ -z "${EXTRACTED_DIR}" ] || [ ! -d "${EXTRACTED_DIR}" ]; then
  print_error "Failed to find extracted directory"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Move to final location
print_info "Installing to ${INSTALL_DIR}..."
rm -rf "${INSTALL_DIR}"
mv "${EXTRACTED_DIR}" "${INSTALL_DIR}"

# Clean up temp directory
rm -rf "${TMP_EXTRACT}"

# Verify installation
if [ ! -d "${INSTALL_DIR}/bin" ]; then
  print_error "Installation verification failed: bin directory not found"
  exit 1
fi

# Add to PATH via env script
ensure_env_block "# HarmonyOS Command-Line Tools" "${ENV_BLOCK}"

echo ""
print_header "Installation completed!"
echo ""
print_success "HarmonyOS tools ${HARMONY_VERSION} installed to: ${INSTALL_DIR}"
echo ""
echo "To use HarmonyOS tools in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export HARMONYOS_HOME=\"${INSTALL_DIR}\""
echo "  export PATH=\"\${HARMONYOS_HOME}/bin:\$PATH\""
echo ""
