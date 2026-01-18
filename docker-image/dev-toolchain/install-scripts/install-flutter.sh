#!/usr/bin/env bash

set -euo pipefail

# Configuration
FLUTTER_VERSION="${FLUTTER_VERSION:-3.35.1}"
INSTALL_DIR="${FLUTTER_HOME:-/opt/flutter}"
FLUTTER_CHANNEL="${FLUTTER_CHANNEL:-stable}"

echo "=========================================="
echo "Installing Flutter SDK"
echo "=========================================="
echo "Version: ${FLUTTER_VERSION}"
echo "Channel: ${FLUTTER_CHANNEL}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Check if already installed
if [ -d "${INSTALL_DIR}" ] && [ -f "${INSTALL_DIR}/bin/flutter" ]; then
  echo "Flutter is already installed at ${INSTALL_DIR}"
  "${INSTALL_DIR}/bin/flutter" --version

  # Update Flutter
  echo ""
  echo "Updating Flutter..."
  "${INSTALL_DIR}/bin/flutter" upgrade

  exit 0
fi

# Download Flutter
echo "Downloading Flutter ${FLUTTER_VERSION}..."
DOWNLOAD_URL="https://storage.googleapis.com/flutter_infra_release/releases/${FLUTTER_CHANNEL}/linux/flutter_linux_${FLUTTER_VERSION}-${FLUTTER_CHANNEL}.tar.xz"
TMP_FILE="/tmp/flutter_${FLUTTER_VERSION}.tar.xz"

curl -L -o "${TMP_FILE}" "${DOWNLOAD_URL}"

# Extract Flutter
echo ""
echo "Extracting Flutter to ${INSTALL_DIR}..."
mkdir -p "$(dirname "${INSTALL_DIR}")"
tar -xf "${TMP_FILE}" -C "$(dirname "${INSTALL_DIR}")"

# Clean up
rm -f "${TMP_FILE}"

# Configure git safe directory
echo ""
echo "Configuring git safe directory..."
git config --global --add safe.directory "${INSTALL_DIR}"

# Run flutter doctor to download Dart SDK and other dependencies
echo ""
echo "Running flutter doctor (first run)..."
"${INSTALL_DIR}/bin/flutter" doctor

# Precache common artifacts
echo ""
echo "Precaching Flutter artifacts..."
"${INSTALL_DIR}/bin/flutter" precache

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
"${INSTALL_DIR}/bin/flutter" --version
echo ""
echo "Flutter has been installed to: ${INSTALL_DIR}"
echo ""
echo "To use Flutter in your shell, add to your profile:"
echo "  export PATH=\"${INSTALL_DIR}/bin:\$PATH\""
echo ""
echo "Run 'flutter doctor' to check your environment:"
echo "  ${INSTALL_DIR}/bin/flutter doctor"
echo ""
