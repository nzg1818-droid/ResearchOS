"""Build a Windows runnable directory using the installed official Electron distribution.

This has no npm subprocess discovery step; useful on managed Windows environments.
The renderer is already bundled by Vite and the main process uses only Node built-ins.
"""
from pathlib import Path
import json
import shutil
import hashlib

root=Path(__file__).resolve().parents[1]
metadata=json.loads((root/'package.json').read_text(encoding='utf-8'))
out=root/'release'/('ResearchOS-'+metadata['version']+'-portable')
electron=root/'node_modules'/'electron'/'dist'
backend=root/'backend'/'dist'/'researchos-backend'
assert (root/'dist'/'index.html').is_file(), 'Build frontend first'
assert (backend/'researchos-backend.exe').is_file(), 'Build Python sidecar first'
shutil.copytree(electron,out,dirs_exist_ok=True)
app=out/'resources'/'app'
app.mkdir(parents=True,exist_ok=True)
for name in ('electron','dist'):
    shutil.copytree(root/name,app/name,dirs_exist_ok=True)
metadata=json.loads((root/'package.json').read_text())
(app/'package.json').write_text(json.dumps({k:metadata[k] for k in ('name','version','main','description','author')}),encoding='utf-8')
shutil.copytree(backend,out/'resources'/'backend',dirs_exist_ok=True)
source=out/'electron.exe';target=out/'ResearchOS.exe'
source.replace(target)
archive=shutil.make_archive(str(root/'release'/('ResearchOS-'+metadata['version']+'-win-x64')),'zip',out.parent,out.name)
digest=hashlib.sha256(Path(archive).read_bytes()).hexdigest()
Path(archive+'.sha256').write_text(digest+'  '+Path(archive).name+'\n')
print(archive)
print('SHA256 '+digest)
