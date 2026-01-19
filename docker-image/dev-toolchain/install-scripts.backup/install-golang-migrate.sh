#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
MIGRATE_VERSION="${MIGRATE_VERSION:-4.19.1}"
BASE_DIR="/opt/migrate"

# Environment variable block
ENV_BLOCK='# golang-migrate
if [ -d "/opt/migrate/current" ]; then
  export PATH="/opt/migrate/current:$PATH"
fi'

print_header "Installing golang-migrate"
echo "Version: ${MIGRATE_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed with same version
if check_installed "golang-migrate" "${MIGRATE_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/migrate" ]; then
    # Ensure env vars are present even if already installed
    ensure_env_block "# golang-migrate" "${ENV_BLOCK}"
    print_success "golang-migrate environment variables ensured in ${ENV_SCRIPT}"
    "${CURRENT_DIR}/migrate" -version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${MIGRATE_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://github.com/golang-migrate/migrate/releases/download/v4.18.1/migrate.linux-amd64.tar.gz
DOWNLOAD_URL="https://github.com/golang-migrate/migrate/releases/download/v${MIGRATE_VERSION}/migrate.linux-amd64.tar.gz"
TMP_FILE="/tmp/migrate-${MIGRATE_VERSION}.tar.gz"

print_info "Downloading golang-migrate ${MIGRATE_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract migrate binary
echo ""
print_info "Extracting migrate binary..."
tar -xzf "${TMP_FILE}" -C "${VERSION_DIR}"

# Clean up download
rm -f "${TMP_FILE}"

# Verify extraction
if [ ! -f "${VERSION_DIR}/migrate" ]; then
  print_error "migrate binary not found after extraction"
  exit 1
fi

# Make binary executable
chmod +x "${VERSION_DIR}/migrate"

# Add to PATH via env script
ensure_env_block "# golang-migrate" "${ENV_BLOCK}"

# Mark as installed
mark_installed "golang-migrate" "${MIGRATE_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
migrate -version
echo ""
print_success "golang-migrate ${MIGRATE_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use golang-migrate in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Usage examples:"
echo "  migrate -version"
echo "  migrate -help"
echo "  migrate -source file://path/to/migrations -database postgres://localhost:5432/database up"
echo ""
