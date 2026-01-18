#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-dev-toolchain}"
IMAGE_TAG="${IMAGE_TAG:-local-test}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "==================================="
echo "Building dev-toolchain (DinD sidecar mode)"
echo "==================================="
echo "Image: ${FULL_IMAGE}"
echo "Context: ${SCRIPT_DIR}"
echo ""

# Build the image
docker build \
  --progress=plain \
  --tag "${FULL_IMAGE}" \
  "${SCRIPT_DIR}"

echo ""
echo "==================================="
echo "Build completed successfully!"
echo "==================================="
echo ""
echo "Image: ${FULL_IMAGE}"
echo ""
echo "Next steps:"
echo "  1. Test the image:"
echo "     docker run -it --rm ${FULL_IMAGE} bash"
echo ""
echo "  2. Test with DinD sidecar (Docker Compose recommended):"
echo "     docker compose -f docker-compose.test.yml up -d"
echo "     docker exec -it dev-test bash"
echo ""
echo "  3. Test SSH access:"
echo "     docker run -d --name dev-test -p 2222:22 ${FULL_IMAGE}"
echo "     # Add your SSH key first:"
echo "     docker exec dev-test mkdir -p /root/.ssh"
echo "     docker exec dev-test sh -c 'echo \"YOUR_SSH_PUBLIC_KEY\" >> /root/.ssh/authorized_keys'"
echo "     ssh -p 2222 root@localhost"
echo ""
echo "  4. Test install scripts:"
echo "     docker exec -it dev-test /opt/install-scripts/install-all.sh --help"
echo "     docker exec -it dev-test /opt/install-scripts/install-nodejs.sh"
echo ""
echo "  5. Clean up:"
echo "     docker compose -f docker-compose.test.yml down -v"
echo ""
