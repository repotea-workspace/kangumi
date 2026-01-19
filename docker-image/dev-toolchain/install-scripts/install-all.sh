#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKER_FILE="${MARKER_FILE:-/data/.install-completed}"
MARKER_DIR="$(dirname "${MARKER_FILE}")"

# Available packages
AVAILABLE_PACKAGES=(
  "nodejs"
  "rust"
  "flutter"
  "java"
  "golang"
  "devtools"
  "docker-compose"
  "vscode"
  "k8s-tools"
  "gcm"
  "harmonytools"
  "maven"
  "golang-migrate"
  "flyway"
  "liquibase"
  "terraform"
)

# Default packages to install (can be overridden by environment variable)
DEFAULT_PACKAGES="${INSTALL_PACKAGES:-nodejs,rust}"

echo "=========================================="
echo "Dev-Toolchain Installation Script"
echo "=========================================="
echo "Script Directory: ${SCRIPT_DIR}"
echo "Marker File: ${MARKER_FILE}"
echo ""

# Function to check if installation is already done
check_marker() {
  if [ -f "${MARKER_FILE}" ]; then
    echo "Installation already completed (marker file exists: ${MARKER_FILE})"
    echo "Marker content:"
    cat "${MARKER_FILE}"
    echo ""
    echo "To reinstall, remove the marker file:"
    echo "  rm ${MARKER_FILE}"
    return 0
  fi
  return 1
}

# Function to create marker file
create_marker() {
  mkdir -p "${MARKER_DIR}"
  cat > "${MARKER_FILE}" <<EOF
Installation completed at: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Installed packages: ${1}
Hostname: $(hostname)
EOF
  echo ""
  echo "Marker file created: ${MARKER_FILE}"
}

# Function to install a package
install_package() {
  local package="$1"
  local script="${SCRIPT_DIR}/install-${package}.sh"

  if [ ! -f "${script}" ]; then
    echo "Warning: Installation script not found: ${script}"
    return 1
  fi

  echo ""
  echo "=========================================="
  echo "Installing: ${package}"
  echo "=========================================="
  bash "${script}"
  local exit_code=$?

  if [ ${exit_code} -eq 0 ]; then
    echo "✓ ${package} installation completed successfully"
  else
    echo "✗ ${package} installation failed with exit code ${exit_code}"
    return ${exit_code}
  fi

  return 0
}

# Function to show usage
show_usage() {
  cat <<EOF
Usage: $0 [OPTIONS] [PACKAGES...]

Install development tools in the dev-toolchain environment.

OPTIONS:
  -h, --help              Show this help message
  -f, --force             Force reinstall (ignore marker file)
  -a, --all               Install all available packages
  --skip-marker           Do not create marker file after installation

PACKAGES:
  Comma-separated list or space-separated list of packages to install.
  If not specified, uses INSTALL_PACKAGES env var (default: ${DEFAULT_PACKAGES})

  Available packages:
$(printf "    - %s\n" "${AVAILABLE_PACKAGES[@]}")

  Core languages:
    - nodejs        : Node.js via nvm
    - rust          : Rust via rustup
    - flutter       : Flutter SDK
    - java          : Java JDK (Adoptium Temurin)
    - golang        : Go programming language

  Build tools:
    - maven         : Apache Maven build tool
    - harmonytools  : HarmonyOS command-line tools

  Database migration tools:
    - golang-migrate: golang-migrate CLI
    - flyway        : Flyway database migration tool
    - liquibase     : Liquibase database migration tool

  Infrastructure tools:
    - terraform     : Terraform IaC tool
    - k8s-tools     : Kubectl, Helm, Kustomize, Helmfile, ArgoCD, Kubeseal, Talosctl

  Optional tools:
    - devtools      : Additional CLI tools (htop, jq, tmux, etc.)
    - docker-compose: Docker Compose standalone
    - vscode        : VSCode CLI (tunnel support)
    - gcm           : Git Credential Manager

EXAMPLES:
  # Install default packages (nodejs, rust)
  $0

  # Install specific packages
  $0 nodejs flutter
  $0 nodejs,flutter,java

  # Install common development setup
  $0 nodejs,rust,devtools,docker-compose,vscode

  # Install all packages
  $0 --all

  # Force reinstall nodejs
  $0 --force nodejs

  # Install without creating marker file
  $0 --skip-marker nodejs rust

ENVIRONMENT VARIABLES:
  INSTALL_PACKAGES        Default packages to install (comma-separated)
  MARKER_FILE             Path to marker file (default: /data/.install-completed)

EOF
}

