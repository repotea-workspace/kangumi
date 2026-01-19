#!/usr/bin/env bash
#
# create-user.sh - Create runtime user with Homebrew access
#
# This script creates a new user and adds them to the brew group,
# allowing them to use Homebrew packages installed by linuxbrew user.
#
# Usage:
#   create-user.sh <username> [uid] [gid]
#
# Examples:
#   create-user.sh foo
#   create-user.sh foo 1000
#   create-user.sh foo 1000 1000

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}→${NC} $*"
}

print_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

# Check if script is run as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

# Parse arguments
USERNAME="${1:-}"
USER_UID="${2:-1000}"
USER_GID="${3:-${USER_UID}}"

if [ -z "${USERNAME}" ]; then
    print_error "Usage: $0 <username> [uid] [gid]"
    echo ""
    echo "Examples:"
    echo "  $0 foo"
    echo "  $0 foo 1000"
    echo "  $0 foo 1000 1000"
    exit 1
fi

# Validate username
if [[ ! "${USERNAME}" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
    print_error "Invalid username: ${USERNAME}"
    echo "Username must start with a lowercase letter or underscore,"
    echo "and contain only lowercase letters, digits, underscores, and hyphens."
    exit 1
fi

print_info "Creating user: ${USERNAME} (UID: ${USER_UID}, GID: ${USER_GID})"

# Check if user already exists
if id "${USERNAME}" &>/dev/null; then
    print_warning "User ${USERNAME} already exists"

    # Ensure user is in brew group
    if groups "${USERNAME}" | grep -q "\bbrew\b"; then
        print_success "User ${USERNAME} is already in brew group"
    else
        print_info "Adding ${USERNAME} to brew group..."
        usermod -aG brew "${USERNAME}"
        print_success "User ${USERNAME} added to brew group"
    fi
else
    # Create user's primary group if needed
    if ! getent group "${USERNAME}" &>/dev/null; then
        print_info "Creating group: ${USERNAME} (GID: ${USER_GID})"
        # Check if GID is already taken
        if getent group "${USER_GID}" &>/dev/null; then
            print_warning "GID ${USER_GID} already exists, using next available GID"
            groupadd "${USERNAME}"
        else
            groupadd -g "${USER_GID}" "${USERNAME}"
        fi
    fi

    # Create user
    print_info "Creating user account..."
    # Check if UID is already taken
    if getent passwd "${USER_UID}" &>/dev/null; then
        print_warning "UID ${USER_UID} already exists, using next available UID"
        useradd -m -g "${USERNAME}" -G brew -s /bin/bash "${USERNAME}"
    else
        useradd -m -u "${USER_UID}" -g "${USERNAME}" -G brew -s /bin/bash "${USERNAME}"
    fi

    # Add sudo privileges
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/dev-users
    chmod 0440 /etc/sudoers.d/dev-users

    print_success "User ${USERNAME} created successfully"
fi

# Setup user's bashrc with Homebrew environment
USER_HOME="/home/${USERNAME}"
BASHRC="${USER_HOME}/.bashrc"

if [ -f "${BASHRC}" ]; then
    # Check if Homebrew config already exists
    if grep -q "Homebrew environment" "${BASHRC}"; then
        print_info "Homebrew configuration already exists in ${BASHRC}"
    else
        print_info "Adding Homebrew configuration to ${BASHRC}..."
        cat >> "${BASHRC}" << 'EOF'

# Homebrew environment
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Aliases for development
alias ll='ls -lah'
alias k='kubectl'
alias d='docker'
alias dc='docker-compose'

# Brew install wrapper (installs as linuxbrew user)
brew-install() {
    sudo -u linuxbrew -H bash -c "eval \"\$(brew shellenv)\" && brew install $*"
}

# Brew upgrade wrapper
brew-upgrade() {
    sudo -u linuxbrew -H bash -c "eval \"\$(brew shellenv)\" && brew upgrade $*"
}

# Brew uninstall wrapper
brew-uninstall() {
    sudo -u linuxbrew -H bash -c "eval \"\$(brew shellenv)\" && brew uninstall $*"
}

# Install dev tools wrapper
dev-install() {
    install-brew-tools.sh "$@"
}
EOF
        print_success "Homebrew configuration added to ${BASHRC}"
    fi
fi

# Set proper ownership
chown -R "${USERNAME}:${USERNAME}" "${USER_HOME}"

# Print summary
echo ""
print_success "User setup complete!"
echo ""
echo "User Information:"
echo "  Username: ${USERNAME}"
echo "  UID:      ${USER_UID}"
echo "  GID:      ${USER_GID}"
echo "  Home:     ${USER_HOME}"
echo "  Groups:   $(groups ${USERNAME})"
echo ""
echo "Homebrew Access:"
echo "  ✓ Can use installed packages (go, node, kubectl, etc.)"
echo "  ✓ Can view package info (brew list, brew info)"
echo "  ✓ Can install packages via: brew-install <package>"
echo "  ✓ Can install dev tools via: dev-install <tool>"
echo ""
echo "Switch to user:"
echo "  su - ${USERNAME}"
echo ""
