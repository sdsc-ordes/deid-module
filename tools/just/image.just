root_dir := `git rev-parse --show-toplevel`
set shell := ["bash", "-cue"]
ctr := "docker"
repository := "ghcr.io/sdsc-ordes/deid-module"

# Default recipe to list all recipes.
[private]
default:
    just --list image

# Build all images
build *args:
  cd {{root_dir}} && \
    fd . './tools/image' \
      --type directory \
      --max-depth 1 \
      -x {{ctr}} build . \
        -f "{}/Dockerfile" \
        -t "{{repository}}:{/}" \
        {{args}}

# Push all images
push *args: build
  {{ctr}} push -a {{repository}}
