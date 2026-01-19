#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
LIQUIBASE_VERSION="${LIQUIBASE_VERSION:-5.0.1}"
BASE_DIR="/opt/liquibase"

print_header "Installing Liquibase"
echo "Liquibase Version: ${LIQUIBASE_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo ""

# Liquibase requires Java, install it first if not already installed
if ! command -v java &> /dev/null; then
  print_info "Java not found, installing Java first..."
  "${SCRIPT_DIR}/install-java.sh"
  echo ""
fi

# Check if already installed with same version
if check_installed "liquibase" "${LIQUIBASE_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/liquibase" ]; then
    "${CURRENT_DIR}/liquibase" --version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${LIQUIBASE_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://github.com/liquibase/liquibase/releases/download/v4.30.0/liquibase-4.30.0.tar.gz
DOWNLOAD_URL="https://github.com/liquibase/liquibase/releases/download/v${LIQUIBASE_VERSION}/liquibase-${LIQUIBASE_VERSION}.tar.gz"
TMP_FILE="/tmp/liquibase-${LIQUIBASE_VERSION}.tar.gz"

print_info "Downloading Liquibase ${LIQUIBASE_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download Liquibase from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract Liquibase directly to version directory
echo ""
print_info "Extracting Liquibase..."
tar -xzf "${TMP_FILE}" -C "${VERSION_DIR}"

# Clean up download
rm -f "${TMP_FILE}"

# Verify extraction
if [ ! -f "${VERSION_DIR}/liquibase" ]; then
  print_error "liquibase binary not found after extraction"
  exit 1
fi

# Make liquibase executable
chmod +x "${VERSION_DIR}/liquibase"

# Add to PATH via env script
cat >> "${ENV_SCRIPT}" << 'EOF'

# Liquibase
if [ -d "/opt/liquibase/current" ]; then
  export LIQUIBASE_HOME="/opt/liquibase/current"
  export PATH="$LIQUIBASE_HOME:$PATH"
fi
EOF

# Mark as installed
mark_installed "liquibase" "${LIQUIBASE_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/liquibase" --version
echo ""
print_success "Liquibase ${LIQUIBASE_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Liquibase in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export LIQUIBASE_HOME=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${LIQUIBASE_HOME}:\$PATH\""
echo ""
echo "Usage examples:"
echo "  liquibase --version"
echo "  liquibase --help"
echo "  liquibase update"
echo ""
