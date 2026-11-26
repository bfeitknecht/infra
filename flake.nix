{
  # The tools to work on infra: `direnv allow` (or `nix develop`) in the
  # repository. talosctl and kubectl must match the cluster (talos/topf.yaml
  # talosVersion, kubernetesVersion); flake.lock pins them, so check both
  # after `nix flake update`. images/opencode has its own flake.
  description = "infra: cluster tools";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      pkgsFor = system: nixpkgs.legacyPackages.${system};
    in
    {
      packages = forAllSystems (system: {
        topf = (pkgsFor system).callPackage ./nix/topf.nix { };
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShellNoCC {
            packages = [
              # Talos and Kubernetes
              self.packages.${system}.topf
              pkgs.talosctl
              pkgs.kubectl
              pkgs.fluxcd
              pkgs.kubernetes-helm
              pkgs.kn
              pkgs.cilium-cli
              # secrets
              pkgs.sops
              pkgs.age
              # the justfile, CI checks
              pkgs.just
              pkgs.yamlfmt
              pkgs.jq
              pkgs.yq-go
              # backups (k8up's restic repository), the oci control plane
              pkgs.restic
              pkgs.oci-cli
              # scripts/journey.py (standard library only)
              pkgs.python3
            ];
          };
        }
      );

      formatter = forAllSystems (system: (pkgsFor system).nixfmt);
    };
}
