#!/bin/bash

set -e

APP_NAME="$1"
IMAGE_TAG="$2"
DOCKER_USERNAME="$3"
MODE="${4:-push}"

APP_DIR="app"

echo "=================================================="
echo "DOCKERFILE-FIRST IMAGE BUILD"
echo "=================================================="

SAFE_APP_NAME=$(echo "$APP_NAME" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9._-]/-/g' \
  | sed 's/_/-/g' \
  | sed 's/--*/-/g' \
  | sed 's/^[.-]*//' \
  | sed 's/[.-]*$//')

if [ -z "$SAFE_APP_NAME" ]; then
  SAFE_APP_NAME="customer-app"
fi

if [ "$DOCKER_USERNAME" = "local" ]; then
  IMAGE="local/${SAFE_APP_NAME}:${IMAGE_TAG}"
else
  IMAGE="${DOCKER_USERNAME}/${SAFE_APP_NAME}:${IMAGE_TAG}"
fi

echo "Original App Name : $APP_NAME"
echo "Docker-safe Name  : $SAFE_APP_NAME"
echo "Image             : $IMAGE"
echo "Mode              : $MODE"
echo "Customer Folder   : $APP_DIR"

DOCKERFILE_PATH=$(find "$APP_DIR" \
  -type f \
  -name "Dockerfile" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  | head -1)

if [ -z "$DOCKERFILE_PATH" ]; then
  echo "ERROR: No Dockerfile found inside app/"
  exit 1
fi

DOCKERFILE_DIR=$(dirname "$DOCKERFILE_PATH")

echo "Dockerfile found at: $DOCKERFILE_PATH"
echo "Build context: $DOCKERFILE_DIR"

docker build \
  -f "$DOCKERFILE_PATH" \
  -t "$IMAGE" \
  "$DOCKERFILE_DIR"

EXPOSED_PORT=$(grep -iE '^EXPOSE ' "$DOCKERFILE_PATH" | head -1 | awk '{print $2}' | cut -d'/' -f1)

if [ -z "$EXPOSED_PORT" ]; then
  EXPOSED_PORT="80"
fi

if [ "$MODE" != "scan-only" ] && [ "$DOCKER_USERNAME" != "local" ]; then
  echo "Pushing image to Docker Hub..."
  docker push "$IMAGE"
else
  echo "Scan-only/local mode. Push skipped."
fi

echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
echo "SAFE_APP_NAME=$SAFE_APP_NAME" >> "$GITHUB_ENV"
echo "APP_PORT=$EXPOSED_PORT" >> "$GITHUB_ENV"
echo "IMAGE_LOCAL_NAME=$SAFE_APP_NAME" >> "$GITHUB_ENV"

echo "=================================================="
echo "BUILD RESULT"
echo "=================================================="
echo "Final Image      : $IMAGE"
echo "Safe App Name    : $SAFE_APP_NAME"
echo "Detected App Port: $EXPOSED_PORT"

if [ -z "$SAFE_APP_NAME" ]; then
  echo "ERROR: SAFE_APP_NAME is empty"
  exit 1
fi

if [ -z "$EXPOSED_PORT" ]; then
  EXPOSED_PORT="80"
fi

# For next steps in the same job
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
  echo "SAFE_APP_NAME=$SAFE_APP_NAME" >> "$GITHUB_ENV"
  echo "APP_PORT=$EXPOSED_PORT" >> "$GITHUB_ENV"
  echo "IMAGE_LOCAL_NAME=$SAFE_APP_NAME" >> "$GITHUB_ENV"
fi

# For other jobs: dev, staging, production
# Do not export full IMAGE because it contains Docker username secret.
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "safe_app_name=$SAFE_APP_NAME" >> "$GITHUB_OUTPUT"
  echo "app_port=$EXPOSED_PORT" >> "$GITHUB_OUTPUT"
fi
