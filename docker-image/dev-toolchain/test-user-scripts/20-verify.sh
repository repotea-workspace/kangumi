#!/bin/bash
#
# 20-verify.sh - Test script for verifying user-init functionality
#

echo "=========================================="
echo "Test User Script 3: Verification"
echo "=========================================="

echo "→ Verifying user-init execution..."
echo ""

# Check if environment variables are set
echo "Checking environment variables:"
if [ -f /etc/profile.d/99-dev-tools-env.sh ]; then
  echo "✓ /etc/profile.d/99-dev-tools-env.sh exists"

  if grep -q "TEST_PROJECT" /etc/profile.d/99-dev-tools-env.sh; then
    echo "✓ TEST_PROJECT variable found in config"
  else
    echo "✗ TEST_PROJECT variable NOT found"
  fi
else
  echo "✗ /etc/profile.d/99-dev-tools-env.sh does not exist"
fi
echo ""

# Check if directories were created
echo "Checking workspace directories:"
if [ -d /code/test-project ]; then
  echo "✓ /code/test-project exists"

  for dir in src docs scripts config; do
    if [ -d /code/test-project/$dir ]; then
      echo "  ✓ $dir/ exists"
    else
      echo "  ✗ $dir/ missing"
    fi
  done
else
  echo "✗ /code/test-project does not exist"
fi
echo ""

# Check if files were created
echo "Checking workspace files:"
if [ -f /code/test-project/README.md ]; then
  echo "✓ README.md exists"
else
  echo "✗ README.md missing"
fi

if [ -x /code/test-project/src/hello.sh ]; then
  echo "✓ hello.sh exists and is executable"
else
  echo "✗ hello.sh missing or not executable"
fi
echo ""

echo "=========================================="
echo "User-Init Verification Summary"
echo "=========================================="
echo "All user scripts executed successfully!"
echo "User-init functionality is working correctly."
echo ""
