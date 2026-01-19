#!/usr/bin/env bash
#
# install-brew-tools.sh - Install development tools via Homebrew
#
# This script can install tools in two ways:
# 1. From tools.yaml definitions (for predefined tool groups and metadata)
# 2. Directly as brew formulas (any package in Homebrew)
#
# If a tool is found in tools.yaml, it uses the definition there.
# Otherwise, it treats the argument as a direct brew formula.
#
# Usage:
#   install-brew-tools.sh <tool-name>
#   install-brew-tools.sh <tool1> <tool2> <tool3>
#
# Examples:
#   install-brew-tools.sh golang          # From tools.yaml
#   install-brew-tools.sh k8s-tools       # From tools.yaml (installs multiple packages)
#   install-brew-tools.sh neovim          # Direct brew formula
#   install-brew-tools.sh any-brew-pkg    # Any Homebrew package

set -euo pipefail

# Configuration
TOOLS_CONFIG="${TOOLS_CONFIG:-/usr/local/lib/dev-tools/install-scripts/tools.yaml}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}→${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

print_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$*"
    echo "=========================================="
}

# Load common functions if available
if [ -f "${SCRIPT_DIR}/common.sh" ]; then
    source "${SCRIPT_DIR}/common.sh"
fi

# Brew command wrapper - intelligently handle different users
brew_cmd() {
    local current_user=$(whoami)

    if [ "${current_user}" = "brewuser" ]; then
        # Native execution as brewuser user
        eval "$(/opt/homebrew/bin/brew shellenv)"
        brew "$@"
    else
        # Execute as brewuser user via sudo for other users
        sudo -u brewuser -H bash -c "eval \"\$(/opt/homebrew/bin/brew shellenv)\" && brew $*"
    fi
}

# Check if Homebrew is installed
check_homebrew() {
    if ! command -v brew &> /dev/null && [ ! -x /opt/homebrew/bin/brew ]; then
        print_error "Homebrew is not installed. Please run install-homebrew.sh first."
        exit 1
    fi
}

# Check if yq is available (optional, only needed if tools.yaml exists and we want to read it)
has_yq() {
    command -v yq &> /dev/null
}

# Check if tool exists in tools.yaml
tool_exists_in_yaml() {
    local tool_name="$1"

    # If tools.yaml doesn't exist or yq isn't available, return false
    [ ! -f "${TOOLS_CONFIG}" ] && return 1
    ! has_yq && return 1

    local result
    result=$(yq eval ".tools.${tool_name}" "${TOOLS_CONFIG}" 2>/dev/null || echo "null")
    [ "${result}" != "null" ]
}

# Get tool info from tools.yaml
get_tool_info() {
    local tool_name="$1"
    local field="$2"

    yq eval ".tools.${tool_name}.${field}" "${TOOLS_CONFIG}" 2>/dev/null || echo "null"
}

# Add tap if needed
add_tap() {
    local tool_name="$1"
    local tap_name

    tap_name=$(get_tool_info "${tool_name}" "tap")

    if [ "${tap_name}" != "null" ] && [ -n "${tap_name}" ]; then
        print_info "Adding tap: ${tap_name}"
        if brew_cmd tap | grep -q "^${tap_name}$"; then
            print_success "Tap ${tap_name} already added"
        else
            brew_cmd tap "${tap_name}" || print_warning "Failed to add tap ${tap_name}"
        fi
    fi
}

# Install a single formula
install_formula() {
    local formula="$1"

    # Check if already installed
    if brew_cmd list "${formula}" &> /dev/null; then
        print_success "${formula} is already installed"
        return 0
    fi

    print_info "Installing ${formula}..."

    if brew_cmd install "${formula}"; then
        print_success "${formula} installed successfully"
        return 0
    else
        print_error "Failed to install ${formula}"
        return 1
    fi
}

