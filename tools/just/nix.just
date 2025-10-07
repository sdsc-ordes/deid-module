set positional-arguments
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`

# Default recipe to list all recipes.
[private]
default:
  just --list nix

# Enter a Nix development shell.
develop *args:
    @echo "Starting nix developer shell in './tools/nix/flake.nix'."
    cd {{root_dir}} && \
      cmd=("$@") && \
      { [ -n "${cmd:-}" ] || cmd=("zsh"); } && \
      nix develop ./tools/nix#default --accept-flake-config --command "${cmd[@]}"
