@echo off
title AURORA - BOT DE TELEGRAM
color 0B
cd /d "%~dp0.."
cd AURORA_APP
python telegram_bot.py
if errorlevel 1 (
    py telegram_bot.py
)
pause
