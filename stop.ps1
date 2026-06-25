# stop.ps1 — Blinsky stopper
# Kills whatever is running on port 9001

$PORT = 9001

Write-Host "=== Blinsky Stop Script ===" -ForegroundColor Cyan

$existing = netstat -ano | Select-String ":$PORT " | Select-String "LISTENING"
if ($existing) {
    $pid = ($existing -split '\s+')[-1]
    Write-Host "[*] Stopping Blinsky (PID $pid on port $PORT)..." -ForegroundColor Yellow
    taskkill /PID $pid /F 2>$null
    Start-Sleep -Milliseconds 400
    Write-Host "[+] Blinsky stopped." -ForegroundColor Green
} else {
    Write-Host "[!] Nothing found on port $PORT — Blinsky is not running." -ForegroundColor DarkGray
}
