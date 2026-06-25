$port = 9001
$uiFile = "$PSScriptRoot\ui\web\index.html"

function Kill-Port {
    param([int]$Port)
    $rows = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING"
    foreach ($row in $rows) {
        $tokens = $row.ToString().Trim() -split '\s+'
        $procId = $tokens[-1]
        Write-Host "Killing PID $procId on port $Port"
        taskkill /F /PID $procId | Out-Null
    }
}

Write-Host "Checking port $port..."
Kill-Port -Port $port

$pythonCmd = "python"
$venvPython = "$PSScriptRoot\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
}

Write-Host "Opening browser..."
Start-Process $uiFile

Write-Host "Starting Blinsky backend on port $port..."
Set-Location $PSScriptRoot
& $pythonCmd -m uvicorn api.app:app --reload --port $port
