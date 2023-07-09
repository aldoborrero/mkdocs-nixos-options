{
  perSystem = {inputs', ...}: let
    inherit
      (inputs'.nixpkgs-unstable.legacyPackages)
      alejandra
      poetry
      ;
  in {
    devshells.default = {
      name = "mkdocs-nixos-options";
      packages = [
        alejandra
        poetry
      ];
      commands = let
        category = "python";
      in [
        {
          inherit category;
          name = "pytest";
          help = "Invoke pytest directly";
          command = ''poetry run pytest $@'';
        }
      ];
    };
  };
}
