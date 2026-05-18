root_dir := `git rev-parse --show-toplevel`
set positional-arguments
set shell := ["bash", "-cue"]
ctr := "docker"
registry := "ghcr.io/sdsc-ordes/deid-module"

# Default recipe to list all recipes.
[private]
default:
    just --list image

# Build all presidio images for all platforms
build tag="latest" *args:
  #!/usr/bin/env bash

  PLATFORMS=("linux/amd64")
  IMAGES=("presidio-anonymizer" "presidio-analyzer")
  cd {{root_dir}}/external/repos/presidio
  for image in ${IMAGES[@]}; do
    for platform in ${PLATFORMS[@]}; do

      # Create platform-specific tag
      PLATFORM_TAG=$(echo "${platform}" | sed 's/\//-/g')
      docker buildx build \
        {{args}} \
        --platform "${platform}" \
        --tag "{{registry}}/${image}:{{tag}}-${PLATFORM_TAG}" \
        "./${image}"

    done
  done
