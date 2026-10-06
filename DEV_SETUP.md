# Windows development and build

## Prerequisites

- Windows 10/11 x64.
- Python 3.12, Node.js 24 LTS with npm, Git.
- Network access for initial dependency installation and live search. Reading/library features work offline.

Run these PowerShell commands from the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
npm ci
npm run build
npm run desktop
```

Electron starts the backend automatically, chooses a free loopback port, injects a random session token and closes the sidecar on exit. Normal data lives in the Electron user-data `library` folder. Settings displays the exact path. For an isolated test library, set `$env:RESEARCHOS_DATA_DIR` before launching.

## Development server

In terminal 1:

```powershell
npm run dev
```

In terminal 2:

```powershell
$env:RESEARCHOS_DEV_URL='http://127.0.0.1:5173'
npm run desktop
```

For browser-only UI development, start `backend/run.py` with a random `RESEARCHOS_TOKEN` and set `VITE_RESEARCHOS_TOKEN` to that same value in the Vite process environment. Never commit the token. File pickers require Electron; browser-only testing can call the authenticated import endpoint.

## Tests

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
$env:PYTHONPATH="$PWD"
..\.venv\Scripts\python.exe tests\live_acceptance.py
Pop-Location
npm test
npm run build
```

Unit tests use HTTP fixtures, a fresh migrated SQLite database and generated PDFs; production adapters always use official HTTP APIs. `live_acceptance.py` explicitly reaches the providers and writes `docs/live-acceptance.json`. Test databases and downloaded PDFs are gitignored. Network failures must be reported as blocked/failing live acceptance, never replaced with fixtures.

## Windows portable build

```powershell
powershell -File scripts\build-windows.ps1
```

This builds the Vite renderer, freezes Python with PyInstaller and assembles the official installed Electron distribution into a Windows runnable folder. Outputs:

- `release/ResearchOS-portable/ResearchOS.exe`
- `release/ResearchOS-0.1.0-win-x64.zip`
- `release/ResearchOS-0.1.0-win-x64.zip.sha256`

The renderer bundles its dependencies; the main process uses only built-in Node/Electron APIs. No development `node_modules` are included in the portable app. The portable build script uses filesystem packaging so it also works in environments that prohibit npm child-process pipes.

The conventional electron-builder configuration is included. After the sidecar build, `npm run package:installer` generates an NSIS installer on an unrestricted Windows build agent. It did not complete in the initial managed Codex environment due to `spawn EPERM`; do not describe an installer as tested until that command passes.

## Managed environment notes

The initial Codex environment denied Node child-process pipes and Python secure temporary directory ACLs. Vite's native config loader plus preserved symlinks avoids unnecessary subprocess discovery. Pytest uses workspace-local directories with inherited ACLs. No Electron sandbox has been disabled.

The generated workspace can carry restrictive AppContainer ACLs. If Electron reports `install_dir_access.cc`, extract the ZIP in an ordinary user-owned folder. Do not disable Electron sandboxing as a workaround. Windows desktop launch must still be verified there.

## Migrations and storage

The backend upgrades Alembic to head at startup. `0001` creates Phase 1 tables, foreign keys, FTS5 and change triggers. Before changing schema, close ResearchOS and back up the entire library folder. Library removal only clears membership; it retains attachments and provenance. Interrupted jobs can be retried from Tasks.

## References

- OpenAlex search: https://help.openalex.org/api/searching/
- OpenAlex authentication: https://help.openalex.org/api/authentication/
- Crossref parameters: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
