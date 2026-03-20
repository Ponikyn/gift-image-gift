; Скрипт установки для GIFT Image Generator
; Inno Setup версия 6.0+

[Setup]
; Основная информация
AppName=GIFT Image Generator
AppVersion=1.0
AppPublisher=Your Name
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com

; Путь установки по умолчанию
DefaultDirName={autopf}\GIFT Image Generator
DefaultGroupName=GIFT Image Generator

; Файл лицензии (опционально, удалите если нет)
; LicenseFile=LICENSE.txt

; Параметры установки
OutputDir=installer
OutputBaseFilename=GIFT_Image_Generator_Setup
SetupIconFile=
Compression=lzma2
SolidCompression=yes
LanguageDetectionMethod=locale

; Минимальные требования
MinVersion=6.1

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1,6.1

[Files]
; Добавляем exe файл приложения
Source: "dist\gui.exe"; DestDir: "{app}"; Flags: ignoreversion
; Добавляем все файлы из папки dist (включая все зависимости)
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GIFT Image Generator"; Filename: "{app}\gui.exe"; IconIndex: 0
Name: "{group}\{cm:UninstallProgram,GIFT Image Generator}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GIFT Image Generator"; Filename: "{app}\gui.exe"; IconIndex: 0; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\GIFT Image Generator"; Filename: "{app}\gui.exe"; IconIndex: 0; Tasks: quicklaunchicon

[Run]
Filename: "{app}\gui.exe"; Description: "{cm:LaunchProgram,GIFT Image Generator}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}"
