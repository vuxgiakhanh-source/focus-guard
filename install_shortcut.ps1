# FocusGuard PRO - Re-create Desktop Shortcut
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = "C:\Users\LOQ\AppData\Local\Programs\Python\Python312\pythonw.exe"
$IconPath = Join-Path $ScriptDir "app_icon.ico"
$MainPy = Join-Path $ScriptDir "main.py"

$DesktopPaths = @([Environment]::GetFolderPath("Desktop"), "C:\Users\LOQ\Desktop") | Select-Object -Unique

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