# Parse arguments
FORCE=false
SKIP_MARKER=false
INSTALL_ALL=false
PACKAGES_TO_INSTALL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_usage
      exit 0
      ;;
    -f|--force)
      FORCE=true
      shift
      ;;
    -a|--all)
      INSTALL_ALL=true
      shift
      ;;
    --skip-marker)
      SKIP_MARKER=true
      shift
      ;;
    *)
      # Handle comma-separated packages
      IFS=',' read -ra PKGS <<< "$1"
      for pkg in "${PKGS[@]}"; do
        pkg=$(echo "${pkg}" | xargs) # trim whitespace
        if [ -n "${pkg}" ]; then
          PACKAGES_TO_INSTALL+=("${pkg}")
        fi
      done
      shift
      ;;
  esac
done

# Check marker file unless forced
if [ "${FORCE}" = false ] && check_marker; then
  echo "Skipping installation. Use --force to reinstall."
  exit 0
fi

# Determine packages to install
if [ "${INSTALL_ALL}" = true ]; then
  PACKAGES_TO_INSTALL=("${AVAILABLE_PACKAGES[@]}")
  echo "Installing all available packages..."
elif [ ${#PACKAGES_TO_INSTALL[@]} -eq 0 ]; then
  # Use default packages from environment or hardcoded default
  IFS=',' read -ra PACKAGES_TO_INSTALL <<< "${DEFAULT_PACKAGES}"
  echo "Installing default packages: ${DEFAULT_PACKAGES}"
fi

# Validate and clean package names
VALIDATED_PACKAGES=()
for pkg in "${PACKAGES_TO_INSTALL[@]}"; do
  pkg=$(echo "${pkg}" | xargs) # trim whitespace
  if [ -z "${pkg}" ]; then
    continue
  fi

  # Check if package is available
  if [[ " ${AVAILABLE_PACKAGES[@]} " =~ " ${pkg} " ]]; then
    VALIDATED_PACKAGES+=("${pkg}")
  else
    echo "Warning: Unknown package '${pkg}', skipping..."
    echo "Available packages: ${AVAILABLE_PACKAGES[*]}"
  fi
done

if [ ${#VALIDATED_PACKAGES[@]} -eq 0 ]; then
  echo "Error: No valid packages to install"
  echo ""
  show_usage
  exit 1
fi

echo ""
echo "Packages to install: ${VALIDATED_PACKAGES[*]}"
echo ""

# Install packages
FAILED_PACKAGES=()
SUCCESSFUL_PACKAGES=()

for pkg in "${VALIDATED_PACKAGES[@]}"; do
  if install_package "${pkg}"; then
    SUCCESSFUL_PACKAGES+=("${pkg}")
  else
    FAILED_PACKAGES+=("${pkg}")
  fi
done

# Summary
echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo "Successful: ${#SUCCESSFUL_PACKAGES[@]} package(s)"
if [ ${#SUCCESSFUL_PACKAGES[@]} -gt 0 ]; then
  printf "  ✓ %s\n" "${SUCCESSFUL_PACKAGES[@]}"
fi

echo ""
echo "Failed: ${#FAILED_PACKAGES[@]} package(s)"
if [ ${#FAILED_PACKAGES[@]} -gt 0 ]; then
  printf "  ✗ %s\n" "${FAILED_PACKAGES[@]}"
fi

# Create marker file if requested and at least one package succeeded
if [ "${SKIP_MARKER}" = false ] && [ ${#SUCCESSFUL_PACKAGES[@]} -gt 0 ]; then
  create_marker "${SUCCESSFUL_PACKAGES[*]}"
fi

# Exit with error if any package failed
if [ ${#FAILED_PACKAGES[@]} -gt 0 ]; then
  echo ""
  echo "Some packages failed to install. Please check the logs above."
  exit 1
fi

echo ""
echo "=========================================="
echo "All installations completed successfully!"
echo "=========================================="
echo ""
echo "Note: Some tools may require shell restart or sourcing profile:"
echo "  source ~/.bashrc"
echo "  # or"
echo "  source ~/.profile"
echo ""

exit 0
