#ifndef MyAppVersion
#define MyAppVersion "0.6.1"
#endif
#define MyAppName "R3E Setup-Coach"
#define MyAppPublisher "Pfoetiman76"
#define MyAppURL "https://github.com/Pfoetiman76/R3E_Setup-Coach"

[Setup]
AppId={{7F3E9A21-5C4B-4E8D-9A6F-2B1C0D8E5F44}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\R3E-Setup-Coach
DefaultGroupName=R3E Setup-Coach
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=R3E-Setup-Coach-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\R3E-Setup-Coach.exe

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\R3E-Setup-Coach\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\R3E Setup-Coach"; Filename: "{app}\R3E-Setup-Coach.exe"
Name: "{group}\{cm:UninstallProgram,R3E Setup-Coach}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\R3E Setup-Coach"; Filename: "{app}\R3E-Setup-Coach.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\R3E-Setup-Coach.exe"; Description: "R3E Setup-Coach starten"; Flags: nowait postinstall skipifsilent