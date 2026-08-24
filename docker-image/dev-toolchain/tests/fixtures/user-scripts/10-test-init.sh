#!/usr/bin/env bash

set -euo pipefail

cat >> /etc/profile.d/99-dev-tools-env.sh <<'EOF'
export TEST_PROJECT=dev-toolchain-test
export TEST_ENV=local-docker
export CUSTOM_MESSAGE='Hello from user-init script!'
EOF

mkdir -p /code/test-project/src
touch /code/test-project/README.md
cat > /code/test-project/src/hello.sh <<'EOF'
#!/usr/bin/env bash
echo "${CUSTOM_MESSAGE}"
EOF
chmod +x /code/test-project/src/hello.sh
