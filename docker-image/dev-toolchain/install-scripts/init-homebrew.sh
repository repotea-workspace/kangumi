#!/usr/bin/env bash
#
# init-homebrew.sh - Initialize Homebrew in persistent storage
#
# This script is called during postStart to install Homebrew to /opt/homebrew
# which is mounted from PVC and persists across pod restarts.
#
# Homebrew is installed and managed by root for simplified access.

set -euo pipefail

# Use standard Linux Homebrew prefix to avoid architecture conflicts
# On Linux x86_64, /opt/homebrew is reserved for ARM architecture
# We use /home/linuxbrew/.linuxbrew which will be mounted from PVC
HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew"

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
    if ${HOMEBREW_PREFIX}/bin/brew --version >/dev/null 2>&1; then
        print_success "Homebrew is working correctly"
        echo ""
        print_info "Skipping installation, using existing Homebrew"
        exit 0
    else
        print_warning "Homebrew binary exists but doesn't work, reinstalling..."
    fi
fi

print_info "Installing Homebrew to ${HOMEBREW_PREFIX}..."

# Ensure directory exists
mkdir -p "${HOMEBREW_PREFIX}"

# Set environment for Homebrew installation
export HOMEBREW_ALLOW_ROOT=1
export NONINTERACTIVE=1

# Install Homebrew as root
print_info "Downloading and installing Homebrew..."

# Create parent directory if needed
mkdir -p "$(dirname "${HOMEBREW_PREFIX}")"

# Use git clone method for custom prefix installation
if git clone --depth=1 https://github.com/Homebrew/brew "${HOMEBREW_PREFIX}"; then
    print_success "Homebrew cloned successfully"

    # Verify installation
    if "${HOMEBREW_PREFIX}/bin/brew" --version &>/dev/null; then
        print_success "Homebrew installed successfully"
    else
        print_error "Homebrew installation verification failed"
        exit 1
    fi
else
    print_error "Failed to clone Homebrew"
    exit 1
fi

# Install yq (required for tools.yaml parsing)
print_info "Installing yq..."
export PATH="${HOMEBREW_PREFIX}/bin:${PATH}"
if ${HOMEBREW_PREFIX}/bin/brew install yq; then
    print_success "yq installed successfully"
else
    print_warning "Failed to install yq, continuing anyway"
fi

echo ""
print_success "Homebrew initialization completed!"
echo ""
echo "Location: ${HOMEBREW_PREFIX}"
echo "Managed by: root"
echo "All users can use: brew commands directly"
echo ""
