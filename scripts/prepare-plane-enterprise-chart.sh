#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART_DIR="$ROOT_DIR/helm-charts/plane-enterprise"
BUILD_DIR="$CHART_DIR/.generated"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# shellcheck source=/dev/null
source "$CHART_DIR/upstream.env"

rm -rf "$BUILD_DIR"

helm repo add "$UPSTREAM_REPO_NAME" "$UPSTREAM_REPO"
helm repo update "$UPSTREAM_REPO_NAME"
helm pull "$UPSTREAM_REPO_NAME/$UPSTREAM_CHART" \
  --version "$UPSTREAM_VERSION" \
  --untar \
  --untardir "$TMP_DIR"

mv "$TMP_DIR/$UPSTREAM_CHART" "$BUILD_DIR"

sed -i \
  -e "s/^name: .*/name: $OUTPUT_CHART_NAME/" \
  -e "s/^version: .*/version: $OUTPUT_VERSION/" \
  -e "s/^appVersion: .*/appVersion: $OUTPUT_APP_VERSION/" \
  "$BUILD_DIR/Chart.yaml"

patch -d "$BUILD_DIR" -p0 < "$CHART_DIR/patches/stabilize-migration-job.patch"
