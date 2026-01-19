#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
RUSTUP_INIT_VERSION="${RUSTUP_INIT_VERSION:-latest}"
RUST_TOOLCHAIN="${RUST_TOOLCHAIN:-stable}"
CARGO_HOME="${CARGO_HOME:-${HOME}/.cargo}"
RUSTUP_HOME="${RUSTUP_HOME:-${HOME}/.rustup}"

print_header "Installing Rust via rustup"
echo "Toolchain: ${RUST_TOOLCHAIN}"
echo "Cargo Home: ${CARGO_HOME}"
echo "Rustup Home: ${RUSTUP_HOME}"
echo ""

# Check if already installed with same toolchain
if check_installed "rust" "${RUST_TOOLCHAIN}"; then
  if [ -f "${CARGO_HOME}/bin/rustc" ]; then
    source "${CARGO_HOME}/env"
    echo "Rust version: $(rustc --version)"
    echo "Cargo version: $(cargo --version)"

    # Optional: Update rustup
    print_info "Updating rustup..."
    "${CARGO_HOME}/bin/rustup" update || print_warning "Rustup update failed, continuing..."
    exit 0
  fi
fi

# Check if rustup is already installed (but maybe different toolchain)
if [ -f "${CARGO_HOME}/bin/rustc" ]; then
  print_info "Rust is already installed at ${CARGO_HOME}"
  source "${CARGO_HOME}/env"

  "${CARGO_HOME}/bin/rustc" --version
  "${CARGO_HOME}/bin/cargo" --version

  # Update rustup
  echo ""
  print_info "Updating rustup..."
  "${CARGO_HOME}/bin/rustup" update

  mark_installed "rust" "${RUST_TOOLCHAIN}"
  exit 0
fi

# Install rustup
print_info "Installing rustup..."
export CARGO_HOME="${CARGO_HOME}"
export RUSTUP_HOME="${RUSTUP_HOME}"

if ! curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain "${RUST_TOOLCHAIN}"; then
  print_error "Failed to install rustup"
  exit 1
fi

# Source cargo env
source "${CARGO_HOME}/env"

# Install rust-src component (for IDE support)
echo ""
print_info "Installing rust-src component..."
rustup component add rust-src || print_warning "Failed to add rust-src component"

# Install commonly used components
echo ""
print_info "Installing additional components..."
rustup component add rustfmt clippy || print_warning "Failed to add some components"

# Add to PATH via env script
cat >> "${ENV_SCRIPT}" << 'EOF'

# Rust (cargo)
export CARGO_HOME="/root/.cargo"
export RUSTUP_HOME="/root/.rustup"
[ -s "$CARGO_HOME/env" ] && \. "$CARGO_HOME/env"
EOF

# Mark as installed
mark_installed "rust" "${RUST_TOOLCHAIN}"

# Verify installation
echo ""
print_header "Installation completed!"
echo "Rust version: $(rustc --version)"
echo "Cargo version: $(cargo --version)"
echo "Rustup version: $(rustup --version)"
echo ""
echo "Installed components:"
rustup component list --installed
echo ""
print_success "Cargo has been installed to: ${CARGO_HOME}"
print_success "Rustup has been installed to: ${RUSTUP_HOME}"
echo ""
echo "To use Rust in your shell, run:"
echo "  source /etc/profile.d/99-dev-tools-env.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export CARGO_HOME=\"${CARGO_HOME}\""
echo "  export RUSTUP_HOME=\"${RUSTUP_HOME}\""
echo "  source \"\$CARGO_HOME/env\""
echo ""
