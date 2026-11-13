@echo off
rem Baut die Windows-App "R3E-Setup-Coach.exe" (dist\R3E-Setup-Coach\R3E-Setup-Coach.exe)
rem onedir statt onefile: kein Temp-Entpacken zur Laufzeit -> weniger AV-False-Positives (z. B. G Data).
rem Voraussetzung: Python 3.9+ installiert, dieses Repo lokal geklont.
pip install pyinstaller || exit /b 1
python tools\gen_icon.py || exit /b 1
pyinstaller --onedir --windowed --noupx --icon assets/app.ico --add-data ".r3e-coach.json;." --add-data "assets/app.ico;." --name "R3E-Setup-Coach" r3e-coach-gui.py || exit /b 1
echo.
echo Fertig: dist\R3E-Setup-Coach\R3E-Setup-Coach.exe