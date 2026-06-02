root_dir := `git rev-parse --show-toplevel`
set positional-arguments
set shell := ["bash", "-cue"]
ctr := "docker"
registry := "ghcr.io/sdsc-ordes/deid-module"
platforms := "linux/amd64"
images := "presidio-anonymizer presidio-analyzer"
images-modules := "surrogate"

# Default recipe to list all recipes.
[private]
default:
    just --list image

# Build all images (presidio and modules)
build tag="latest" *args: (build-presidio tag args) (build-modules tag args)

# Build all presidio images for all platforms
[private]
build-presidio tag="latest" *args:
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

# Build modules images
[private]
build-modules tag="latest" platform="" *args:
  #!/usr/bin/env bash

  cd {{root_dir}}/src/modules/
  for image in {{images-modules}}; do
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
        --tag "{{registry}}/${image}:{{tag}}" \
        "{{registry}}/${image}:{{tag}}-${PLATFORM_TAG}"
    done
  done
