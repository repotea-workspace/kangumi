#!/usr/bin/env bash
#
# install-devtools.sh - Install system development tools
#
# This script only installs packages that MUST use apt because:
# - They are system libraries
# - They are not available in Homebrew
# - They work better as system packages
#
# For other tools, use: install-brew-tools.sh <package>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

print_header "Installing System Development Tools"
echo ""

# Check if already installed
if check_installed "devtools"; then
  print_success "System development tools are already installed"
  exit 0
fi

print_info "Installing system packages via apt..."

apt-get update -y

apt-get install --no-install-recommends -y \
  # Build system dependencies (not in Homebrew or needed for compilation)
  autoconf automake libtool pkg-config \
  # System libraries (dev headers)
  libssl-dev \
  # Python (system Python for tools that depend on it)
  python3-pip python3-dev python3-venv \
  # Git security (gnupg for GPG, pass for password store)
  gnupg pass

# Create python symlink
if [ ! -e /usr/bin/python ]; then
  print_info "Creating python -> python3 symlink..."
  ln -s /usr/bin/python3 /usr/bin/python
fi

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*

# Mark as installed
mark_installed "devtools" "latest"

echo ""
print_success "System development tools installed!"
echo ""
echo "Installed packages:"
echo "  - Build tools: autoconf, automake, libtool, pkg-config"
echo "  - Libraries: libssl-dev"
echo "  - Python: python3-pip, python3-dev, python3-venv"
echo "  - Git security: gnupg, pass"
echo ""
echo "For other development tools, use Homebrew:"
echo "  install-brew-tools.sh <package>"
echo ""
echo "Examples:"
echo "  install-brew-tools.sh golang nodejs"
echo "  install-brew-tools.sh htop tmux jq"
echo "  install-brew-tools.sh k8s-tools"
echo ""
