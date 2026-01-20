#!/usr/bin/env bash
#
# run-tests.sh - Unified test runner for dev-toolchain image
#
# Usage:
#   ./tests/run-tests.sh [test-name]
#
# Available tests:
#   basic       - Basic image functionality (build, run, environment)
#   user-init   - User-init script execution
#   docker-compose - Docker Compose deployment
#   all         - Run all tests (default)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
IMAGE_NAME="dev-toolchain"
IMAGE_TAG="test"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Test results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Print helpers
print_info() { echo -e "${BLUE}→${NC} $*"; }
print_success() { echo -e "${GREEN}✓${NC} $*"; }
print_error() { echo -e "${RED}✗${NC} $*" >&2; }
print_warning() { echo -e "${YELLOW}⚠${NC} $*"; }
print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}=========================================="
    echo -e "$*"
    echo -e "==========================================${NC}"
}

print_test_header() {
    echo ""
    echo -e "${BOLD}------------------------------------------"
    echo -e "$*"
    echo -e "------------------------------------------${NC}"
}

# Assertion helpers
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-}"

    if [ "$expected" = "$actual" ]; then
        print_success "${message:-Assertion passed}"
        return 0
    else
        print_error "${message:-Assertion failed}"
        print_error "  Expected: $expected"
        print_error "  Actual:   $actual"
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-}"

    if echo "$haystack" | grep -q "$needle"; then
        print_success "${message:-Contains check passed}"
        return 0
    else
        print_error "${message:-Contains check failed}"
        print_error "  Looking for: $needle"
        print_error "  In: $haystack"
        return 1
    fi
}

assert_file_exists() {
    local container="$1"
    local filepath="$2"
    local message="${3:-File exists: $filepath}"

    if docker exec "$container" test -f "$filepath"; then
        print_success "$message"
        return 0
    else
        print_error "$message (NOT FOUND)"
        return 1
    fi
}

assert_dir_exists() {
    local container="$1"
    local dirpath="$2"
    local message="${3:-Directory exists: $dirpath}"

    if docker exec "$container" test -d "$dirpath"; then
        print_success "$message"
        return 0
    else
        print_error "$message (NOT FOUND)"
        return 1
    fi
}

assert_command_success() {
    local container="$1"
    local command="$2"
    local message="${3:-Command succeeded}"

    if docker exec "$container" bash -c "$command" >/dev/null 2>&1; then
        print_success "$message"
        return 0
    else
        print_error "$message (FAILED)"
        return 1
    fi
}

# Test result tracking
record_test() {
    local test_name="$1"
    local result="$2"

    ((TESTS_RUN++))
    if [ "$result" = "pass" ]; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
}

# Cleanup helpers
cleanup_container() {
    local container="$1"
    docker stop "$container" 2>/dev/null || true
    docker rm "$container" 2>/dev/null || true
}

cleanup_compose() {
    docker compose -f "${SCRIPT_DIR}/docker-compose.test.yml" down -v 2>/dev/null || true
}

# Build image
build_image() {
    print_header "Building Docker Image"
    print_info "Building ${IMAGE_NAME}:${IMAGE_TAG}..."

    if docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" "${PROJECT_DIR}"; then
        print_success "Image built successfully"
        return 0
    else
        print_error "Failed to build image"
        return 1
    fi
}

# Test: Basic functionality
test_basic() {
    print_header "Test: Basic Functionality"

    local container_name="dev-toolchain-test-basic"
    local test_result="pass"

    cleanup_container "$container_name"

    print_test_header "Starting container"
    if ! docker run -d --name "$container_name" "${IMAGE_NAME}:${IMAGE_TAG}"; then
        print_error "Failed to start container"
        record_test "basic" "fail"
        return 1
    fi
    print_success "Container started"

    sleep 5

    print_test_header "Checking environment variables"
    if ! docker exec "$container_name" bash -c 'echo "DOCKER_HOST=$DOCKER_HOST"'; then
        test_result="fail"
    fi

    print_test_header "Checking Homebrew environment"
    if ! docker exec "$container_name" bash -c 'echo "HOMEBREW_PREFIX=$HOMEBREW_PREFIX"'; then
        test_result="fail"
    fi

    print_test_header "Checking /etc/profile.d/99-dev-tools-env.sh"
    if ! assert_file_exists "$container_name" "/etc/profile.d/99-dev-tools-env.sh"; then
        test_result="fail"
    fi

    print_test_header "Checking .bashrc sources profile.d"
    if ! docker exec "$container_name" grep -q "/etc/profile.d/99-dev-tools-env.sh" /root/.bashrc; then
        print_error ".bashrc does not source profile.d script"
        test_result="fail"
    else
        print_success ".bashrc sources profile.d script"
    fi

    print_test_header "Checking s6-overlay is running"
    if ! docker exec "$container_name" pgrep -f s6-supervise >/dev/null; then
        print_error "s6-overlay not running"
        test_result="fail"
    else
        print_success "s6-overlay is running"
    fi

    cleanup_container "$container_name"
    record_test "basic" "$test_result"

    if [ "$test_result" = "pass" ]; then
        print_success "Basic test PASSED"
        return 0
    else
        print_error "Basic test FAILED"
        return 1
    fi
}

