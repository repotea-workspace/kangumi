#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
HARMONY_VERSION="${HARMONY_VERSION:-5.0.3.500}"
BASE_DIR="/opt/harmony"
DOWNLOAD_URL="https://github.com/0xfe10/dynamic-actions/releases/download/v0.0.1-ohtools/commandline-tools-linux-x64-5.0.3.500.tar.gz"

print_header "Installing HarmonyOS Command-Line Tools"
echo "Version: ${HARMONY_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo ""

# Check if already installed with same version
if check_installed "harmonytools" "${HARMONY_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -d "${CURRENT_DIR}/bin" ]; then
    print_success "HarmonyOS tools are ready at: ${CURRENT_DIR}"
    exit 0
  fi
fi

# Setup version directory structure
# Extract major.minor.patch from version (e.g., 5.0.3.500 -> 5.0.3 or v5.0.3)
VERSION_SHORT=$(echo "${HARMONY_VERSION}" | cut -d. -f1-3)
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "v${VERSION_SHORT}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

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

# The tarball contains a "command-line-tools" directory
# We need to move its contents to the version directory
if [ -d "${TMP_EXTRACT}/command-line-tools" ]; then
  mv "${TMP_EXTRACT}/command-line-tools"/* "${VERSION_DIR}/"
  rm -rf "${TMP_EXTRACT}"
else
  print_error "Expected 'command-line-tools' directory not found in archive"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Clean up download
rm -f "${TMP_FILE}"

# Verify installation
if [ ! -d "${VERSION_DIR}/bin" ]; then
  print_error "Installation verification failed: bin directory not found"
  exit 1
fi

# Add to PATH via env script
append_to_env ""
append_to_env "# HarmonyOS Command-Line Tools"
append_to_env 'if [ -d "/opt/harmony/current" ]; then'
append_to_env '  export HARMONYOS_HOME="/opt/harmony/current"'
append_to_env '  export PATH="$HARMONYOS_HOME/bin:$PATH"'
append_to_env 'fi'

# Mark as installed
mark_installed "harmonytools" "${HARMONY_VERSION}"

# Display installation summary
echo ""
print_header "Installation completed!"
echo ""
print_success "HarmonyOS tools ${HARMONY_VERSION} installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "Available tools in ${CURRENT_LINK}/bin/:"
ls -1 "${CURRENT_LINK}/bin/" | sed 's/^/  - /'
echo ""
echo "Available components:"
ls -1d "${CURRENT_LINK}"/*/ 2>/dev/null | xargs -n1 basename | sed 's/^/  - /'
echo ""
echo "To use HarmonyOS tools in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export HARMONYOS_HOME=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${HARMONYOS_HOME}/bin:\$PATH\""
echo ""
