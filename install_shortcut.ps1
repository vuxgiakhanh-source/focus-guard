# FocusGuard PRO - Re-create Desktop Shortcut
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ScriptDir "venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonPath)) {
    $PythonPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe"
}
if (-not (Test-Path $PythonPath)) {
    $PythonCommand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($PythonCommand) { $PythonPath = $PythonCommand.Source }
    else { throw "Không tìm thấy pythonw.exe; hãy cài Python hoặc tạo venv trong thư mục dự án." }
}
$IconPath = Join-Path $ScriptDir "app_icon.ico"
$MainPy = Join-Path $ScriptDir "main.py"

$DesktopPaths = @([Environment]::GetFolderPath("Desktop")) | Select-Object -Unique

foreach ($Desktop in $DesktopPaths) {
    if (Test-Path $Desktop) {
        $WshShell = New-Object -ComObject WScript.Shell
        $ShortcutPath = Join-Path $Desktop "FocusGuard PRO.lnk"
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $PythonPath
        $Shortcut.Arguments = "`"$MainPy`""
        $Shortcut.WorkingDirectory = $ScriptDir
        $Shortcut.IconLocation = "$IconPath, 0"
        $Shortcut.Description = "FocusGuard PRO - Trợ Lý Học Tập AI"
        $Shortcut.Save()
        Write-Host "[+] Đã tạo shortcut tại: $ShortcutPath"
    }
}
