{
  description = "mkdocs-nixos-options - A mkdocs plugin for rendering NixOS module options";

  nixConfig = {
    extra-substituters = ["https://nix-community.cachix.org"];
    extra-trusted-public-keys = ["nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="];
  };

  inputs = {
    # packages
    nixpkgs.url = "github:nixos/nixpkgs/23.05";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    # flake-parts
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    flake-root.url = "github:srid/flake-root";
    hercules-ci-effects.url = "github:hercules-ci/hercules-ci-effects";

    # utils
    devshell = {
      url = "github:numtide/devshell";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-compat.url = "github:nix-community/flake-compat";
    devour-flake = {
      url = "github:srid/devour-flake";
      flake = false;
    };
    lib-extras = {
      url = "github:aldoborrero/lib-extras/v0.2.2";
      inputs.devshell.follows = "devshell";
      inputs.flake-parts.follows = "flake-parts";
      inputs.flake-root.follows = "flake-root";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.treefmt-nix.follows = "treefmt-nix";
    };
  };

  outputs = inputs @ {
    flake-parts,
    nixpkgs,
    lib-extras,
    ...
  }: let
    lib = nixpkgs.lib.extend (l: _: {extras = lib-extras.lib l;});
  in
    flake-parts.lib.mkFlake {
      inherit inputs;
      specialArgs = {inherit lib;};
    }
    {
      imports = [
        inputs.devshell.flakeModule
        inputs.flake-parts.flakeModules.easyOverlay
        inputs.flake-root.flakeModule
        inputs.treefmt-nix.flakeModule
      ];

      systems = ["x86_64-linux"];

      debug = false;

      perSystem = {
        pkgs,
        pkgsUnstable,
        lib,
        config,
        system,
        ...
      }: {
        # nixpkgs
        _module.args = {
          pkgs = lib.extras.nix.mkNixpkgs {
            inherit system;
            inherit (inputs) nixpkgs;
          };
          pkgsUnstable = lib.extras.nix.mkNixpkgs {
            inherit system;
            nixpkgs = inputs.nixpkgs-unstable;
          };
        };

        # devshell
        devshells.default = {
          name = "mkdocs-nixos-options";
          packages = with pkgs; [
            poetry
            python311
          ];
          commands = [
            {
              category = "python";
              name = "pytest";
              help = "Invoke pytest directly";
              command = ''poetry run pytest $@'';
            }
            {
              category = "Tools";
              name = "fmt";
              help = "Format the source tree";
              command = "nix fmt";
            }
            {
              category = "Tools";
              name = "check";
              help = "Checks the source tree";
              command = "nix flake check";
            }
          ];
        };

        # formatter
        treefmt.config = {
          inherit (config.flake-root) projectRootFile;
          package = pkgs.treefmt;
          flakeFormatter = true;
          flakeCheck = true;
          programs = {
            alejandra.enable = true;
            black.enable = true;
            deadnix.enable = true;
            mdformat.enable = true;
            prettier.enable = true;
          };
          settings.formatter.prettier.excludes = ["*.md"];
        };

        # checks
        checks = {
          nix-build-all = let
            devour-flake = pkgs.callPackage inputs.devour-flake {};
          in
            pkgs.writeShellApplication {
              name = "nix-build-all";
              runtimeInputs = [
                pkgs.nix
                devour-flake
              ];
              text = ''
                # Make sure that flake.lock is sync
                nix flake lock --no-update-lock-file

                # Do a full nix build (all outputs)
                devour-flake . "$@"
              '';
            };
        };

        # packages
        packages.mkdocs-nixos-options = pkgs.python311Packages.buildPythonPackage rec {
          pname = "mkdocs-nixos-options";
          version = "0.1.0";
          format = "pyproject";

          src = lib.cleanSource ./.;

          buildInputs = with pkgs.python311Packages; [
            mkdocs
          ];

          propagatedBuildInputs = with pkgs.python311Packages; [
            jinja2
          ];

          nativeBuildInputs = with pkgs.python311Packages; [
            poetry-core
          ];

          nativeCheckInputs = with pkgs.python311Packages; [
            pytestCheckHook
            pythonImportsCheckHook
            pytest-mock
          ];

          pythonImportsCheck = [
            "mkdocs_nixos_options"
          ];

          meta = with lib; {
            homepage = "https://github.com/aldoborrero/mkdocs-nixos-options";
            description = "Render your NixOS options on MkDocs";
            changelog = "https://github.com/aldoborrero/mkdocs-nixos-options/releases/v${version}";
            license = licenses.mit;
            maintainers = with maintainers; [aldoborrero];
          };
        };
      };
    };
}
