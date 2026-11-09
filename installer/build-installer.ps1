$ErrorActionPreference = "Stop"
$v = python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
Write-Host "Baue Installer für Version $v"
iscc installer\setup.iss /DMyAppVersion=$v
