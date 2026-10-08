"""Explicit allow-list backup format: SQLite snapshot + managed PDFs only."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import uuid
import zipfile
from sqlalchemy import select, text, func
from .db import Work, File, Annotation, Material, now
from .phase2_models import ExternalAttachment, SyncState, MaintenanceEvent
from .storage import Storage

VERSION='0.2.0'
def diagnostics(session,root):
    storage=Storage(root);files=session.scalars(select(File)).all();missing=[];corrupt=[]
    for file in files:
        path=storage.resolve(file.path)
        if not path.is_file():missing.append(file.id)
        elif storage.hash(path)!=file.sha256:corrupt.append(file.id)
    last=session.scalar(select(MaintenanceEvent).where(MaintenanceEvent.kind=='backup').order_by(MaintenanceEvent.id.desc()).limit(1))
    return dict(app_version=VERSION,schema_version=session.execute(text('SELECT version_num FROM alembic_version')).scalar(),works=session.scalar(select(func.count()).select_from(Work)),managed_attachments=len(files),external_attachments=session.scalar(select(func.count()).select_from(ExternalAttachment)),missing_files=missing,corrupt_files=corrupt,duplicate_hashes=session.execute(select(File.sha256,func.count()).group_by(File.sha256).having(func.count()>1)).all(),linked_items=session.scalar(select(func.count()).select_from(SyncState)),conflicts=session.scalar(select(func.count()).select_from(SyncState).where(SyncState.status=='Conflict')),last_backup=last.created_at if last else None,storage_bytes=sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file()))

def backup(session,root,destination):
    root=Path(root).resolve();destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Choose a new backup filename; existing files are never overwritten')
    if destination.suffix.lower()!='.zip':raise ValueError('Backup filename must end in .zip')
    issues=diagnostics(session,root)
    if issues['missing_files'] or issues['corrupt_files']:raise ValueError('Repair missing/corrupt PDFs before creating a complete backup')
    snapshot=root/('backup-'+uuid.uuid4().hex+'.db');temporary=destination.with_name(destination.name+'.partial')
    if temporary.exists():raise ValueError('A partial backup already exists at this destination')
    try:
        with closing(sqlite3.connect(root/'researchos.db')) as source,closing(sqlite3.connect(snapshot)) as target:source.backup(target)
        files=session.scalars(select(File)).all()
        inventory=[dict(path=f.path,sha256=f.sha256,size=Storage(root).resolve(f.path).stat().st_size) for f in files]
        manifest=dict(format='ResearchOS-backup',version=1,app_version=VERSION,schema_version=issues['schema_version'],created_at=now(),database={'path':'researchos.db','sha256':Storage.hash(snapshot)},attachments=inventory)
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest,indent=2));archive.write(snapshot,'researchos.db')
            for f in files:archive.write(Storage(root).resolve(f.path),f.path)
        validate_backup(temporary)
        temporary.replace(destination)
        session.add(MaintenanceEvent(kind='backup',details={'filename':destination.name,'sha256':Storage.hash(destination)}))
        return {'path':str(destination),'manifest':manifest}
    finally:snapshot.unlink(missing_ok=True);temporary.unlink(missing_ok=True)

def validate_backup(path):
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('format')!='ResearchOS-backup' or manifest.get('version')!=1 or manifest.get('schema_version')!='0002':raise ValueError('Unsupported backup/schema version')
        expected={'manifest.json','researchos.db'}
        db=manifest['database']
        if db['path']!='researchos.db':raise ValueError('Invalid database inventory')
        entries=[db]+manifest['attachments']
        for item in manifest['attachments']:
            if item['path']!=Storage('.').key(item['sha256']):raise ValueError('Invalid attachment inventory')
            expected.add(item['path'])
        if len(archive.namelist())!=len(expected) or set(archive.namelist())!=expected:raise ValueError('Unexpected/duplicate backup entries')
        for item in entries:
            with archive.open(item['path']) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:raise ValueError('Backup checksum mismatch: '+item['path'])
        return manifest

def restore(path,destination):
    manifest=validate_backup(path);destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Restore destination must be a new folder')
    staging=destination.with_name(destination.name+'.restore-'+uuid.uuid4().hex)
    staging.mkdir(parents=True)
    try:
        with zipfile.ZipFile(path) as archive:
            for name in ['researchos.db']+[f['path'] for f in manifest['attachments']]:
                target=staging/name;target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(name) as source,target.open('wb') as out:shutil.copyfileobj(source,out)
        with closing(sqlite3.connect(staging/'researchos.db')) as database:
            if database.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or database.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Backup database integrity failed')
            inventory={f['path']:f['sha256'] for f in manifest['attachments']}
            actual=dict(database.execute('SELECT path,sha256 FROM files').fetchall())
            if actual!=inventory:raise ValueError('Database and manifest inventory differ')
            if database.execute('SELECT version_num FROM alembic_version').fetchone()[0]!=manifest['schema_version']:raise ValueError('Database schema does not match manifest')
        staging.rename(destination)
        return {'data_dir':str(destination),'manifest':manifest}
    except Exception:
        # Leave failed staging intact for inspection; never remove a user folder.
        raise
