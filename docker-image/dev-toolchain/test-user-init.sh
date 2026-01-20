#!/usr/bin/env bash
#
# test-user-init.sh - Test user-init functionality locally
#
# This script builds the dev-toolchain image and tests the user-init script feature

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="dev-toolchain"
IMAGE_TAG="test-user-init"
CONTAINER_NAME="dev-toolchain-test-user-init"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}→${NC} $*"; }
print_success() { echo -e "${GREEN}✓${NC} $*"; }
print_error() { echo -e "${RED}✗${NC} $*" >&2; }
print_warning() { echo -e "${YELLOW}⚠${NC} $*"; }
print_header() {
    echo ""
    echo "=========================================="
    echo "$*"
    echo "=========================================="
}

# Cleanup function
cleanup() {
    print_info "Cleaning up..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
}

# Trap cleanup on exit
trap cleanup EXIT

print_header "Dev-Toolchain User-Init Test"

# Step 1: Build image
print_header "Step 1: Building Docker Image"
print_info "Building ${IMAGE_NAME}:${IMAGE_TAG}..."
if docker build -t ${IMAGE_NAME}:${IMAGE_TAG} "${SCRIPT_DIR}"; then
    print_success "Image built successfully"
else
    print_error "Failed to build image"
    exit 1
fi

# Step 2: Run container with user scripts
print_header "Step 2: Running Container with User Scripts"
print_info "Starting container: ${CONTAINER_NAME}"
print_info "Mounting user scripts from: ${SCRIPT_DIR}/test-user-scripts"

if docker run -d \
    --name ${CONTAINER_NAME} \
    -v "${SCRIPT_DIR}/test-user-scripts:/usr/local/lib/dev-tools/user-scripts:ro" \
    ${IMAGE_NAME}:${IMAGE_TAG}; then
    print_success "Container started"
else
    print_error "Failed to start container"
    exit 1
fi

# Wait for container to initialize
print_info "Waiting for container initialization (10 seconds)..."
sleep 10

# Step 3: Check logs
print_header "Step 3: Checking Container Logs"
print_info "Looking for user-init execution logs..."
echo ""

docker logs ${CONTAINER_NAME} 2>&1 | grep -A 200 "user-init" || {
    print_warning "No user-init logs found, showing all logs:"
    docker logs ${CONTAINER_NAME}
}

# Step 4: Verify execution
print_header "Step 4: Verifying User-Init Results"

echo ""
print_info "Checking if environment variables were set..."
if docker exec ${CONTAINER_NAME} bash -c 'source /etc/profile.d/99-dev-tools-env.sh && [ -n "$TEST_PROJECT" ]'; then
    print_success "Environment variables configured"
    docker exec ${CONTAINER_NAME} bash -c 'source /etc/profile.d/99-dev-tools-env.sh && echo "  TEST_PROJECT=$TEST_PROJECT"'
    docker exec ${CONTAINER_NAME} bash -c 'source /etc/profile.d/99-dev-tools-env.sh && echo "  TEST_ENV=$TEST_ENV"'
    docker exec ${CONTAINER_NAME} bash -c 'source /etc/profile.d/99-dev-tools-env.sh && echo "  CUSTOM_MESSAGE=$CUSTOM_MESSAGE"'
else
    print_error "Environment variables not found"
fi

echo ""
print_info "Checking if workspace was created..."
if docker exec ${CONTAINER_NAME} [ -d /code/test-project ]; then
    print_success "Workspace directory exists"
    docker exec ${CONTAINER_NAME} ls -la /code/test-project/
else
    print_error "Workspace directory not found"
fi

echo ""
print_info "Checking if README was created..."
if docker exec ${CONTAINER_NAME} [ -f /code/test-project/README.md ]; then
    print_success "README.md exists"
    echo ""
    echo "Content:"
    docker exec ${CONTAINER_NAME} cat /code/test-project/README.md | sed 's/^/  /'
else
    print_error "README.md not found"
fi

echo ""
print_info "Testing hello.sh script..."
if docker exec ${CONTAINER_NAME} [ -x /code/test-project/src/hello.sh ]; then
    print_success "hello.sh exists and is executable"
    echo ""
    echo "Executing hello.sh:"
    docker exec ${CONTAINER_NAME} bash -c 'source /etc/profile.d/99-dev-tools-env.sh && /code/test-project/src/hello.sh' | sed 's/^/  /'
else
    print_error "hello.sh not found or not executable"
fi

# Step 5: Interactive shell (optional)
print_header "Step 5: Test Summary"

echo ""
print_success "User-init test completed!"
echo ""
echo "Container is still running: ${CONTAINER_NAME}"
echo ""
echo "To inspect manually, run:"
echo "  docker exec -it ${CONTAINER_NAME} bash"
echo ""
echo "To view logs again:"
echo "  docker logs ${CONTAINER_NAME}"
echo ""
echo "To cleanup:"
echo "  docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}"
echo ""

# Ask if user wants to enter the container
read -p "Do you want to enter the container for manual inspection? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Entering container..."
    docker exec -it ${CONTAINER_NAME} bash
fi

print_info "Test complete. Container will be cleaned up on exit."