# Test: User-init functionality
test_user_init() {
    print_header "Test: User-Init Functionality"

    local container_name="dev-toolchain-test-user-init"
    local test_result="pass"
    local user_scripts_dir="${SCRIPT_DIR}/fixtures/user-scripts"

    cleanup_container "$container_name"

    print_test_header "Starting container with user scripts"
    if ! docker run -d \
        --name "$container_name" \
        -v "${user_scripts_dir}:/usr/local/lib/dev-tools/user-scripts:ro" \
        "${IMAGE_NAME}:${IMAGE_TAG}"; then
        print_error "Failed to start container"
        record_test "user-init" "fail"
        return 1
    fi
    print_success "Container started"

    print_info "Waiting for initialization (10 seconds)..."
    sleep 10

    print_test_header "Checking container logs for user-init"
    if ! docker logs "$container_name" 2>&1 | grep -q "user-init"; then
        print_warning "user-init logs not found (may not have run)"
        test_result="fail"
    else
        print_success "user-init logs found"
    fi

    print_test_header "Checking environment variables from user scripts"
    if ! docker exec "$container_name" bash -c 'source /etc/profile.d/99-dev-tools-env.sh && [ -n "$TEST_PROJECT" ]'; then
        print_error "TEST_PROJECT not set"
        test_result="fail"
    else
        local test_project=$(docker exec "$container_name" bash -c 'source /etc/profile.d/99-dev-tools-env.sh && echo $TEST_PROJECT')
        assert_equals "dev-toolchain-test" "$test_project" "TEST_PROJECT value" || test_result="fail"
    fi

    print_test_header "Checking workspace created by user scripts"
    assert_dir_exists "$container_name" "/code/test-project" || test_result="fail"
    assert_dir_exists "$container_name" "/code/test-project/src" || test_result="fail"
    assert_file_exists "$container_name" "/code/test-project/README.md" || test_result="fail"
    assert_file_exists "$container_name" "/code/test-project/src/hello.sh" || test_result="fail"

    print_test_header "Testing hello.sh script execution"
    if ! docker exec "$container_name" bash -c 'source /etc/profile.d/99-dev-tools-env.sh && /code/test-project/src/hello.sh'; then
        print_error "hello.sh execution failed"
        test_result="fail"
    else
        print_success "hello.sh executed successfully"
    fi

    cleanup_container "$container_name"
    record_test "user-init" "$test_result"

    if [ "$test_result" = "pass" ]; then
        print_success "User-init test PASSED"
        return 0
    else
        print_error "User-init test FAILED"
        return 1
    fi
}

# Test: Docker Compose deployment
test_docker_compose() {
    print_header "Test: Docker Compose Deployment"

    local test_result="pass"
    local compose_file="${SCRIPT_DIR}/docker-compose.test.yml"

    cleanup_compose

    print_test_header "Starting services with docker compose"
    if ! docker compose -f "$compose_file" up -d; then
        print_error "Failed to start services"
        record_test "docker-compose" "fail"
        return 1
    fi
    print_success "Services started"

    print_info "Waiting for services to initialize (15 seconds)..."
    sleep 15

    print_test_header "Checking dev-toolchain service"
    if ! docker compose -f "$compose_file" ps | grep -q "dev-toolchain.*running"; then
        print_error "dev-toolchain service not running"
        test_result="fail"
    else
        print_success "dev-toolchain service is running"
    fi

    print_test_header "Checking DinD service"
    if ! docker compose -f "$compose_file" ps | grep -q "dind.*running"; then
        print_error "DinD service not running"
        test_result="fail"
    else
        print_success "DinD service is running"
    fi

    print_test_header "Testing Docker connectivity from dev-toolchain"
    if ! docker compose -f "$compose_file" exec -T dev-toolchain docker version >/dev/null 2>&1; then
        print_error "Cannot connect to Docker daemon"
        test_result="fail"
    else
        print_success "Docker client can connect to DinD daemon"
    fi

    print_test_header "Checking volumes"
    if ! docker volume ls | grep -q "dev-code"; then
        print_error "dev-code volume not found"
        test_result="fail"
    else
        print_success "dev-code volume exists"
    fi

    cleanup_compose
    record_test "docker-compose" "$test_result"

    if [ "$test_result" = "pass" ]; then
        print_success "Docker Compose test PASSED"
        return 0
    else
        print_error "Docker Compose test FAILED"
        return 1
    fi
}

# Print summary
print_summary() {
    print_header "Test Summary"

    echo ""
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}${BOLD}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
        echo ""
        return 1
    else
        echo -e "${GREEN}${BOLD}All tests passed! ✓${NC}"
        echo ""
        return 0
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [test-name]

Available tests:
  basic           - Basic image functionality
  user-init       - User-init script execution
  docker-compose  - Docker Compose deployment
  all             - Run all tests (default)

Examples:
  $0              # Run all tests
  $0 basic        # Run only basic test
  $0 user-init    # Run only user-init test

EOF
}

# Main
main() {
    local test_target="${1:-all}"

    if [ "$test_target" = "-h" ] || [ "$test_target" = "--help" ]; then
        show_usage
        exit 0
    fi

    print_header "Dev-Toolchain Test Suite"
    echo "Test target: $test_target"

    # Build image first
    if ! build_image; then
        print_error "Image build failed, cannot run tests"
        exit 1
    fi

    # Run tests
    case "$test_target" in
        basic)
            test_basic
            ;;
        user-init)
            test_user_init
            ;;
        docker-compose|compose)
            test_docker_compose
            ;;
        all)
            test_basic
            test_user_init
            test_docker_compose
            ;;
        *)
            print_error "Unknown test: $test_target"
            echo ""
            show_usage
            exit 1
            ;;
    esac

    # Print summary and exit
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
