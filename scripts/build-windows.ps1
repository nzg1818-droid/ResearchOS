$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& node node_modules/typescript/bin/tsc --noEmit
if ($LASTEXITCODE) { throw 'TypeScript validation failed' }
& node node_modules/vite/bin/vite.js build --configLoader native
if ($LASTEXITCODE) { throw 'Frontend build failed' }
Push-Location backend
& ../.venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --name researchos-backend --collect-all keyring --collect-all pymupdf --add-data 'alembic.ini;.' --add-data 'migrations;migrations' run.py
if ($LASTEXITCODE) { throw 'Sidecar build failed' }
Pop-Location
& .venv/Scripts/python.exe scripts/package_portable.py
if ($LASTEXITCODE) { throw 'Packaging failed' }
