#!/usr/bin/env bash

set -euo pipefail

# Configuration
JDK_VERSION="${JDK_VERSION:-17}"
JDK_BUILD="${JDK_BUILD:-17.0.16+8}"
INSTALL_DIR="${JAVA_HOME:-/opt/jdk}"
ARCH="${ARCH:-x64}"

echo "=========================================="
echo "Installing Java JDK (Adoptium Temurin)"
echo "=========================================="
echo "JDK Version: ${JDK_VERSION}"
echo "JDK Build: ${JDK_BUILD}"
echo "Install Directory: ${INSTALL_DIR}"
echo "Architecture: ${ARCH}"
echo ""

# Check if already installed
if [ -d "${INSTALL_DIR}" ] && [ -f "${INSTALL_DIR}/bin/java" ]; then
  echo "Java is already installed at ${INSTALL_DIR}"
  "${INSTALL_DIR}/bin/java" -version
  exit 0
fi

# Construct download URL based on version
# Format: https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.16%2B8/OpenJDK17U-jdk_x64_linux_hotspot_17.0.16_8.tar.gz
echo "Downloading JDK ${JDK_BUILD}..."

# URL encode the + sign
JDK_BUILD_ENCODED="${JDK_BUILD//+/%2B}"

# Construct filename (replace + with _)
JDK_BUILD_FILENAME="${JDK_BUILD//+/_}"

DOWNLOAD_URL="https://github.com/adoptium/temurin${JDK_VERSION}-binaries/releases/download/jdk-${JDK_BUILD_ENCODED}/OpenJDK${JDK_VERSION}U-jdk_${ARCH}_linux_hotspot_${JDK_BUILD_FILENAME}.tar.gz"
TMP_FILE="/tmp/jdk_${JDK_VERSION}.tar.gz"

echo "Download URL: ${DOWNLOAD_URL}"
echo ""

curl -L -o "${TMP_FILE}" "${DOWNLOAD_URL}"

# Extract JDK
echo ""
echo "Extracting JDK..."
mkdir -p /opt
tar -xzf "${TMP_FILE}" -C /opt

# Find the extracted directory and rename it
JDK_EXTRACTED_DIR=$(find /opt -maxdepth 1 -type d -name "jdk-${JDK_VERSION}*" | head -n 1)

if [ -z "${JDK_EXTRACTED_DIR}" ]; then
  echo "Error: Could not find extracted JDK directory"
  exit 1
fi

# Move to target directory
if [ "${JDK_EXTRACTED_DIR}" != "${INSTALL_DIR}" ]; then
  mv "${JDK_EXTRACTED_DIR}" "${INSTALL_DIR}"
fi

# Clean up
rm -f "${TMP_FILE}"

# Verify installation
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
"${INSTALL_DIR}/bin/java" -version
echo ""
echo "JDK has been installed to: ${INSTALL_DIR}"
echo ""
echo "To use Java in your shell, add to your profile:"
echo "  export JAVA_HOME=\"${INSTALL_DIR}\""
echo "  export PATH=\"\${JAVA_HOME}/bin:\$PATH\""
echo ""
