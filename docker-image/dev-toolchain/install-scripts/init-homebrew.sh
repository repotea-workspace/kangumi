#!/usr/bin/env bash
#
# init-homebrew.sh - Initialize Homebrew in persistent storage
#
# This script is called during postStart to install Homebrew to /opt/homebrew
# which is mounted from PVC and persists across pod restarts.

set -euo pipefail

HOMEBREW_PREFIX="/opt/homebrew"
BREW_USER="brewuser"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}→${NC} $*"; }
print_success() { echo -e "${GREEN}✓${NC} $*"; }
print_error() { echo -e "${RED}✗${NC} $*" >&2; }
print_warning() { echo -e "${YELLOW}⚠${NC} $*"; }

echo "=========================================="
echo "Homebrew Initialization"
echo "=========================================="
echo ""

# Check if Homebrew is already installed
if [ -x "${HOMEBREW_PREFIX}/bin/brew" ]; then
    print_success "Homebrew is already installed at ${HOMEBREW_PREFIX}"
    
    # Verify it works
    if su - ${BREW_USER} -c "${HOMEBREW_PREFIX}/bin/brew --version" &>/dev/null; then
        BREW_VERSION=$(su - ${BREW_USER} -c "${HOMEBREW_PREFIX}/bin/brew --version" | head -1)
        print_success "Homebrew version: ${BREW_VERSION}"
        echo ""
        print_info "Skipping installation, using existing Homebrew"
        exit 0
    else
        print_warning "Homebrew binary exists but doesn't work, reinstalling..."
    fi
fi

print_info "Installing Homebrew to ${HOMEBREW_PREFIX}..."

# Ensure directory exists with correct ownership
mkdir -p "${HOMEBREW_PREFIX}"
chown ${BREW_USER}:brew "${HOMEBREW_PREFIX}"

# Install Homebrew as brewuser
print_info "Downloading and installing Homebrew..."

# Run the install script
if su - ${BREW_USER} -c "cd ${HOMEBREW_PREFIX} && curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash -s -- --prefix=${HOMEBREW_PREFIX}"; then
    print_success "Homebrew installed successfully"
else
    print_error "Failed to install Homebrew"
    exit 1
fi

# Set correct permissions for group sharing
print_info "Configuring permissions for group sharing..."
chown -R ${BREW_USER}:brew "${HOMEBREW_PREFIX}"
chmod -R g+rX "${HOMEBREW_PREFIX}"
chmod -R g+w "${HOMEBREW_PREFIX}/var" 2>/dev/null || true

# Install yq (required for tools.yaml parsing)
print_info "Installing yq..."
if su - ${BREW_USER} -c "eval \"\$(${HOMEBREW_PREFIX}/bin/brew shellenv)\" && brew install yq"; then
    print_success "yq installed successfully"
else
    print_warning "Failed to install yq, continuing anyway"
fi

echo ""
print_success "Homebrew initialization completed!"
echo ""
echo "Location: ${HOMEBREW_PREFIX}"
echo "User: ${BREW_USER}"
echo "Group: brew"
echo ""
