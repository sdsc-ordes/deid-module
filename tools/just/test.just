root_dir := `git rev-parse --show-toplevel`
set shell := ["bash", "-cue"]

# Default recipe to list all recipes.
[private]
default:
    just --list test

# Run modules unit tests
modules:
  just dev surrogate uv run pytest src/modules/surrogate

# Test deploy on minikube instance
deployment:
  just dev default bash ./tests/minikube_deploy
  just dev default minikube stop

