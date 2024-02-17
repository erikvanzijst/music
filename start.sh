#!/usr/bin/env bash
set -e

IMAGE="music:latest"
MUSIC_DIR="${1:-$PWD}"

if [[ $1 = "--build" || -z "$(docker images -q ${IMAGE} 2>/dev/null)" ]]; then
  echo "Building container..."
  docker build -t ${IMAGE} -f Dockerfile .
fi

docker run -it --rm -p 8000:8000 -v "${PWD}":/app -v "${MUSIC_DIR}":/music --name music ${IMAGE}
