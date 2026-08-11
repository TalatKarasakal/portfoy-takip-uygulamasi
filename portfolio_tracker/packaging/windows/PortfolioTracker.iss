#ifndef SourceDir
  #define SourceDir "..\..\dist\PortfolioTracker"
#endif

#ifndef OutputDir
  #define OutputDir "..\..\release"
#endif

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{A6B08D46-0C79-4CD2-81D8-A4F85EBE9079}
AppName=Portföy Takip
AppVersion={#AppVersion}
AppPublisher=Talat Karasakal
DefaultDirName={localappdata}\Programs\PortfolioTracker
DefaultGroupName=Portföy Takip
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=PortfolioTracker-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\..\app\resources\app_icon.ico
UninstallDisplayIcon={app}\PortfolioTracker.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Portföy Takip"; Filename: "{app}\PortfolioTracker.exe"
Name: "{autodesktop}\Portföy Takip"; Filename: "{app}\PortfolioTracker.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"

[Run]
Filename: "{app}\PortfolioTracker.exe"; Description: "Portföy Takip'i çalıştır"; Flags: nowait postinstall skipifsilent
