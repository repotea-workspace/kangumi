#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
GOLANG_VERSION="${GOLANG_VERSION:-1.25.6}"
BASE_DIR="/opt/golang"
ARCH="${ARCH:-amd64}"

print_header "Installing Go Programming Language"
echo "Go Version: ${GOLANG_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo "Architecture: ${ARCH}"
echo ""

# Check if already installed with same version
if check_installed "golang" "${GOLANG_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/bin/go" ]; then
    "${CURRENT_DIR}/bin/go" version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "v${GOLANG_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://go.dev/dl/go1.23.5.linux-amd64.tar.gz
DOWNLOAD_URL="https://go.dev/dl/go${GOLANG_VERSION}.linux-${ARCH}.tar.gz"
TMP_FILE="/tmp/go${GOLANG_VERSION}.tar.gz"

print_info "Downloading Go ${GOLANG_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download Go from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract Go
echo ""
print_info "Extracting Go..."
tar -xzf "${TMP_FILE}" -C "${VERSION_DIR}" --strip-components=1

# Clean up download
rm -f "${TMP_FILE}"

# Verify installation
if [ ! -f "${VERSION_DIR}/bin/go" ]; then
  print_error "Installation verification failed: go binary not found"
  exit 1
fi

# Add to PATH via env script
cat >> "${ENV_SCRIPT}" << 'EOF'

# Go Programming Language
if [ -d "/opt/golang/current" ]; then
  export GOROOT="/opt/golang/current"
  export PATH="$GOROOT/bin:$PATH"
  # GOPATH defaults to $HOME/go, users can override if needed
  export PATH="$HOME/go/bin:$PATH"
fi
EOF

# Mark as installed
mark_installed "golang" "${GOLANG_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/bin/go" version
echo ""
print_success "Go ${GOLANG_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Go in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export GOROOT=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${GOROOT}/bin:\$PATH\""
echo "  export PATH=\"\$HOME/go/bin:\$PATH\""
echo ""
echo "GOPATH will default to \$HOME/go"
echo "You can set it explicitly if needed:"
echo "  export GOPATH=\"/path/to/your/workspace\""
echo ""
