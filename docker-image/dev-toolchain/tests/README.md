# Dev-Toolchain Test Suite

Comprehensive test suite for the dev-toolchain Docker image.

## Overview

This test suite validates:
- **Basic functionality**: Image build, container startup, environment configuration
- **User-init scripts**: Custom initialization script execution
- **Docker Compose**: Multi-container deployment with DinD sidecar
- **Environment variables**: Homebrew, DOCKER_HOST, custom variables
- **File system**: Directory structure, configuration files

## Directory Structure

```
tests/
├── README.md                      # This file
├── run-tests.sh                   # Unified test runner
├── docker-compose.test.yml        # Docker Compose test configuration
└── fixtures/
    └── user-scripts/              # Test user-init scripts
        ├── 00-setup-env.sh        # Environment setup test
        ├── 10-create-workspace.sh # Workspace creation test
        └── 20-verify.sh           # Verification test
```

## Quick Start

### Run All Tests

```bash
cd /path/to/dev-toolchain
./tests/run-tests.sh
```

### Run Specific Test

```bash
# Basic functionality only
./tests/run-tests.sh basic

# User-init functionality only
./tests/run-tests.sh user-init

# Docker Compose deployment only
./tests/run-tests.sh docker-compose
```

## Test Details

### 1. Basic Functionality Test

**What it tests:**
- Docker image builds successfully
- Container starts and runs
- s6-overlay init system is running
- Environment variables are set correctly
- `/etc/profile.d/99-dev-tools-env.sh` is created
- `.bashrc` sources the profile.d script
- Homebrew environment variables are present

**Usage:**
```bash
./tests/run-tests.sh basic
```

**Expected behavior:**
- Container starts successfully
- `DOCKER_HOST` is set to `tcp://localhost:2375`
- `HOMEBREW_PREFIX` is set to `/home/linuxbrew/.linuxbrew`
- s6-overlay supervisor is running
- Environment script exists and is sourced

### 2. User-Init Test

**What it tests:**
- User-init script mechanism (`cont-init.d/99-user-init`)
- Custom scripts in `/usr/local/lib/dev-tools/user-scripts/` are executed
- Scripts run in alphabetical order
- Scripts can modify `/etc/profile.d/99-dev-tools-env.sh`
- Scripts can create workspace structure
- Environment variables set by scripts are available in shells

**Usage:**
```bash
./tests/run-tests.sh user-init
```

**Test fixtures used:**
- `00-setup-env.sh`: Adds custom environment variables
- `10-create-workspace.sh`: Creates `/code/test-project` structure
- `20-verify.sh`: Verifies setup was successful

**Expected behavior:**
- All three user scripts execute in order
- `TEST_PROJECT`, `TEST_ENV`, `CUSTOM_MESSAGE` variables are set
- `/code/test-project/` directory structure is created
- `README.md` and `hello.sh` files are created
- `hello.sh` is executable and runs successfully

### 3. Docker Compose Test

**What it tests:**
- Multi-container deployment
- Docker-in-Docker (DinD) sidecar connectivity
- Volume mounting
- Network connectivity between services
- Docker client can communicate with DinD daemon

**Usage:**
```bash
./tests/run-tests.sh docker-compose
```

**Services:**
- `dev-toolchain`: Main development container
- `dind`: Docker-in-Docker daemon (sidecar)

**Expected behavior:**
- Both services start successfully
- `dev-toolchain` can execute `docker` commands via DinD
- Volumes `dev-code`, `dev-data`, `dind-storage` are created
- SSH port 2222 is exposed
- `INSTALL_PACKAGES` environment variable triggers package installation

## Test Fixtures

### User Scripts

Located in `tests/fixtures/user-scripts/`, these scripts demonstrate and test the user-init functionality:

#### `00-setup-env.sh`
Adds custom environment variables to `/etc/profile.d/99-dev-tools-env.sh`:
- `TEST_PROJECT=dev-toolchain-test`
- `TEST_ENV=local-docker`
- `CUSTOM_MESSAGE=Hello from user-init script!`

#### `10-create-workspace.sh`
Creates a sample workspace structure:
```
/code/
├── test-project/
│   ├── README.md
│   ├── src/
│   │   └── hello.sh
│   ├── docs/
│   ├── scripts/
│   └── config/
└── shared/
    ├── tools/
    └── data/
```

#### `20-verify.sh`
Verifies that previous scripts executed successfully by checking:
- Environment variables are in config file
- Directories were created
- Files exist and have correct permissions

## Writing Your Own Tests

