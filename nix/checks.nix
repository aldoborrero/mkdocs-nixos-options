{self, ...}: {
  perSystem = {
    self',
    inputs',
    pkgs,
    lib,
    ...
  }:
    with lib; {
      checks = let
        inherit (inputs'.nixpkgs-unstable.legacyPackages) statix;
      in
        {
          statix =
            pkgs.runCommand "statix" {
              nativeBuildInputs = [statix];
            } ''
              cp --no-preserve=mode -r ${self} source
              cd source
              HOME=$TMPDIR statix check
              touch $out
            '';
        }
        # merge in the package derivations to force a build of all packages during a `nix flake check`
        // (mapAttrs' (n: nameValuePair "package-${n}") self'.packages);

      devshells.default.commands = [
        {
          category = "Tools";
          name = "check";
          help = "Checks the source tree";
          command = "nix flake check";
        }
      ];
    };
}
