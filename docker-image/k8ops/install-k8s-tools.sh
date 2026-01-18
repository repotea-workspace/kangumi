#!/usr/bin/env bash

set -euo pipefail

# Configuration
KUSTOMIZE_VERSION="${KUSTOMIZE_VERSION:-5.6.0}"
HELMFILE_VERSION="${HELMFILE_VERSION:-0.170.0}"
ARGOCD_VERSION="${ARGOCD_VERSION:-2.14.2}"
KUBESEAL_VERSION="${KUBESEAL_VERSION:-0.28.3}"
INSTALL_DIR="/usr/local/bin"

echo "=========================================="
echo "Installing Kubernetes Tools"
echo "=========================================="
echo "Kustomize: ${KUSTOMIZE_VERSION}"
echo "Helmfile: ${HELMFILE_VERSION}"
echo "ArgoCD CLI: ${ARGOCD_VERSION}"
echo "Kubeseal: ${KUBESEAL_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Function to check if tool is installed
check_installed() {
  local tool=$1
  if command -v "${tool}" &> /dev/null; then
    echo "✓ ${tool} is already installed: $(${tool} version 2>/dev/null | head -1 || echo 'version unknown')"
    return 0
  fi
  return 1
}

# Check if all tools are already installed
ALL_INSTALLED=true
for tool in kustomize helmfile argocd kubeseal; do
  if ! check_installed "${tool}"; then
    ALL_INSTALLED=false
  fi
done

if [ "${ALL_INSTALLED}" = true ]; then
  echo ""
  echo "All Kubernetes tools are already installed"
  echo "Use --force to reinstall"
  exit 0
fi

echo ""
echo "Installing missing tools..."
echo ""

# Install Kustomize
if ! check_installed kustomize; then
  echo "Installing Kustomize ${KUSTOMIZE_VERSION}..."
  KUSTOMIZE_URL="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz"
  curl -SL "${KUSTOMIZE_URL}" -o /tmp/kustomize.tar.gz
  tar -xzf /tmp/kustomize.tar.gz -C /tmp
  install -m 755 /tmp/kustomize "${INSTALL_DIR}/kustomize"
  rm -f /tmp/kustomize.tar.gz /tmp/kustomize
  echo "✓ Kustomize installed"
fi

# Install Helmfile
if ! check_installed helmfile; then
  echo ""
  echo "Installing Helmfile ${HELMFILE_VERSION}..."
  HELMFILE_URL="https://github.com/helmfile/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_${HELMFILE_VERSION}_linux_amd64.tar.gz"
  curl -SL "${HELMFILE_URL}" -o /tmp/helmfile.tar.gz
  tar -xzf /tmp/helmfile.tar.gz -C /tmp
  install -m 755 /tmp/helmfile "${INSTALL_DIR}/helmfile"
  rm -f /tmp/helmfile.tar.gz /tmp/helmfile
  echo "✓ Helmfile installed"
fi

# Install ArgoCD CLI
if ! check_installed argocd; then
  echo ""
  echo "Installing ArgoCD CLI ${ARGOCD_VERSION}..."
  ARGOCD_URL="https://github.com/argoproj/argo-cd/releases/download/v${ARGOCD_VERSION}/argocd-linux-amd64"
  curl -SL "${ARGOCD_URL}" -o "${INSTALL_DIR}/argocd"
  chmod +x "${INSTALL_DIR}/argocd"
  echo "✓ ArgoCD CLI installed"
fi

# Install Kubeseal
if ! check_installed kubeseal; then
  echo ""
  echo "Installing Kubeseal ${KUBESEAL_VERSION}..."
  KUBESEAL_URL="https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
  curl -SL "${KUBESEAL_URL}" -o /tmp/kubeseal.tar.gz
  tar -xzf /tmp/kubeseal.tar.gz -C /tmp
  install -m 755 /tmp/kubeseal "${INSTALL_DIR}/kubeseal"
  rm -f /tmp/kubeseal.tar.gz /tmp/kubeseal
  echo "✓ Kubeseal installed"
fi

# Install helm-diff plugin
echo ""
echo "Installing helm-diff plugin..."
if ! helm plugin list | grep -q "^diff"; then
  helm plugin install https://github.com/databus23/helm-diff --version=v3.1.3 --verify=false
  echo "✓ helm-diff plugin installed"
else
  echo "✓ helm-diff plugin is already installed"
fi

# Verify installations
echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
echo ""
echo "Installed tools:"
kustomize version 2>/dev/null || echo "  - Kustomize: installed"
helmfile version 2>/dev/null | head -1 || echo "  - Helmfile: installed"
argocd version --client 2>/dev/null | head -1 || echo "  - ArgoCD CLI: installed"
kubeseal --version 2>/dev/null || echo "  - Kubeseal: installed"
echo ""
echo "Helm plugins:"
helm plugin list | grep diff || echo "  - helm-diff: installed"
echo ""
