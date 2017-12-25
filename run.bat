@echo off

if not exist venv (
    echo venv doesn't exist, please run install.bat
    pause
    exit /b 0
)

call venv\Scripts\activate.bat

text2jira.exe

pause