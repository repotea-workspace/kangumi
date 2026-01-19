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
  print_warning() { echo "⚠ $*"; }
  print_header() { echo "=========================================="; echo "$*"; echo "=========================================="; }
fi

# Tool name mapping: script name -> brew formula
declare -A BREW_FORMULAS=(
  ["docker-compose"]="docker-compose"
  ["flutter"]="flutter"
  ["flyway"]="flyway"
  ["gcm"]="git-credential-manager"
  ["golang"]="go"
  ["golang-migrate"]="golang-migrate"
  ["java"]="openjdk@17"
  ["k8s-tools"]="kubectl helm kustomize helmfile argocd kubeseal"
  ["talosctl"]="siderolabs/tap/talosctl"
  ["liquibase"]="liquibase"
  ["maven"]="maven"
  ["nodejs"]="node"
  ["rust"]="rust"
  ["terraform"]="terraform"
)

# Special handling: tools that need tap
declare -A BREW_TAPS=(
  ["talosctl"]="siderolabs/tap"
)

print_header "Installing Development Tools via Homebrew"

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
  print_error "Homebrew is not installed. Please run install-homebrew.sh first."
  exit 1
fi

# Get tool name from argument or environment
TOOL_NAME="${1:-}"

if [ -z "${TOOL_NAME}" ]; then
  print_error "Usage: $0 <tool-name>"
  echo ""
  echo "Available tools:"
  for tool in "${!BREW_FORMULAS[@]}"; do
    echo "  - ${tool}"
  done
  exit 1
fi

# Check if tool is supported
if [ -z "${BREW_FORMULAS[$TOOL_NAME]:-}" ]; then
  print_error "Unknown tool: ${TOOL_NAME}"
  echo ""
  echo "Available tools:"
  for tool in "${!BREW_FORMULAS[@]}"; do
    echo "  - ${tool}"
  done
  exit 1
fi

# Brew command wrapper - run as linuxbrew user if we're root
brew_cmd() {
  if [ "$(id -u)" -eq 0 ]; then
    sudo -u linuxbrew -H bash -c "eval \"\$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\" && brew $*"
  else
    brew "$@"
  fi
}

# Add tap if needed
if [ -n "${BREW_TAPS[$TOOL_NAME]:-}" ]; then
  TAP_NAME="${BREW_TAPS[$TOOL_NAME]}"
  print_info "Adding tap: ${TAP_NAME}"
  brew_cmd tap "${TAP_NAME}" || print_warning "Failed to add tap ${TAP_NAME}, continuing..."
fi

# Get formula(s) for the tool
FORMULAS="${BREW_FORMULAS[$TOOL_NAME]}"

print_info "Installing ${TOOL_NAME}..."
echo "Formula(s): ${FORMULAS}"
echo ""

# Install the formula(s)
INSTALL_FAILED=0

for formula in ${FORMULAS}; do
  print_info "Installing ${formula}..."

  # Check if already installed
  if brew_cmd list "${formula}" &> /dev/null; then
    print_success "${formula} is already installed"
    brew_cmd info "${formula}" | head -3
    continue
  fi

  # Install the formula
  if brew_cmd install "${formula}"; then
    print_success "${formula} installed successfully"
  else
    print_error "Failed to install ${formula}"
    INSTALL_FAILED=1
  fi
done

# Special post-install configurations
case "${TOOL_NAME}" in
  "java")
    # Link Java for system-wide use
    if brew_cmd list openjdk@17 &> /dev/null; then
      JAVA_HOME="$(brew_cmd --prefix openjdk@17)"
      print_info "Java installed at: ${JAVA_HOME}"
      # Note: JAVA_HOME will be set by brew shellenv
    fi
    ;;

  "gcm")
    # Configure git to use credential manager
    if command -v git-credential-manager &> /dev/null; then
      print_info "Configuring git credential helper..."
      git config --global credential.helper manager || print_warning "Failed to configure git credential helper"
    fi
    ;;
esac

# Verify installation
echo ""
print_header "Installation Summary"

VERIFY_FAILED=0
for formula in ${FORMULAS}; do
  if brew_cmd list "${formula}" &> /dev/null; then
    VERSION=$(brew_cmd info "${formula}" --json | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    print_success "${formula} (${VERSION})"
  else
    print_error "${formula} - NOT INSTALLED"
    VERIFY_FAILED=1
  fi
done

echo ""

if [ ${INSTALL_FAILED} -eq 0 ] && [ ${VERIFY_FAILED} -eq 0 ]; then
  print_success "All tools for ${TOOL_NAME} installed successfully!"
  echo ""
  echo "Note: Homebrew environment is automatically loaded in new shells."
  echo "For current shell, run:"
  echo "  eval \"\$(brew shellenv)\""
  exit 0
else
  print_error "Some tools failed to install"
  exit 1
fi
