@echo off
rem Windows: runs the Python installer. Same flags as install.py.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 install.py %*) || (python install.py %*)
