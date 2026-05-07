#!/bin/bash

REQUESTED_TYPE="${1:-auto-detect}"

detect() {
  if [ "$REQUESTED_TYPE" != "auto-detect" ]; then
    echo "$REQUESTED_TYPE"
    return
  fi

  if [ -f "package.json" ]; then echo "nodejs"; return; fi
  if [ -f "requirements.txt" ]; then echo "python"; return; fi
  if [ -f "Pipfile" ]; then echo "python"; return; fi
  if [ -f "pom.xml" ]; then echo "java"; return; fi
  if [ -f "build.gradle" ]; then echo "java"; return; fi
  if [ -f "go.mod" ]; then echo "go"; return; fi
  if [ -f "Dockerfile" ]; then echo "docker"; return; fi

  echo "unknown"
}

get_language() {
  case "$1" in
    nodejs) echo "javascript" ;;
    python) echo "python" ;;
    java) echo "java" ;;
    go) echo "go" ;;
    docker) echo "docker" ;;
    *) echo "unknown" ;;
  esac
}

APP_TYPE=$(detect)
LANGUAGE=$(get_language "$APP_TYPE")

HAS_DOCKER="false"
HAS_TERRAFORM="false"
HAS_K8S="false"

[ -f "Dockerfile" ] && HAS_DOCKER="true"
find . -name "*.tf" | grep -q . && HAS_TERRAFORM="true"
[ -d "k8s" ] && HAS_K8S="true"

echo "app_type=$APP_TYPE" >> "$GITHUB_OUTPUT"
echo "language=$LANGUAGE" >> "$GITHUB_OUTPUT"
echo "has_docker=$HAS_DOCKER" >> "$GITHUB_OUTPUT"
echo "has_terraform=$HAS_TERRAFORM" >> "$GITHUB_OUTPUT"
echo "has_k8s=$HAS_K8S" >> "$GITHUB_OUTPUT"

echo "Detected app type: $APP_TYPE"
echo "Detected language: $LANGUAGE"
echo "Dockerfile found: $HAS_DOCKER"
echo "Terraform found: $HAS_TERRAFORM"
echo "Kubernetes folder found: $HAS_K8S"
