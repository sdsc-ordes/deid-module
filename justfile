set positional-arguments
set shell := ["bash", "-cue"]

root_dir := `git rev-parse --show-toplevel`


# Default recipe to list all recipes.
[private]
default:
    just --list

# Format the whole repository.
format *args:
    treefmt --excludes 'src/chart/templates/*' {{args}}

# Clean up generated manifests.
clean:
    @echo "Cleaning up..."
    rm -rf build/ external/repos/*

# Render Helm charts
[private]
render-helm:
  # render helm charts with our values
  helm template dev src/chart -f src/chart/values.yaml --output-dir build

# Render manifests
render:
    just render-helm && \
    just format

# Apply manifests in dir to the cluster.
deploy dir="src/chart":
  cd {{root_dir}} && \
    helm upgrade --install dev {{dir}} -n ml-clin-deid -f {{dir}}/values.yaml

# Enter development shell
dev:
  just nix::develop

# Fetch external dependencies
fetch:
  just external::fetch

# Test deploy on minikube instance
test:
  bash ./tests/minikube_deploy
  minikube stop

# Manage OCI images.
[group('modules')]
mod image 'tools/just/image.just'
# Manage nix development environment.
[group('modules')]
mod nix 'tools/just/nix.just'
# Manage external dependencies.
[group('modules')]
mod external 'tools/just/external.just'
