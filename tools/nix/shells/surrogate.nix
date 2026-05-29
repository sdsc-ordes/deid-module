# devenv modules for the surrogate Python service.
# Enter with: nix develop ./tools/nix#surrogate
# Then cd into src/modules/surrogate and run: uv sync --extra dev
{pkgs, ...}: [
  {
    name = "surrogate";
    packages = [
      pkgs.pyright
      pkgs.ruff
    ];

    languages.python = {
      enable = true;
      directory = "src/modules/surrogate";
      venv.enable = true;
      uv = {
        enable = true;
        package = pkgs.uv;
        # pyproject.toml lives in src/modules/surrogate/, not the repo root,
        # so auto-sync is disabled — run `uv sync --extra dev` manually there.
        sync.enable = false;
      };
    };
  }
]
