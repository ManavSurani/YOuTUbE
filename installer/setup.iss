#define MyAppName "YOuTUbE"
#define MyAppVersion "1.0.4"
#define MyAppExe "YOuTUbE.exe"

[Setup]
AppId={{7EBA9B70-1A62-4D3F-A437-4DD99FB4CA6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\Output
OutputBaseFilename=YOuTUbE_Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
; no admin rights needed
PrivilegesRequired=lowest
; lets silent updates replace a running app
CloseApplications=yes
RestartApplications=yes
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\YOuTUbE\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
  BinDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    AppDataDir := ExpandConstant('{userappdata}\{#MyAppName}');
    BinDir := AppDataDir + '\bin';

    // Always remove external tools in bin\
    DelTree(BinDir, True, True, True);

    // Ask once about history and settings (default: No)
    if SuppressibleMsgBox('Also remove history and settings?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
    begin
      DelTree(AppDataDir, True, True, True);
    end;
  end;
end;