# Install tool from tools.yaml definition
install_from_yaml() {
    local tool_name="$1"
    local brew_value
    local description
    local install_failed=0

    # Get tool info
    brew_value=$(get_tool_info "${tool_name}" "brew")
    description=$(get_tool_info "${tool_name}" "description")

    print_header "Installing ${tool_name}"

    if [ "${description}" != "null" ]; then
        echo "${description}"
        echo ""
    fi

    # Add tap if needed
    add_tap "${tool_name}"

    # Parse brew value - can be single formula or array
    if [[ "${brew_value}" == "- "* ]]; then
        # Array of formulas
        print_info "Installing multiple packages for ${tool_name}..."
        echo ""

        while IFS= read -r line; do
            if [[ "${line}" == "- "* ]]; then
                formula="${line#- }"
                install_formula "${formula}" || install_failed=1
            fi
        done <<< "${brew_value}"
    else
        # Single formula
        install_formula "${brew_value}" || install_failed=1
    fi

    # Run post-install commands if any
    local post_install
    post_install=$(get_tool_info "${tool_name}" "post_install")

    if [ "${post_install}" != "null" ] && [ -n "${post_install}" ]; then
        print_info "Running post-install configuration..."
        eval "${post_install}" || print_warning "Post-install script failed"
    fi

    return ${install_failed}
}

# Install tool directly as brew formula
install_direct_formula() {
    local formula="$1"

    print_header "Installing ${formula} (direct brew formula)"

    install_formula "${formula}"
}

# Install a single tool (check yaml first, then direct)
install_tool() {
    local tool_name="$1"

    # Check if tool is defined in tools.yaml
    if tool_exists_in_yaml "${tool_name}"; then
        install_from_yaml "${tool_name}"
    else
        # Treat as direct brew formula
        install_direct_formula "${tool_name}"
    fi
}

# Main function
main() {
    print_header "Homebrew Development Tools Installer"

    # Check prerequisites
    check_homebrew

    # Parse arguments
    if [ $# -eq 0 ]; then
        print_error "Usage: $0 <tool-name> [tool-name...]"
        echo ""
        echo "Install tools defined in tools.yaml or any Homebrew formula."
        echo ""

        if [ -f "${TOOLS_CONFIG}" ] && has_yq; then
            echo "Available predefined tools (from tools.yaml):"
            yq eval '.tools | keys | .[]' "${TOOLS_CONFIG}" 2>/dev/null | sed 's/^/  - /' || true
            echo ""
        fi

        echo "You can also install any Homebrew formula directly:"
        echo "  $0 <any-brew-formula>"
        echo ""
        echo "Examples:"
        echo "  $0 golang                    # From tools.yaml"
        echo "  $0 k8s-tools                 # From tools.yaml (group)"
        echo "  $0 neovim ripgrep            # Direct brew formulas"
        echo "  $0 golang nodejs terraform   # Mix of both"
        exit 1
    fi

    # Track overall status
    local overall_failed=0
    local total_tools=$#
    local successful=0

    # Install each requested tool
    for tool_name in "$@"; do
        if install_tool "${tool_name}"; then
            ((successful++)) || true
        else
            overall_failed=1
        fi
        echo ""
    done

    # Print summary
    print_header "Installation Summary"
    echo "Requested: ${total_tools} tool(s)"
    echo "Successful: ${successful} tool(s)"

    if [ ${overall_failed} -eq 0 ]; then
        echo ""
        print_success "All tools installed successfully!"
        echo ""
        echo "Note: Homebrew environment is automatically loaded in new shells."
        echo "For current shell, run:"
        echo "  eval \"\$(brew shellenv)\""
        echo ""
        exit 0
    else
        echo ""
        print_warning "Some tools failed to install"
        echo ""
        echo "You can:"
        echo "  1. Check the error messages above"
        echo "  2. Retry installation: $0 $*"
        echo "  3. Install manually: brew install <formula>"
        echo ""
        exit 1
    fi
}

# Run main function
main "$@"