### Test Function Template

```bash
test_my_feature() {
    print_header "Test: My Feature"
    
    local container_name="dev-toolchain-test-my-feature"
    local test_result="pass"
    
    # Cleanup before test
    cleanup_container "$container_name"
    
    # Setup test
    print_test_header "Setting up test"
    docker run -d --name "$container_name" "${IMAGE_NAME}:${IMAGE_TAG}"
    
    # Run assertions
    print_test_header "Checking feature X"
    if ! assert_file_exists "$container_name" "/path/to/file"; then
        test_result="fail"
    fi
    
    # Cleanup after test
    cleanup_container "$container_name"
    
    # Record result
    record_test "my-feature" "$test_result"
    
    if [ "$test_result" = "pass" ]; then
        print_success "My feature test PASSED"
        return 0
    else
        print_error "My feature test FAILED"
        return 1
    fi
}
```

### Available Assertion Helpers

- `assert_equals expected actual [message]`
- `assert_contains haystack needle [message]`
- `assert_file_exists container filepath [message]`
- `assert_dir_exists container dirpath [message]`
- `assert_command_success container command [message]`

### Helper Functions

- `print_info "message"` - Print info message
- `print_success "message"` - Print success message
- `print_error "message"` - Print error message
- `print_warning "message"` - Print warning message
- `print_header "title"` - Print section header
- `print_test_header "title"` - Print test subsection header
- `cleanup_container "name"` - Stop and remove container
- `cleanup_compose` - Stop and remove compose services

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Dev-Toolchain

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run tests
        run: |
          cd kangumi/docker-image/dev-toolchain
          ./tests/run-tests.sh
```

### GitLab CI Example

```yaml
test:dev-toolchain:
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd kangumi/docker-image/dev-toolchain
    - ./tests/run-tests.sh
```

## Troubleshooting

### Tests Hang or Timeout

**Issue:** Container doesn't start or tests wait forever

**Solution:**
- Check Docker daemon is running: `docker info`
- Increase wait times in test scripts (sleep commands)
- Check container logs: `docker logs <container-name>`

### User-Init Scripts Not Executing

**Issue:** User scripts don't run or environment variables not set

**Solution:**
- Verify scripts are executable: `chmod +x tests/fixtures/user-scripts/*.sh`
- Check mount path is correct: `/usr/local/lib/dev-tools/user-scripts`
- Check container logs for init errors: `docker logs <container-name> 2>&1 | grep user-init`

### Docker Compose Test Fails

**Issue:** DinD connectivity fails or services don't start

**Solution:**
- Ensure Docker Compose is installed: `docker compose version`
- Check if ports are already in use: `lsof -i :2222`
- Verify privileged mode is allowed for DinD
- Check compose logs: `docker compose -f tests/docker-compose.test.yml logs`

### Environment Variables Not Available

**Issue:** Variables set in Dockerfile ENV or init scripts are missing

**Solution:**
- Verify `/etc/profile.d/99-dev-tools-env.sh` exists in container
- Check `.bashrc` sources the script: `docker exec <container> cat /root/.bashrc`
- Source the script manually: `source /etc/profile.d/99-dev-tools-env.sh`
- Check for typos in variable names

## Development Workflow

### 1. Make Changes to Image
Edit `Dockerfile`, `install-scripts/`, or `cont-init.d/`

### 2. Run Tests Locally
```bash
./tests/run-tests.sh
```

### 3. Test Specific Feature
```bash
# Test only what you changed
./tests/run-tests.sh basic
./tests/run-tests.sh user-init
```

### 4. Add New Tests
- Add test function to `run-tests.sh`
- Add test case to main() switch statement
- Create fixtures in `tests/fixtures/` if needed

### 5. Verify All Tests Pass
```bash
./tests/run-tests.sh all
```

## Best Practices

1. **Keep tests isolated**: Each test should clean up after itself
2. **Use meaningful names**: Test names should describe what they test
3. **Wait for initialization**: Allow time for s6-overlay and init scripts
4. **Check logs**: Always verify expected log output
5. **Test edge cases**: Not just happy path
6. **Document fixtures**: Explain what test data does
7. **Keep tests fast**: Optimize wait times, parallelize when possible
8. **Fail fast**: Exit early on critical failures

## Contributing

When adding new features to dev-toolchain:

1. Write tests first (TDD approach)
2. Ensure all existing tests still pass
3. Add documentation for new test cases
4. Update this README if test structure changes
5. Consider CI/CD implications

---

**Questions or issues?** Open an issue or check the project documentation.