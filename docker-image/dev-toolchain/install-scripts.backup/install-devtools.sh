#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

print_header "Installing Development Tools"
echo ""

# Check if already installed via marker
if check_installed "devtools"; then
  if command -v htop &> /dev/null && command -v jq &> /dev/null && command -v tree &> /dev/null; then
    print_success "Development tools are already installed"
    exit 0
  fi
fi

print_info "Installing additional packages via apt..."

apt-get update -y

apt-get install --no-install-recommends -y \
  # Additional editors
  emacs-nox \
  # Terminal tools
  htop ncdu tmux screen \
  # Advanced build tools
  cmake autoconf automake libtool \
  pkg-config libssl-dev \
  clang llvm \
  # Protobuf compiler
  protobuf-compiler \
  # Python tools
  python3-pip python3-dev python3-venv \
  # Git helpers
  gnupg pass git-lfs \
  # JSON/YAML tools
  jq yq \
  # Network diagnostic tools
  netcat-openbsd telnet traceroute \
  dnsutils net-tools tcpdump nmap \
  # Process tools
  psmisc lsof strace \
  # File tools
  rsync tree ripgrep fd-find \
  # Compression tools
  p7zip-full rar unrar-free \
  # Misc utilities
  colordiff moreutils shellcheck

# Create python symlink
if [ ! -e /usr/bin/python ]; then
  ln -s /usr/bin/python3 /usr/bin/python
fi

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*

# Mark as installed
mark_installed "devtools" "latest"

echo ""
print_header "Installation completed!"
echo "Installed tools:"
echo "  - Editors: emacs"
echo "  - Terminal: htop, ncdu, tmux, screen"
echo "  - Build: cmake, autoconf, clang, llvm"
echo "  - Python: pip, venv"
echo "  - JSON/YAML: jq, yq"
echo "  - Network: netcat, telnet, traceroute, tcpdump, nmap"
echo "  - File: rsync, tree, ripgrep, fd"
echo "  - Git: git-lfs"
echo ""
