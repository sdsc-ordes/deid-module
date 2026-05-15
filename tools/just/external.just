root_dir := `git rev-parse --show-toplevel`
set shell := ["bash", "-cue"]

# Default recipe to list all recipes.
[private]
default:
    just --list external

# Fetch external files.
fetch:
  cd {{root_dir}} && \
    vendir sync --locked -f vendir.yaml --chdir external

# Apply local patches to external repos.
patch: fetch
  for repo in ./external/repos; do \
    for patch in ./external/patches/$(basename $repo)/*; do
      git -C $repo apply $patch
    done
  done


# Update external manifests to their latest version.
[confirm("Update external files? [y/n]")]
refresh:
  cd {{root_dir}} && \
    vendir sync -f vendir.yaml --chdir external
