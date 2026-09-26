#ifndef AppVersion
  #error AppVersion must be provided by build.ps1
#endif

[Setup]
AppId={{A230FA14-4B4A-42DC-B977-8616F778D75F}
AppName=Snap Extract
AppVersion={#AppVersion}
AppPublisher=switchfire6
AppPublisherURL=https://github.com/switchfire6/snap-extract
AppSupportURL=https://github.com/switchfire6/snap-extract/issues
AppUpdatesURL=https://github.com/switchfire6/snap-extract/releases
DefaultDirName={localappdata}\Programs\Snap Extract
DefaultGroupName=Snap Extract
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
SetupIconFile=..\snap_extract\assets\app.ico
UninstallDisplayIcon={app}\Snap Extract.exe
OutputDir=..\dist
OutputBaseFilename=Snap-Extract-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=Snap Extract.exe
RestartApplications=no
SetupLogging=yes
VersionInfoDescription=Snap Extract Installer

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Snap Extract\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Snap Extract"; Filename: "{app}\Snap Extract.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Snap Extract"; Filename: "{app}\Snap Extract.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Snap Extract.exe"; Description: "Launch Snap Extract"; Flags: nowait postinstall skipifsilent

; Inno removes only installed files. Exports, settings and cache belong to users.
