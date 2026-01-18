#!/usr/bin/env bash

set -euo pipefail

# Configuration
RUSTUP_INIT_VERSION="${RUSTUP_INIT_VERSION:-latest}"
RUST_TOOLCHAIN="${RUST_TOOLCHAIN:-stable}"
INSTALL_DIR="${CARGO_HOME:-${HOME}/.cargo}"

echo "=========================================="
echo "Installing Rust via rustup"
echo "=========================================="
echo "Toolchain: ${RUST_TOOLCHAIN}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -f "${INSTALL_DIR}/bin/rustc" ]; then
  echo "Rust is already installed at ${INSTALL_DIR}"
  "${INSTALL_DIR}/bin/rustc" --version
  "${INSTALL_DIR}/bin/cargo" --version

  # Update rustup
  echo ""
  echo "Updating rustup..."
  "${INSTALL_DIR}/bin/rustup" update

  exit 0
fi

# Install rustup
echo "Installing rustup..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain "${RUST_TOOLCHAIN}"

# Source cargo env
source "${INSTALL_DIR}/env"

# Install rust-src component (for IDE support)
echo ""
echo "Installing rust-src component..."
rustup component add rust-src

# Install commonly used components
echo ""
echo "Installing additional components..."
rustup component add rustfmt clippy

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
echo "Rust version: $(rustc --version)"
echo "Cargo version: $(cargo --version)"
echo "Rustup version: $(rustup --version)"
echo ""
echo "Installed components:"
rustup component list --installed
echo ""
echo "Cargo has been installed to: ${INSTALL_DIR}"
echo ""
echo "To use Rust in your shell, add to your profile:"
echo "  export PATH=\"${INSTALL_DIR}/bin:\$PATH\""
echo "  source \"${INSTALL_DIR}/env\""
echo ""
