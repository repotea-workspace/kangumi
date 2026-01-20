#!/usr/bin/env bash
#
# user-init.sh - Execute user-provided initialization scripts
#
# This script is called during container initialization (s6-overlay cont-init phase)
# to run any user-provided custom initialization scripts.
#
# User scripts can be provided in two ways:
# 1. Mount scripts to /usr/local/lib/dev-tools/user-scripts/
# 2. Through Helm Chart ConfigMap (in Kubernetes)
#
# Scripts are executed in alphabetical order.

set -euo pipefail

# User scripts directory
USER_SCRIPTS_DIR="/usr/local/lib/dev-tools/user-scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}→${NC} $*"; }
print_success() { echo -e "${GREEN}✓${NC} $*"; }
print_error() { echo -e "${RED}✗${NC} $*" >&2; }
print_warning() { echo -e "${YELLOW}⚠${NC} $*"; }

echo "[user-init] Checking for user initialization scripts..."

# Check if user scripts directory exists
if [ ! -d "${USER_SCRIPTS_DIR}" ]; then
    echo "[user-init] User scripts directory does not exist: ${USER_SCRIPTS_DIR}"
    echo "[user-init] Skipping user initialization"
    exit 0
fi

# Find all executable scripts in the directory
shopt -s nullglob
USER_SCRIPTS=("${USER_SCRIPTS_DIR}"/*.sh)
shopt -u nullglob

# Check if any scripts exist
if [ ${#USER_SCRIPTS[@]} -eq 0 ]; then
    echo "[user-init] No user scripts found in ${USER_SCRIPTS_DIR}"
    echo "[user-init] Skipping user initialization"
    exit 0
fi

# Execute user scripts
echo ""
echo "=========================================="
echo "User Initialization Scripts"
echo "=========================================="
echo "Found ${#USER_SCRIPTS[@]} script(s) in ${USER_SCRIPTS_DIR}"
echo ""

FAILED_SCRIPTS=()
SUCCEEDED_SCRIPTS=()

for script in "${USER_SCRIPTS[@]}"; do
    script_name=$(basename "${script}")

    # Check if script is executable
    if [ ! -x "${script}" ]; then
        print_warning "Script is not executable, making it executable: ${script_name}"
        chmod +x "${script}" || {
            print_error "Failed to make script executable: ${script_name}"
            FAILED_SCRIPTS+=("${script_name}")
            continue
        }
    fi

    echo ""
    print_info "Executing user script: ${script_name}"
    echo "---"

    # Execute the script
    if "${script}"; then
        echo "---"
        print_success "Successfully executed: ${script_name}"
        SUCCEEDED_SCRIPTS+=("${script_name}")
    else
        exit_code=$?
        echo "---"
        print_error "Failed to execute: ${script_name} (exit code: ${exit_code})"
        FAILED_SCRIPTS+=("${script_name}")
    fi
done

# Print summary
echo ""
echo "=========================================="
echo "User Initialization Summary"
echo "=========================================="
echo "Total scripts: ${#USER_SCRIPTS[@]}"
echo "Succeeded: ${#SUCCEEDED_SCRIPTS[@]}"
echo "Failed: ${#FAILED_SCRIPTS[@]}"

if [ ${#SUCCEEDED_SCRIPTS[@]} -gt 0 ]; then
    echo ""
    echo "Succeeded scripts:"
    for script_name in "${SUCCEEDED_SCRIPTS[@]}"; do
        echo "  ✓ ${script_name}"
    done
fi

if [ ${#FAILED_SCRIPTS[@]} -gt 0 ]; then
    echo ""
    echo "Failed scripts:"
    for script_name in "${FAILED_SCRIPTS[@]}"; do
        echo "  ✗ ${script_name}"
    done
    echo ""
    print_warning "Some user scripts failed, but continuing container initialization"
fi

echo ""
echo "[user-init] User initialization completed"
exit 0
