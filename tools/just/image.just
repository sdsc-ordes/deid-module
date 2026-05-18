root_dir := `git rev-parse --show-toplevel`
set positional-arguments
set shell := ["bash", "-cue"]
ctr := "docker"
registry := "ghcr.io/sdsc-ordes/deid-module"
platforms := "linux/amd64"
images := "presidio-anonymizer presidio-analyzer"

# Default recipe to list all recipes.
[private]
default:
    just --list image

# Build all presidio images for all platforms
build tag="latest" *args:
  #!/usr/bin/env bash

  cd {{root_dir}}/external/repos/presidio
  for image in {{images}}; do
    for platform in {{platforms}}; do

      # Create platform-specific tag
      PLATFORM_TAG=$(echo "${platform}" | sed 's/\//-/g')
      docker buildx build \
        {{args}} \
        --platform "${platform}" \
        --tag "{{registry}}/${image}:{{tag}}-${PLATFORM_TAG}" \
        "./${image}"

    done
  done


# Create multi-platform manifests
create-manifests tag="latest":
  #!/usr/bin/env bash

  cd {{root_dir}}/external/repos/presidio
  for image in {{images}}; do
    for platform in {{platforms}}; do

    echo "Creating manifest for $image"
    PLATFORM_TAG=$(echo "${platform}" | sed 's/\//-/g')
    docker buildx imagetools create \
      --tag "{{registry}}/${image}:${{tag}}" \
      "{{registry}}/${image}:{{tag}}-${PLATFORM_TAG}"
  done
