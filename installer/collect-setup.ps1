$ErrorActionPreference = "Stop"
$setup = Get-ChildItem -Recurse -Filter "R3E-Setup-Coach-Setup.exe" | Select-Object -First 1
if (-not $setup) { throw "Setup-exe nicht gefunden" }
Copy-Item $setup.FullName "dist\R3E-Setup-Coach-Setup.exe" -Force
(Get-FileHash "dist\R3E-Setup-Coach-Setup.exe" -Algorithm SHA256).Hash | Out-File "dist\SHA256-Setup.txt" -Encoding ascii
Write-Host "Setup-exe: $($setup.FullName)"
