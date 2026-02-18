# Iniciar Aurora - ejecutar en PowerShell
Set-Location $PSScriptRoot

Write-Host "Verificando dependencias..." -ForegroundColor Cyan
if (-not (Test-Path "node_modules\dotenv")) {
    Write-Host "Instalando dependencias Node..." -ForegroundColor Yellow
    npm install
}
Write-Host ""
Write-Host "Iniciando servidor Aurora... Abriendo navegador en 4 s." -ForegroundColor Green
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://localhost:3000" } | Out-Null
Write-Host ""
node server.js
