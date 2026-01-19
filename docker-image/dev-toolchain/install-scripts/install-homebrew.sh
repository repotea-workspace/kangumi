#!/usr/bin/env bash

set -euo pipefail

# Load common functions if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/common.sh" ]; then
  source "${SCRIPT_DIR}/common.sh"
else
  # Minimal print functions if common.sh not available
  print_info() { echo "→ $*"; }
  print_success() { echo "✓ $*"; }
  print_error() { echo "✗ $*" >&2; }
  print_header() { echo "=========================================="; echo "$*"; echo "=========================================="; }
fi

print_header "Installing Homebrew"

# Check if already installed
if command -v brew &> /dev/null; then
  print_success "Homebrew is already installed"
  brew --version
  exit 0
fi

# Download and run Homebrew install script
print_info "Downloading Homebrew installation script..."
HOMEBREW_INSTALL_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

# Run in non-interactive mode
export NONINTERACTIVE=1

print_info "Installing Homebrew (this may take a few minutes)..."
if ! curl -fsSL "${HOMEBREW_INSTALL_URL}" | bash; then
  print_error "Homebrew installation failed"
  exit 1
fi

# Set up Homebrew environment
BREW_PREFIX="/opt/homebrew"
if [ -d "${BREW_PREFIX}" ] && [ -f "${BREW_PREFIX}/bin/brew" ]; then
  eval "$(${BREW_PREFIX}/bin/brew shellenv)"
else
  print_error "Homebrew installation directory not found: ${BREW_PREFIX}"
  exit 1
fi

# Verify installation
if ! command -v brew &> /dev/null; then
  print_error "Homebrew installation verification failed"
  exit 1
fi

# Disable analytics and auto-update
brew analytics off

echo ""
print_header "Installation completed!"
brew --version
echo ""
print_success "Homebrew has been installed to: ${BREW_PREFIX}"
echo ""
echo "To use Homebrew in your shell, add to your shell profile:"
echo "  eval \"\$(${BREW_PREFIX}/bin/brew shellenv)\""
echo ""
echo "Or source it immediately:"
echo "  eval \"\$(${BREW_PREFIX}/bin/brew shellenv)\""
echo ""
