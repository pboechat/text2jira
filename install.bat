@echo off

if exist venv (
    echo venv directory already exist.
    pause
    exit /b 0
)

where python.exe >nul 2>nul
if %errorlevel%==1 (
    echo python.exe couldn't be found...
    exit /b 0
)

python -m venv venv

call venv\Scripts\activate.bat

rem update pip to the latest version
python -m pip install -U pip

pip3 install -e .

pause
