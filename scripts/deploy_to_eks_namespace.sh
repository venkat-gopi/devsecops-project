#!/bin/bash

set -e

ENV_NAME="$1"
SERVICE_TYPE="$2"
SAFE_APP_NAME="$3"
APP_PORT="$4"
DOCKER_USERNAME="$5"
IMAGE_TAG="$6"

echo "=================================================="
echo "DEPLOYING TO EKS NAMESPACE"
echo "=================================================="

if [ -z "$ENV_NAME" ]; then
  echo "ERROR: ENV_NAME is empty"
  exit 1
fi

if [ -z "$SERVICE_TYPE" ]; then
  echo "ERROR: SERVICE_TYPE is empty"
  exit 1
fi

if [ -z "$SAFE_APP_NAME" ]; then
  echo "ERROR: SAFE_APP_NAME is empty. Build job did not export safe_app_name."
  exit 1
fi

if [ -z "$DOCKER_USERNAME" ]; then
  echo "ERROR: DOCKER_USERNAME is empty"
  exit 1
fi

if [ -z "$IMAGE_TAG" ]; then
  echo "ERROR: IMAGE_TAG is empty"
  exit 1
fi

if [ -z "$APP_PORT" ]; then
  APP_PORT="80"
fi

IMAGE="${DOCKER_USERNAME}/${SAFE_APP_NAME}:${IMAGE_TAG}"

echo "Environment      : $ENV_NAME"
echo "Service Type     : $SERVICE_TYPE"
echo "Safe App Name    : $SAFE_APP_NAME"
echo "Application Port : $APP_PORT"
echo "Docker Image     : $IMAGE"

if [ -z "$IMAGE" ]; then
  echo "ERROR: Docker image value is empty."
  exit 1
fi

kubectl create namespace "$ENV_NAME" --dry-run=client -o yaml | kubectl apply -f -

sed "s|DOCKER_IMAGE_PLACEHOLDER|$IMAGE|g" k8s/deployment.yaml \
  | sed "s|CONTAINER_PORT_PLACEHOLDER|$APP_PORT|g" \
  | sed "s|APP_ENV_PLACEHOLDER|$ENV_NAME|g" \
  > "k8s/deployment-${ENV_NAME}.yaml"

sed "s|TARGET_PORT_PLACEHOLDER|$APP_PORT|g" k8s/service.yaml \
  | sed "s|SERVICE_TYPE_PLACEHOLDER|$SERVICE_TYPE|g" \
  > "k8s/service-${ENV_NAME}.yaml"

echo "Final deployment file:"
cat "k8s/deployment-${ENV_NAME}.yaml"

echo "Final service file:"
cat "k8s/service-${ENV_NAME}.yaml"

kubectl apply -n "$ENV_NAME" -f "k8s/deployment-${ENV_NAME}.yaml"
kubectl apply -n "$ENV_NAME" -f "k8s/service-${ENV_NAME}.yaml"

kubectl rollout status deployment/devsecops-app -n "$ENV_NAME" --timeout=180s

echo "Deployment completed for namespace: $ENV_NAME"

kubectl get pods -n "$ENV_NAME" -o wide
kubectl get svc -n "$ENV_NAME"
