#!/bin/bash

set -e

APP_NAME="$1"
IMAGE_TAG="$2"
DOCKER_USERNAME="$3"

echo "=================================================="
echo "DYNAMIC DOCKER BUILD LAYER"
echo "=================================================="

if [ -z "$APP_NAME" ] || [ -z "$IMAGE_TAG" ] || [ -z "$DOCKER_USERNAME" ]; then
  echo "ERROR: APP_NAME, IMAGE_TAG, or DOCKER_USERNAME missing"
  exit 1
fi

SAFE_APP_NAME=$(echo "$APP_NAME" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9._-]/-/g' \
  | sed 's/_/-/g' \
  | sed 's/--*/-/g' \
  | sed 's/^[.-]*//' \
  | sed 's/[.-]*$//')

IMAGE="$DOCKER_USERNAME/$SAFE_APP_NAME:$IMAGE_TAG"

echo "Original App Name : $APP_NAME"
echo "Docker Safe Name  : $SAFE_APP_NAME"
echo "Docker Image      : $IMAGE"
echo ""

echo "Searching for customer app files..."

APP_DIR=""

if [ -f "package.json" ]; then
  APP_DIR="."
elif find . -name "package.json" -not -path "./node_modules/*" | head -1 | grep -q "package.json"; then
  APP_DIR=$(dirname "$(find . -name "package.json" -not -path "./node_modules/*" | head -1)")
fi

if [ -z "$APP_DIR" ]; then
  echo "No package.json found."
  echo "This customer repo may not be a deployable Node.js app."
  echo "Security scanning and Excel report are completed."
  echo "Skipping Docker build and EKS deployment."

  echo "DEPLOYABLE=false" >> "$GITHUB_ENV"
  exit 0
fi

echo "Deployable Node.js app found at: $APP_DIR"

cd "$APP_DIR"

echo "Current app directory:"
pwd
ls -la

if [ ! -f "Dockerfile" ]; then
  echo "Dockerfile not found in app folder. Generating Dockerfile..."

  cat > Dockerfile <<'EOF'
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --omit=dev

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
EOF

else
  echo "Dockerfile already exists in app folder."
fi

echo "Final Dockerfile:"
cat Dockerfile

echo "Building Docker image..."
docker build -t "$IMAGE" .

echo "Pushing Docker image..."
docker push "$IMAGE"

echo "Docker image pushed successfully: $IMAGE"

echo "DEPLOYABLE=true" >> "$GITHUB_ENV"
echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
echo "SAFE_APP_NAME=$SAFE_APP_NAME" >> "$GITHUB_ENV"
