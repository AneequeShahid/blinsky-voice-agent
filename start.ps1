# start.ps1 — Blinsky launcher
# Kills anything on port 9001, starts backend, opens browser

$PORT = 9001
$PROJECT = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Blinsky Start Script ===" -ForegroundColor Cyan

# Step 1: Kill anything holding port 9001
$existing = netstat -ano | Select-String ":$PORT " | Select-String "LISTENING"
if ($existing) {
    $pid = ($existing -split '\s+')[-1]
    Write-Host "[*] Port $PORT in use by PID $pid — killing..." -ForegroundColor Yellow
    taskkill /PID $pid /F 2>$null
    Start-Sleep -Milliseconds 800
    Write-Host "[+] Process killed." -ForegroundColor Green
} else {
    Write-Host "[+] Port $PORT is free." -ForegroundColor Green
}

# Step 2: Start uvicorn backend in a new window
Write-Host "[*] Starting Blinsky backend on port $PORT..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PROJECT'; .\venv\Scripts\python.exe -m uvicorn api.app:app --port $PORT" -WindowStyle Normal

# Step 3: Wait for backend to come up
Write-Host "[*] Waiting for backend..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$PORT/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "  waiting... ($i/15)" -ForegroundColor DarkGray
}

if ($ready) {
    Write-Host "[+] Backend is up at http://localhost:$PORT" -ForegroundColor Green
} else {
    Write-Host "[!] Backend may not have started — check the terminal window" -ForegroundColor Red
}

# Step 4: Open the UI in the default browser
$uiPath = Join-Path $PROJECT "ui\web\index.html"
Write-Host "[*] Opening UI: $uiPath" -ForegroundColor Cyan
Start-Process $uiPath

Write-Host ""
Write-Host "=== Blinsky is running ===" -ForegroundColor Green
Write-Host "  Backend : http://localhost:$PORT" -ForegroundColor White
Write-Host "  Docs    : http://localhost:$PORT/docs" -ForegroundColor White
Write-Host "  UI      : $uiPath" -ForegroundColor White
Write-Host ""
Write-Host "Run .\stop.ps1 to shut down." -ForegroundColor DarkGray
