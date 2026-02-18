# Obtener nuevo codigo QR - ejecutar DESPUES de cerrar el servidor
Set-Location $PSScriptRoot
Write-Host ""
Write-Host "=== OBTENER NUEVO CODIGO QR ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Cierra el servidor (en la ventana donde corre node server.js, pulsa Ctrl+C)." -ForegroundColor Yellow
Write-Host "2. Luego ejecuta este script de nuevo o borra la carpeta .wwebjs_auth" -ForegroundColor Yellow
Write-Host ""

if (Test-Path ".wwebjs_auth") {
    Remove-Item -Recurse -Force ".wwebjs_auth"
    Write-Host "Sesion borrada." -ForegroundColor Green
} else {
    Write-Host "No habia sesion guardada." -ForegroundColor Gray
}
Write-Host ""
Write-Host "Ahora ejecuta: node server.js" -ForegroundColor Cyan
Write-Host "Abre http://localhost:3000 y veras el codigo QR de nuevo. Escanealo con WhatsApp." -ForegroundColor Cyan
Write-Host ""
