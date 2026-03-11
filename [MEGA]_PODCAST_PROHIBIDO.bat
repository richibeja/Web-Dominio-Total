@echo off
title [MEGA] CHERRY STUDIO - CONSOLE
color 0C
cd /d "%~dp0"
py -m streamlit run AURORA_PODCAST/app.py
if errorlevel 1 (
    streamlit run AURORA_PODCAST/app.py
)
pause
