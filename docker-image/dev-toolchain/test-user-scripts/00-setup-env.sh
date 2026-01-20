#!/bin/bash
#
# 00-setup-env.sh - Test script for environment setup
#

echo "=========================================="
echo "Test User Script 1: Environment Setup"
echo "=========================================="

echo "→ Setting up custom environment variables..."

# Add custom environment variables
cat >> /etc/profile.d/99-dev-tools-env.sh << 'EOF'

# Test Custom Environment
export TEST_PROJECT="dev-toolchain-test"
export TEST_ENV="local-docker"
export CUSTOM_MESSAGE="Hello from user-init script!"
EOF

echo "✓ Environment variables configured"
echo ""
echo "Added variables:"
echo "  - TEST_PROJECT=dev-toolchain-test"
echo "  - TEST_ENV=local-docker"
echo "  - CUSTOM_MESSAGE=Hello from user-init script!"
echo ""
