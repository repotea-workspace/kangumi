#!/usr/bin/env bash

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Configuration
KUBECTL_VERSION="${KUBECTL_VERSION:-1.35.0}"
HELM_VERSION="${HELM_VERSION:-4.0.5}"
HELM_DIFF_VERSION="${HELM_DIFF_VERSION:-3.14.1}"
HELMFILE_VERSION="${HELMFILE_VERSION:-1.2.3}"
KUSTOMIZE_VERSION="${KUSTOMIZE_VERSION:-5.8.0}"
ARGOCD_VERSION="${ARGOCD_VERSION:-3.2.5}"
KUBESEAL_VERSION="${KUBESEAL_VERSION:-0.34.0}"
INSTALL_DIR="/usr/local/bin"

print_header "Installing Kubernetes Tools"
echo "Kubectl: ${KUBECTL_VERSION}"
echo "Helm: ${HELM_VERSION}"
echo "Helm Diff Plugin: ${HELM_DIFF_VERSION}"
echo "Kustomize: ${KUSTOMIZE_VERSION}"
echo "Helmfile: ${HELMFILE_VERSION}"
echo "ArgoCD CLI: ${ARGOCD_VERSION}"
echo "Kubeseal: ${KUBESEAL_VERSION}"
echo "Install Directory: ${INSTALL_DIR}"
echo ""

# Function to check if tool is installed (command exists)
check_tool_installed() {
  local tool=$1
  if command -v "${tool}" &> /dev/null; then
    print_success "${tool} is already installed: $(${tool} version 2>/dev/null | head -1 || echo 'version unknown')"
    return 0
  fi
  return 1
}

# Create combined version string for marker
COMBINED_VERSION="${KUBECTL_VERSION}:${HELM_VERSION}:${KUSTOMIZE_VERSION}:${HELMFILE_VERSION}:${ARGOCD_VERSION}:${KUBESEAL_VERSION}"

# Check if already installed with same versions via marker
if check_installed "k8s-tools" "${COMBINED_VERSION}"; then
  ALL_INSTALLED=true
  for tool in kubectl helm kustomize helmfile argocd kubeseal; do
    if ! check_tool_installed "${tool}"; then
      ALL_INSTALLED=false
    fi
  done

  if [ "${ALL_INSTALLED}" = true ]; then
    echo ""
    print_success "All Kubernetes tools are already installed"
    exit 0
  else
    print_warning "Some tools are missing, reinstalling..."
  fi
fi

echo ""
echo "Installing missing tools..."
echo ""

# Install Kubectl
if ! check_tool_installed kubectl; then
  print_info "Installing Kubectl ${KUBECTL_VERSION}..."
  KUBECTL_URL="https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  curl -SL "${KUBECTL_URL}" -o "${INSTALL_DIR}/kubectl"
  chmod +x "${INSTALL_DIR}/kubectl"
  print_success "Kubectl installed"
fi

# Install Helm
if ! check_tool_installed helm; then
  echo ""
  print_info "Installing Helm ${HELM_VERSION}..."
  HELM_URL="https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz"
  curl -SL "${HELM_URL}" -o /tmp/helm.tar.gz
  tar -xzf /tmp/helm.tar.gz -C /tmp
  install -m 755 /tmp/linux-amd64/helm "${INSTALL_DIR}/helm"
  rm -rf /tmp/helm.tar.gz /tmp/linux-amd64
  print_success "Helm installed"
fi

# Install Kustomize
if ! check_tool_installed kustomize; then
  print_info "Installing Kustomize ${KUSTOMIZE_VERSION}..."
  KUSTOMIZE_URL="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz"
  curl -SL "${KUSTOMIZE_URL}" -o /tmp/kustomize.tar.gz
  tar -xzf /tmp/kustomize.tar.gz -C /tmp
  install -m 755 /tmp/kustomize "${INSTALL_DIR}/kustomize"
  rm -f /tmp/kustomize.tar.gz /tmp/kustomize
  print_success "Kustomize installed"
fi

# Install Helmfile
if ! check_tool_installed helmfile; then
  echo ""
  print_info "Installing Helmfile ${HELMFILE_VERSION}..."
  HELMFILE_URL="https://github.com/helmfile/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_${HELMFILE_VERSION}_linux_amd64.tar.gz"
  curl -SL "${HELMFILE_URL}" -o /tmp/helmfile.tar.gz
  tar -xzf /tmp/helmfile.tar.gz -C /tmp
  install -m 755 /tmp/helmfile "${INSTALL_DIR}/helmfile"
  rm -f /tmp/helmfile.tar.gz /tmp/helmfile
  print_success "Helmfile installed"
fi

# Install ArgoCD CLI
if ! check_tool_installed argocd; then
  echo ""
  print_info "Installing ArgoCD CLI ${ARGOCD_VERSION}..."
  ARGOCD_URL="https://github.com/argoproj/argo-cd/releases/download/v${ARGOCD_VERSION}/argocd-linux-amd64"
  curl -SL "${ARGOCD_URL}" -o "${INSTALL_DIR}/argocd"
  chmod +x "${INSTALL_DIR}/argocd"
  print_success "ArgoCD CLI installed"
fi

# Install Kubeseal
if ! check_tool_installed kubeseal; then
  echo ""
  print_info "Installing Kubeseal ${KUBESEAL_VERSION}..."
  KUBESEAL_URL="https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
  curl -SL "${KUBESEAL_URL}" -o /tmp/kubeseal.tar.gz
  tar -xzf /tmp/kubeseal.tar.gz -C /tmp
  install -m 755 /tmp/kubeseal "${INSTALL_DIR}/kubeseal"
  rm -f /tmp/kubeseal.tar.gz /tmp/kubeseal
  print_success "Kubeseal installed"
fi

# Install helm-diff plugin
echo ""
print_info "Installing helm-diff plugin ${HELM_DIFF_VERSION}..."
if ! helm plugin list | grep -q "^diff"; then
  helm plugin install https://github.com/databus23/helm-diff --version=v${HELM_DIFF_VERSION} --verify=false
  print_success "helm-diff plugin installed"
else
  print_success "helm-diff plugin is already installed"
fi

# Mark as installed with combined version
mark_installed "k8s-tools" "${COMBINED_VERSION}"

# Verify installations
echo ""
print_header "Installation completed!"
echo ""
echo "Installed tools:"
kubectl version --client 2>/dev/null | head -1 || echo "  - Kubectl: installed"
helm version 2>/dev/null | head -1 || echo "  - Helm: installed"
kustomize version 2>/dev/null || echo "  - Kustomize: installed"
helmfile version 2>/dev/null | head -1 || echo "  - Helmfile: installed"
argocd version --client 2>/dev/null | head -1 || echo "  - ArgoCD CLI: installed"
kubeseal --version 2>/dev/null || echo "  - Kubeseal: installed"
echo ""
echo "Helm plugins:"
helm plugin list | grep diff || echo "  - helm-diff: installed"
echo ""
