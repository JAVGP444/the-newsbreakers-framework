#define MyAppName "The NewsBreakers"
#define MyAppVersion "1.0"
#define MyAppExeName "NewsBreakers.exe"

[Setup]
AppId={{9E7B2C11-4A6F-4D3A-9C1E-NEWSBREAKERS}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\NewsBreakers
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultGroupName={#MyAppName}
OutputDir=..\..\dist
OutputBaseFilename=NewsBreakers-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\branding\logo.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\..\dist\NewsBreakers\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "..\..\branding\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir The NewsBreakers"; Flags: nowait postinstall skipifsilent
