{
  # The isolated OpenCode server's image. The definition lives in omni
  # (modules/images/opencode.nix); this flake pins omni (flake.lock), so an
  # infra release tag names exactly one image. Bump: `nix flake update omni`
  # in this directory, commit, release.
  description = "OpenCode server image for infra applications/opencode";

  inputs.omni.url = "github:bfeitknecht/omni";

  outputs =
    { omni, ... }:
    {
      packages.x86_64-linux.default = omni.packages.x86_64-linux.opencode-image;
    };
}
