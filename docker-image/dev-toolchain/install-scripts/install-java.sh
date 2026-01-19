#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
JDK_VERSION="${JDK_VERSION:-17}"
JDK_BUILD="${JDK_BUILD:-17.0.16+8}"
BASE_DIR="/opt/java"
ARCH="${ARCH:-x64}"

print_header "Installing Java JDK (Adoptium Temurin)"
echo "JDK Version: ${JDK_VERSION}"
echo "JDK Build: ${JDK_BUILD}"
echo "Base Directory: ${BASE_DIR}"
echo "Architecture: ${ARCH}"
echo ""

# Check if already installed with same version
if check_installed "java" "${JDK_BUILD}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/bin/java" ]; then
    "${CURRENT_DIR}/bin/java" -version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${JDK_BUILD}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL based on version
# Format: https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.16%2B8/OpenJDK17U-jdk_x64_linux_hotspot_17.0.16_8.tar.gz
print_info "Downloading JDK ${JDK_BUILD}..."

# URL encode the + sign
JDK_BUILD_ENCODED="${JDK_BUILD//+/%2B}"

# Construct filename (replace + with _)
JDK_BUILD_FILENAME="${JDK_BUILD//+/_}"

DOWNLOAD_URL="https://github.com/adoptium/temurin${JDK_VERSION}-binaries/releases/download/jdk-${JDK_BUILD_ENCODED}/OpenJDK${JDK_VERSION}U-jdk_${ARCH}_linux_hotspot_${JDK_BUILD_FILENAME}.tar.gz"
TMP_FILE="/tmp/jdk_${JDK_VERSION}_${JDK_BUILD_FILENAME}.tar.gz"

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download JDK from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract JDK
echo ""
print_info "Extracting JDK..."
TMP_EXTRACT="/tmp/jdk_extract_$$"
mkdir -p "${TMP_EXTRACT}"
tar -xzf "${TMP_FILE}" -C "${TMP_EXTRACT}"

# Find the extracted directory
JDK_EXTRACTED_DIR=$(find "${TMP_EXTRACT}" -maxdepth 1 -type d -name "jdk-${JDK_VERSION}*" | head -n 1)

if [ -z "${JDK_EXTRACTED_DIR}" ]; then
  print_error "Could not find extracted JDK directory"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Move contents to version directory
mv "${JDK_EXTRACTED_DIR}"/* "${VERSION_DIR}/"
rm -rf "${TMP_EXTRACT}"

# Clean up download
rm -f "${TMP_FILE}"

# Add to PATH via env script
append_to_env ""
append_to_env "# Java"
append_to_env 'if [ -d "/opt/java/current" ]; then'
append_to_env '  export JAVA_HOME="/opt/java/current"'
append_to_env '  export PATH="$JAVA_HOME/bin:$PATH"'
append_to_env 'fi'

# Mark as installed
mark_installed "java" "${JDK_BUILD}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/bin/java" -version
echo ""
print_success "JDK ${JDK_BUILD} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Java in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export JAVA_HOME=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${JAVA_HOME}/bin:\$PATH\""
echo ""
