set positional-arguments
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`

# Default recipe to list all recipes.
[private]
default:
  just --list nix

# Enter a Nix development shell.
develop shell="default" *args:
    @echo "Starting {{shell}} developer shell in './tools/nix/flake.nix'."
    cd {{root_dir}} && \
      shell="$1" && \
      shift 1 && \
      cmd=("$@") && \
      { [ -n "${cmd:-}" ] || cmd=("zsh"); } && \
      nix develop --impure ./tools/nix#$shell --accept-flake-config --command "${cmd[@]}"
