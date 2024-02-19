#!/usr/bin/env bash
set -e

IMAGE="music:latest"
DOCKER_BUILD=false
MUSIC_DIR=""

for arg in "$@"
do
    case $arg in
        --build)
            DOCKER_BUILD=true
            ;;
        *)
            MUSIC_DIR="$arg"
            ;;
    esac
done

MUSIC_DIR="${MUSIC_DIR:-$PWD}"
MUSIC_DIR="$(cd "$MUSIC_DIR" && pwd)"

if [[ $DOCKER_BUILD == "true" || -z "$(docker images -q ${IMAGE} 2>/dev/null)" ]]; then
  echo "Building container..."
  docker build -t ${IMAGE} -f Dockerfile .
fi

echo Serving files under: $MUSIC_DIR
docker run -it --rm -p 8000:8000 -v "${PWD}":/app -v "${MUSIC_DIR}":/music --name music ${IMAGE}
