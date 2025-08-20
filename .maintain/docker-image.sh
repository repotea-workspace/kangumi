#!/bin/sh
#
#

# set -xe

BIN_PATH=$(dirname $(readlink -f $0))
WORKSPACE_PATH=${BIN_PATH}/../

cd ${WORKSPACE_PATH}/docker-image

for FOLDER in $(ls -1p | grep '/$'); do
  cd ${WORKSPACE_PATH}/docker-image/$FOLDER
  IMAGE_NAME=$(echo $FOLDER | sed -e "s/\///g")

  echo 'Image -> '$IMAGE_NAME

  IMAGE_TAG_SHA=$CI_REGISTRY/$CI_PROJECT_PATH/$IMAGE_NAME:sha-$CI_COMMIT_SHORT_SHA
  # IMAGE_TAG_SLUG=$CI_REGISTRY/$CI_PROJECT_PATH/$IMAGE_NAME:$CI_COMMIT_REF_SLUG
  IMAGE_TAG_LATEST=$CI_REGISTRY/$CI_PROJECT_PATH/$IMAGE_NAME:latest

  echo "[$IMAGE_NAME] ➡ $IMAGE_TAG_SHA"
  # echo "[$IMAGE_NAME] ➡ $IMAGE_TAG_SLUG"
  echo "[$IMAGE_NAME] ➡ $IMAGE_TAG_LATEST"
  docker build -t "$IMAGE_TAG_SHA" .
  docker tag "$IMAGE_TAG_SHA" "$IMAGE_TAG_SLUG"
  docker tag "$IMAGE_TAG_SHA" "$IMAGE_TAG_LATEST"

  echo "[$IMAGE_NAME] ⬆ $IMAGE_TAG_SHA"
  # echo "[$IMAGE_NAME] ⬆ $IMAGE_TAG_SLUG"
  echo "[$IMAGE_NAME] ⬆ $IMAGE_TAG_LATEST"
  docker push "$IMAGE_TAG_SHA"
  docker push "$IMAGE_TAG_SLUG"
  docker push "$IMAGE_TAG_LATEST"
done

