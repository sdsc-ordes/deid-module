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

    env.UV_PROJECT = "src/modules/surrogate";

    languages.python = {
      enable = true;
      directory = "src/modules/surrogate";
      venv.enable = true;
      uv = {
        enable = true;
        package = pkgs.uv;
        sync = {
          enable = true;
          allExtras = true;
        };
      };
    };
  }
]
