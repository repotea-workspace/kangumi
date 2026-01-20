#!/bin/bash
#
# 10-create-workspace.sh - Test script for creating workspace structure
#

echo "=========================================="
echo "Test User Script 2: Create Workspace"
echo "=========================================="

echo "→ Creating workspace directory structure..."

# Create directory structure
mkdir -p /code/test-project/{src,docs,scripts,config}
mkdir -p /code/shared/{tools,data}

echo "✓ Directories created:"
echo "  - /code/test-project/src"
echo "  - /code/test-project/docs"
echo "  - /code/test-project/scripts"
echo "  - /code/test-project/config"
echo "  - /code/shared/tools"
echo "  - /code/shared/data"
echo ""

echo "→ Creating README files..."

cat > /code/test-project/README.md << 'EOF'
# Test Project

This is a test project created by user-init script.

## Directory Structure

- `src/` - Source code
- `docs/` - Documentation
- `scripts/` - Utility scripts
- `config/` - Configuration files

EOF

cat > /code/test-project/src/hello.sh << 'EOF'
#!/bin/bash
echo "Hello from test project!"
echo "TEST_PROJECT: ${TEST_PROJECT}"
echo "TEST_ENV: ${TEST_ENV}"
echo "${CUSTOM_MESSAGE}"
EOF

chmod +x /code/test-project/src/hello.sh

echo "✓ Files created:"
echo "  - /code/test-project/README.md"
echo "  - /code/test-project/src/hello.sh"
echo ""

echo "✓ Workspace setup completed!"
echo ""
