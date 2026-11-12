@echo off
setlocal
pushd "%~dp0"
python src\main.py %*
set "rc=%errorlevel%"
popd
exit /b %rc%
