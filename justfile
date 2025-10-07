set positional-arguments
set shell := ["bash", "-cue"]

root_dir := `git rev-parse --show-toplevel`


# Default recipe to list all recipes.
[private]
default:
    just --list

# Format the whole repository.
format *args:
    treefmt {{args}}

# Clean up external and generated manifests.
clean:
    @echo "Cleaning up..."
    rm -rf external/{helm,ytt}/**
    rm -rf src/**/{ytt,helm}/out

# Render Helm charts [intermediate step before rendering ytt manifests]
[private]
render-helm dir="src":
  # render external helm charts with our values into src/<service>/helm/out
  fd '^helm$' {{dir}} \
    -x sh -c 'helm template $(basename {//}) external/helm/$(basename {//}) -f {}/values.yaml --output-dir {}/out'

# Render ytt manifests
[private]
render-ytt dir="src":
  # render external ytt templates with our values into src/<service>/ytt/out
  fd '^ytt$' {{dir}} \
    -x sh -c 'ytt -f {}/values.yaml -f external/ytt/$(basename {//}) --output-files {}/out'

# Render manifests
render dir="src":
  just fetch && \
    just render-helm {{dir}} && \
    just render-ytt {{dir}} && \
    just format

# Apply manifests in dir to the cluster.
deploy dir="src":
  # decrypts+sources the .env file and injects values into the manifests
  cd {{root_dir}} && \
    just secrets::exec-env \
      "kubectl kustomize {{dir}} | envsubst \\\$QLEVER_ACCESS_TOKEN | kubectl apply -f -"

# Enter development shell
dev:
  just nix::develop

# Fetch external dependencies
fetch:
  just external::fetch

# Manage secrets.
[group('modules')]
mod secrets 'tools/just/secrets.just'
# Manage OCI images.
[group('modules')]
mod image 'tools/just/image.just'
# Manage nix development environment.
[group('modules')]
mod nix 'tools/just/nix.just'
# Manage external dependencies.
[group('modules')]
mod external 'tools/just/external.just'
