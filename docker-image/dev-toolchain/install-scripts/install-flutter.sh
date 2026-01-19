#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
FLUTTER_VERSION="${FLUTTER_VERSION:-3.38.7}"
BASE_DIR="/opt/flutter"
FLUTTER_CHANNEL="${FLUTTER_CHANNEL:-stable}"

print_header "Installing Flutter SDK"
echo "Version: ${FLUTTER_VERSION}"
echo "Channel: ${FLUTTER_CHANNEL}"
echo "Install Directory: ${BASE_DIR}"
echo ""

# Check if already installed with same version
if check_installed "flutter" "${FLUTTER_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/bin/flutter" ]; then
    "${CURRENT_DIR}/bin/flutter" --version

    # Optional: Update Flutter
    echo ""
    print_info "Updating Flutter..."
    "${CURRENT_DIR}/bin/flutter" upgrade || print_warning "Flutter upgrade failed, continuing..."
  fi
  exit 0
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${FLUTTER_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Download Flutter
print_info "Downloading Flutter ${FLUTTER_VERSION}..."
DOWNLOAD_URL="https://storage.googleapis.com/flutter_infra_release/releases/${FLUTTER_CHANNEL}/linux/flutter_linux_${FLUTTER_VERSION}-${FLUTTER_CHANNEL}.tar.xz"
TMP_FILE="/tmp/flutter_${FLUTTER_VERSION}.tar.xz"

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download Flutter"
  exit 1
fi

# Extract Flutter
echo ""
print_info "Extracting Flutter..."
# Flutter tarball contains a top-level 'flutter' directory
# We need to extract it and move contents to our version directory
TMP_EXTRACT="/tmp/flutter_extract_$$"
mkdir -p "${TMP_EXTRACT}"
tar -xf "${TMP_FILE}" -C "${TMP_EXTRACT}"

# Move extracted flutter directory contents to version directory
if [ -d "${TMP_EXTRACT}/flutter" ]; then
  mv "${TMP_EXTRACT}/flutter"/* "${VERSION_DIR}/"
  rm -rf "${TMP_EXTRACT}"
else
  print_error "Unexpected Flutter archive structure"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Clean up download
rm -f "${TMP_FILE}"

# Configure git safe directory
print_info "Configuring git safe directory..."
git config --global --add safe.directory "${VERSION_DIR}" || print_warning "Git config failed, continuing..."

# Run flutter doctor to download Dart SDK and other dependencies
echo ""
print_info "Running flutter doctor (first run)..."
"${CURRENT_LINK}/bin/flutter" doctor || print_warning "Flutter doctor found issues, continuing..."

# Precache common artifacts
echo ""
print_info "Precaching Flutter artifacts..."
"${CURRENT_LINK}/bin/flutter" precache || print_warning "Precache failed, continuing..."

# Add to PATH via env script
append_to_env ""
append_to_env "# Flutter"
append_to_env 'if [ -d "/opt/flutter/current" ]; then'
append_to_env '  export FLUTTER_HOME="/opt/flutter/current"'
append_to_env '  export PATH="$FLUTTER_HOME/bin:$PATH"'
append_to_env 'fi'

# Mark as installed
mark_installed "flutter" "${FLUTTER_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/bin/flutter" --version
echo ""
print_success "Flutter ${FLUTTER_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Flutter in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export PATH=\"${CURRENT_LINK}/bin:\$PATH\""
echo ""
