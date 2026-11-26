# topf (Talos orchestrator by PostFinance) is not in nixpkgs: built from the
# release tag. Bump: version, then the two hashes (build once with
# lib.fakeHash to get each).
{
  lib,
  buildGoModule,
  fetchFromGitHub,
}:
buildGoModule (finalAttrs: {
  pname = "topf";
  version = "0.6.2";

  src = fetchFromGitHub {
    owner = "postfinance";
    repo = "topf";
    tag = "v${finalAttrs.version}";
    hash = "sha256-frUyZtpA0iyFwHxlN5SqZ0WFfU4sMalmdkHtulg+B3I=";
  };

  vendorHash = "sha256-VLZLPM1/a1Lf5ggk4pwB/AL+Drrdfmm3f9DYjvpBKcA=";

  subPackages = [ "cmd/topf" ];
  env.CGO_ENABLED = 0;
  ldflags = [
    "-s"
    "-w"
    "-X main.version=${finalAttrs.version}"
  ];

  meta = {
    description = "Talos orchestrator by PostFinance";
    homepage = "https://github.com/postfinance/topf";
    license = lib.licenses.mit;
    mainProgram = "topf";
  };
})
