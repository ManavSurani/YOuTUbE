#define MyAppName "YOuTUbE"
#define MyAppVersion "1.0.0"
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
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpReady then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe', 'yt-dlp.exe', '');
    DownloadPage.Add('https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip', 'ffmpeg.zip', '');
    DownloadPage.Add('https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip', 'deno.zip', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        // If download fails (e.g. offline), continue without failing the install
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
  Result := True;
end;

procedure SearchAndCopy(const SearchDir, TargetFileName, DestDir: String);
var
  FindRec: TFindRec;
begin
  if FindFirst(SearchDir + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            SearchAndCopy(SearchDir + '\' + FindRec.Name, TargetFileName, DestDir)
          else if CompareText(FindRec.Name, TargetFileName) = 0 then
            CopyFile(SearchDir + '\' + FindRec.Name, DestDir + '\' + TargetFileName, False);
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  BinDir: String;
  TmpDir: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    BinDir := ExpandConstant('{userappdata}\{#MyAppName}\bin');
    TmpDir := ExpandConstant('{tmp}');
    ForceDirectories(BinDir);

    // 1. Copy yt-dlp.exe
    if FileExists(TmpDir + '\yt-dlp.exe') then
    begin
      CopyFile(TmpDir + '\yt-dlp.exe', BinDir + '\yt-dlp.exe', False);
    end;

    // 2. Extract deno.zip with tar.exe (hidden)
    if FileExists(TmpDir + '\deno.zip') then
    begin
      ForceDirectories(TmpDir + '\deno_out');
      Exec(ExpandConstant('{sys}\tar.exe'), '-xf "' + TmpDir + '\deno.zip" -C "' + TmpDir + '\deno_out"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      SearchAndCopy(TmpDir + '\deno_out', 'deno.exe', BinDir);
    end;

    // 3. Extract ffmpeg.zip with tar.exe (hidden)
    if FileExists(TmpDir + '\ffmpeg.zip') then
    begin
      ForceDirectories(TmpDir + '\ffmpeg_out');
      Exec(ExpandConstant('{sys}\tar.exe'), '-xf "' + TmpDir + '\ffmpeg.zip" -C "' + TmpDir + '\ffmpeg_out"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      SearchAndCopy(TmpDir + '\ffmpeg_out', 'ffmpeg.exe', BinDir);
      SearchAndCopy(TmpDir + '\ffmpeg_out', 'ffprobe.exe', BinDir);
    end;
  end;
end;

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
