#!/bin/sh
#
#

# set -xe

BIN_PATH=$(dirname $(readlink -f $0))
WORKSPACE_PATH=${BIN_PATH}/../


cd ${WORKSPACE_PATH}/helm-charts

echo '1. Package'
for FOLDER in $(ls -1p | grep '/$'); do
  CHART_NAME=$(echo $FOLDER | sed -e "s/\///g")

  echo 'Package ➡ '$CHART_NAME
  helm package $CHART_NAME
done

# echo '2. Publish'
# for FOLDER in $(ls -1p | grep 'tgz$'); do
#   CHART_NAME=$(echo $FOLDER | sed -e "s/\///g")

#   echo 'Publish ⬆ '$CHART_NAME
#   curl --request POST \
#     --user gitlab-ci-token:$CI_JOB_TOKEN \
#     --form "chart=@${CHART_NAME}" \
#     "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/helm/api/stable/charts"
#   echo ''
# done


