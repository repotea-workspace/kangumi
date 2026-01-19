#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
MAVEN_VERSION="${MAVEN_VERSION:-3.9.12}"
BASE_DIR="/opt/maven"
ARCH="${ARCH:-x64}"

# Environment variable block
ENV_BLOCK='# Apache Maven
if [ -d "/opt/maven/current" ]; then
  export MAVEN_HOME="/opt/maven/current"
  export M2_HOME="/opt/maven/current"
  export PATH="$MAVEN_HOME/bin:$PATH"
fi'

print_header "Installing Apache Maven"
echo "Maven Version: ${MAVEN_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo ""

# Maven requires Java, install it first if not already installed
if ! command -v java &> /dev/null; then
  print_info "Java not found, installing Java first..."
  "${SCRIPT_DIR}/install-java.sh"
  echo ""
fi

# Check if already installed with same version
if check_installed "maven" "${MAVEN_VERSION}"; then
  CURRENT_DIR="${BASE_DIR}/current"
  if [ -d "${CURRENT_DIR}" ] && [ -f "${CURRENT_DIR}/bin/mvn" ]; then
    # Ensure env vars are present even if already installed
    ensure_env_block "# Apache Maven" "${ENV_BLOCK}"
    print_success "Maven environment variables ensured in ${ENV_SCRIPT}"
    "${CURRENT_DIR}/bin/mvn" --version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${MAVEN_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
MAVEN_MAJOR=$(echo "${MAVEN_VERSION}" | cut -d. -f1)
DOWNLOAD_URL="https://archive.apache.org/dist/maven/maven-${MAVEN_MAJOR}/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz"
TMP_FILE="/tmp/maven-${MAVEN_VERSION}.tar.gz"

print_info "Downloading Maven ${MAVEN_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download Maven from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract Maven
echo ""
print_info "Extracting Maven..."
TMP_EXTRACT="/tmp/maven_extract_$$"
mkdir -p "${TMP_EXTRACT}"
tar -xzf "${TMP_FILE}" -C "${TMP_EXTRACT}"

# Find the extracted directory
MAVEN_EXTRACTED_DIR=$(find "${TMP_EXTRACT}" -maxdepth 1 -type d -name "apache-maven-${MAVEN_VERSION}" | head -n 1)

if [ -z "${MAVEN_EXTRACTED_DIR}" ]; then
  print_error "Could not find extracted Maven directory"
  rm -rf "${TMP_EXTRACT}"
  exit 1
fi

# Move contents to version directory
mv "${MAVEN_EXTRACTED_DIR}"/* "${VERSION_DIR}/"
rm -rf "${TMP_EXTRACT}"

# Clean up download
rm -f "${TMP_FILE}"

# Add to PATH via env script
ensure_env_block "# Apache Maven" "${ENV_BLOCK}"

# Mark as installed
mark_installed "maven" "${MAVEN_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
"${CURRENT_LINK}/bin/mvn" --version
echo ""
print_success "Maven ${MAVEN_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
echo ""
echo "To use Maven in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export MAVEN_HOME=\"${CURRENT_LINK}\""
echo "  export M2_HOME=\"${CURRENT_LINK}\""
echo "  export PATH=\"\${MAVEN_HOME}/bin:\$PATH\""
echo ""
