{ pkgs ? import <nixpkgs> {} }:

pkgs.python3Packages.buildPythonApplication rec {
  pname = "devops-info-service";
  version = "1.0.0";
  src = ./.;

  format = "other";
  doCheck = false;

  propagatedBuildInputs = with pkgs.python3Packages; [
    flask
    prometheus-client
  ];

  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/share/${pname}
    cp app.py $out/share/${pname}/app.py

    makeWrapper ${pkgs.python3.interpreter} $out/bin/devops-info-service \
      --add-flags "$out/share/${pname}/app.py" \
      --prefix PYTHONPATH : "$PYTHONPATH" \
      --set PYTHONDONTWRITEBYTECODE 1 \
      --set PYTHONUNBUFFERED 1

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "DevOps course info service packaged reproducibly with Nix";
    mainProgram = "devops-info-service";
    license = licenses.mit;
    platforms = platforms.linux ++ platforms.darwin;
  };
}
