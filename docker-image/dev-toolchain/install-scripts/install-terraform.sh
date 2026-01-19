#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
TERRAFORM_VERSION="${TERRAFORM_VERSION:-1.14.3}"
BASE_DIR="/opt/terraform"
INSTALL_DIR="/usr/local/bin"

print_header "Installing Terraform"
echo "Version: ${TERRAFORM_VERSION}"
echo "Base Directory: ${BASE_DIR}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed with same version
if check_installed "terraform" "${TERRAFORM_VERSION}"; then
  if command -v terraform &> /dev/null; then
    terraform version
    exit 0
  fi
fi

# Setup version directory structure
VERSION_DIR=$(setup_version_dir "${BASE_DIR}" "${TERRAFORM_VERSION}")
CURRENT_LINK="${BASE_DIR}/current"

print_info "Installing to ${VERSION_DIR}..."

# Construct download URL
# Format: https://releases.hashicorp.com/terraform/1.10.3/terraform_1.10.3_linux_amd64.zip
DOWNLOAD_URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
TMP_FILE="/tmp/terraform-${TERRAFORM_VERSION}.zip"

print_info "Downloading Terraform ${TERRAFORM_VERSION}..."

if ! curl -fSL -o "${TMP_FILE}" "${DOWNLOAD_URL}"; then
  print_error "Failed to download from ${DOWNLOAD_URL}"
  exit 1
fi

# Extract terraform binary
echo ""
print_info "Extracting terraform binary..."
unzip -q "${TMP_FILE}" -d "${VERSION_DIR}"

# Clean up download
rm -f "${TMP_FILE}"

# Verify extraction
if [ ! -f "${VERSION_DIR}/terraform" ]; then
  print_error "terraform binary not found after extraction"
  exit 1
fi

# Make binary executable
chmod +x "${VERSION_DIR}/terraform"

# Create symlink in /usr/local/bin
ln -sf "${CURRENT_LINK}/terraform" "${INSTALL_DIR}/terraform"

# Mark as installed
mark_installed "terraform" "${TERRAFORM_VERSION}"

# Verify installation
echo ""
print_header "Installation completed!"
terraform version
echo ""
print_success "Terraform ${TERRAFORM_VERSION} has been installed to: ${VERSION_DIR}"
print_success "Current version symlink: ${CURRENT_LINK}"
print_success "Binary symlinked to: ${INSTALL_DIR}/terraform"
echo ""
echo "Usage examples:"
echo "  terraform version"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
echo ""
