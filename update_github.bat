@echo off
setlocal

cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo Not a git repository.
  exit /b 1
)

git add -A
git diff --cached --quiet
if errorlevel 1 (
  for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set TS=%%i
  git commit -m "update %TS%"
) else (
  echo No changes to commit.
)

git pull --rebase origin main
if errorlevel 1 exit /b 1

git push origin main
if errorlevel 1 exit /b 1

echo Done.
endlocal
