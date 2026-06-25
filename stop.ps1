$port = 9001
$rows = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
if (-not $rows) {
    Write-Host "Blinsky stopped"
    return
}
foreach ($row in $rows) {
    $tokens = $row.ToString().Trim() -split '\s+'
    $procId = $tokens[-1]
    Write-Host "Killing PID $procId on port $port"
    taskkill /F /PID $procId | Out-Null
}
Start-Sleep -Seconds 1
Write-Host "Blinsky stopped"
