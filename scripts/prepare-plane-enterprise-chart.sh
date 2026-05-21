#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_DIR="$ROOT_DIR/helm-chart-patches/plane-enterprise"
CHART_DIR="$ROOT_DIR/helm-charts/plane-enterprise"

# shellcheck source=/dev/null
source "$PATCH_DIR/upstream.env"

rm -rf "$CHART_DIR"

helm repo add "$UPSTREAM_REPO_NAME" "$UPSTREAM_REPO"
helm repo update "$UPSTREAM_REPO_NAME"
helm pull "$UPSTREAM_REPO_NAME/$UPSTREAM_CHART" \
  --version "$UPSTREAM_VERSION" \
  --untar \
  --untardir "$ROOT_DIR/helm-charts"

if [[ "$UPSTREAM_CHART" != "plane-enterprise" ]]; then
  mv "$ROOT_DIR/helm-charts/$UPSTREAM_CHART" "$CHART_DIR"
fi

sed -i \
  -e "s/^name: .*/name: $OUTPUT_CHART_NAME/" \
  -e "s/^version: .*/version: $OUTPUT_VERSION/" \
  -e "s/^appVersion: .*/appVersion: $OUTPUT_APP_VERSION/" \
  "$CHART_DIR/Chart.yaml"

patch -d "$CHART_DIR" -p0 < "$PATCH_DIR/stabilize-migration-job.patch"
