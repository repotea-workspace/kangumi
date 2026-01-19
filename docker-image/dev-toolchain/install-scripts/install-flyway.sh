#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
FLYWAY_VERSION="${FLYWAY_VERSION:-11.20.2}"
BASE_DIR="/opt/flyway"

print_header "Installing Flyway"
echo "Flyway Version: ${FLYWAY_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo ""

# Flyway requires Java, install it first if not already installed
if ! command -v java &> /dev/null; then
  print_info "Java not found, installing Java first..."
  "${SCRIPT_DIR}/install-java.sh"
  echo ""
fi

# Check if already installed with same version
if check_installed "flyway" "${FLYWAY_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/flyway" ]; then
    "${CURRENT_DIR}/flyway" --version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${FLYWAY_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://github.com/flyway/flyway/releases/download/flyway-11.20.2/flyway-commandline-11.20.2-linux-x64.tar.gz
DOWNLOAD_URL="https://github.com/flyway/flyway/releases/download/flyway-${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz"
TMP_FILE="/tmp/flyway-${FLYWAY_VERSION}.tar.gz"

print_info "Downloading Flyway ${FLYWAY_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download Flyway from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract Flyway
echo ""
print_info "Extracting Flyway..."
TMP_EXTRACT="/tmp/flyway_extract_$$"
mkdir -p "${TMP_EXTRACT}"
tar -xzf "${TMP_FILE}" -C "${TMP_EXTRACT}"

# Find the extracted directory
FLYWAY_EXTRACTED_DIR=$(find "${TMP_EXTRACT}" -maxdepth 1 -type d -name "flyway-${FLYWAY_VERSION}" | head -n 1)

if [ -z "${FLYWAY_EXTRACTED_DIR}" ]; then
  print_error "Could not find extracted Flyway directory"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Move contents to version directory
mv "${FLYWAY_EXTRACTED_DIR}"/* "${VERSION_DIR}/"
rm -rf "${TMP_EXTRACT}"

# Clean up download
rm -f "${TMP_FILE}"

# Make flyway executable
chmod +x "${VERSION_DIR}/flyway"

# Add to PATH via env script
append_to_env ""
append_to_env "# Flyway"
append_to_env 'if [ -d "/opt/flyway/current" ]; then'
append_to_env '  export FLYWAY_HOME="/opt/flyway/current"'
append_to_env '  export PATH="$FLYWAY_HOME:$PATH"'
append_to_env 'fi'

# Mark as installed
mark_installed "flyway" "${FLYWAY_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/flyway" --version
echo ""
print_success "Flyway ${FLYWAY_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Flyway in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export FLYWAY_HOME=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${FLYWAY_HOME}:\$PATH\""
echo ""
echo "Usage examples:"
echo "  flyway --version"
echo "  flyway info"
echo "  flyway migrate"
echo ""
