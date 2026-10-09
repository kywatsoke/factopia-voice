; Factopia Voice installer for Windows 10 and later (Inno Setup).
; Built by packaging/finish_app.py:
;   ISCC /DAppVersion=3.0.0-beta.1 /DNumericVersion=3.0.0 packaging\windows\installer.iss
; Installs for the current user only (no administrator prompt) into
; %LOCALAPPDATA%\Programs\Factopia Voice. Settings and downloaded models live
; in %LOCALAPPDATA%\Factopia Voice; the files people make in Documents.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef NumericVersion
  #define NumericVersion "0.0.0"
#endif
#define AppName "Factopia Voice"
#define Root "..\.."
#define WebView2Key "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

[Setup]
AppId={{6F1C2B7A-4E8D-4C3B-9A51-2D7E8F0B3C64}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Factopia Gist
AppPublisherURL=https://github.com/kywatsoke/factopia
VersionInfoVersion={#NumericVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#Root}\dist
OutputBaseFilename=Factopia-Voice-Windows-Setup
SetupIconFile={#Root}\build\icon.ico
UninstallDisplayIcon={app}\Factopia Voice.exe
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Root}\dist\Factopia Voice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\build\vendor\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Factopia Voice.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Factopia Voice.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 (the app window)..."; Check: NeedsWebView2; Flags: waituntilterminated
Filename: "{app}\Factopia Voice.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function HasWebView2(Root: Integer; Key: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

function NeedsWebView2(): Boolean;
begin
  Result := not (HasWebView2(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{#WebView2Key}')
              or HasWebView2(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{#WebView2Key}')
              or HasWebView2(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{#WebView2Key}'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Data: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Data := ExpandConstant('{localappdata}\{#AppName}');
    if DirExists(Data) then
      if SuppressibleMsgBox('Also remove the downloaded AI models and the settings (' + Data + ')?' + #13#10 + #13#10 +
         'Your own files in Documents\Factopia Voice are kept either way.',
         mbConfirmation, MB_YESNO, IDNO) = IDYES then
        DelTree(Data, True, True, True);
  end;
end;
