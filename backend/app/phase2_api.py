import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
import keyring
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from .db import Work, File, Collection, CollectionWork, columns, now
from .phase2_models import RemoteLibrary, SyncState, ExternalAttachment, RemoteNote, CollectionMapping
from .integrations import registry
from .integrations.zotero.base import ZoteroError
from .integrations.zotero import sync
from .integrations.zotero.mapping import fingerprint, from_remote
from .maintenance import backup, restore, validate_backup, diagnostics
from .exporting import export_works

class ConnectionInput(BaseModel):
    mode:Literal['local','web']='local'
    enabled:bool=True
    endpoint:str='http://127.0.0.1:23119/api'
    library_type:Literal['user','group']='user'
    library_id:str=Field(default='0',pattern=r'^\d+$')
    key:SecretStr|None=None
class ImportInput(BaseModel):
    collections:list[str]=Field(default_factory=list)
class PushInput(BaseModel):
    work_ids:list[int]=Field(min_length=1,max_length=1000)
    collection:str|None=None
    note:bool=False
    pdf:bool=False
class ResolveInput(BaseModel):
    version:int
    fields:dict[str,Literal['local','remote','merge']]
class MappingInput(BaseModel):
    collection_id:int
    mirror:bool=False
class BackupInput(BaseModel):
    path:str
class RestoreInput(BackupInput):
    destination:str
class ExportInput(BaseModel):
    format:Literal['ris','bibtex','csl-json']
    work_ids:list[int]|None=None
    collection_id:int|None=None

def register(app,sessions,root,write_lock):
    integration_lock=asyncio.Lock()
    @app.exception_handler(ZoteroError)
    async def zotero_error(request:Request,error:ZoteroError):return JSONResponse(status_code=error.status,content={'detail':str(error)})
    @app.exception_handler(keyring.errors.KeyringError)
    async def credential_error(request:Request,error):return JSONResponse(status_code=503,content={'detail':'OS credential store unavailable'})
    def required(s,cls,id):
        obj=s.get(cls,id)
        if obj is None:raise HTTPException(404,'Record not found')
        return obj
    def connection(s,id):
        library=required(s,RemoteLibrary,id)
        if not library.enabled:raise HTTPException(409,'Enable this Zotero connection first')
        return library,registry.adapter(library,transport=getattr(app.state,'zotero_transport',None))
    async def health(library,adapter):
        status=await adapter.health()
        if library.mode=='local' and not library.server_id and status.server_id:
            # Identity partitions local DBs from each other and from Web versions.
            library.server_id=status.server_id
        return status

    @app.get('/zotero/connections')
    def connections():
        with sessions() as s:
            return [{**columns(l),'configured':bool(keyring.get_password(registry.SERVICE,l.identity))} for l in s.scalars(select(RemoteLibrary))]
    @app.post('/zotero/connections')
    async def configure(body:ConnectionInput):
        endpoint=body.endpoint.rstrip('/') if body.mode=='local' else 'https://api.zotero.org'
        if body.mode=='local':
            from .integrations.zotero.local import ZoteroLocal
            ZoteroLocal(endpoint,body.library_type,body.library_id)
        identity=f'{body.mode}:{endpoint}:{body.library_type}:{body.library_id}'
        async with integration_lock:
            with sessions.begin() as s:
                library=s.scalar(select(RemoteLibrary).where(RemoteLibrary.identity==identity))
                if library is None:
                    library=RemoteLibrary(identity=identity,mode=body.mode,endpoint=endpoint,library_type=body.library_type,library_id=body.library_id);s.add(library);s.flush()
                library.enabled=body.enabled
                if body.key is not None:registry.set_secret(library,body.key.get_secret_value())
                return columns(library)
    @app.post('/zotero/{id}/test')
    async def test_connection(id:int):
        async with integration_lock:
            with sessions.begin() as s:
                library,adapter=connection(s,id);return asdict(await health(library,adapter))
    @app.post('/zotero/{id}/clear-credentials')
    async def clear_credentials(id:int):
        async with integration_lock:
            with sessions.begin() as s:
                library=required(s,RemoteLibrary,id);registry.set_secret(library,'');library.enabled=False
                return {'cleared':True,'message':'Local credential removed. Revoke the Web API key in Zotero account settings to invalidate it for other applications.'}
    @app.post('/zotero/{id}/authorize-local')
    async def authorize_local(id:int):
        async with integration_lock:
            with sessions.begin() as s:
                library,adapter=connection(s,id)
                if library.mode!='local':raise HTTPException(422,'Local mode required')
                result=await adapter.authorize();library.server_id=adapter.server_id;registry.set_secret(library,result['key'])
                return {'configured':True,'remember':bool(result.get('remember'))}
    @app.get('/zotero/{id}/collections')
    async def remote_collections(id:int):
        with sessions() as s:
            library,adapter=connection(s,id);await health(library,adapter);return await adapter.collections()
    async def fetch_scope(adapter,body):
        items={}
        for collection in body.collections or [None]:
            for item in await adapter.items(collection):items[item['key']]=item
        # Collection endpoint may omit children. Fetch only selected parents.
        for item in list(items.values()):
            if item['data'].get('itemType') not in ('attachment','note','annotation'):
                for child in await adapter.children(item['key']):items[child['key']]=child
        return list(items.values())
    @app.post('/zotero/{id}/preview')
    async def preview(id:int,body:ImportInput):
        with sessions() as s:
            library,adapter=connection(s,id);await health(library,adapter);items=await fetch_scope(adapter,body)
            summary=dict(created=0,matched=0,updated=0,skipped=0,conflicts=0,errors=0)
            preview=[]
            for item in items:
                if item['data'].get('itemType') in ('attachment','note','annotation'):continue
                linked=s.scalar(select(SyncState).where(SyncState.library_id==id,SyncState.item_key==item['key']))
                match,conflict=sync.find_match(s,item)
                action='skipped' if linked else 'conflicts' if conflict else 'matched' if match else 'created'
                summary[action]+=1;preview.append({'key':item['key'],'title':item['data'].get('title',''),'action':action})
            return {'summary':summary,'items':preview,'attachments':sum(i['data'].get('itemType')=='attachment' for i in items)}
    @app.post('/zotero/{id}/import')
    async def import_remote(id:int,body:ImportInput):
        async with integration_lock:
            with sessions.begin() as s:
                library,adapter=connection(s,id);await health(library,adapter)
                collections=await adapter.collections();items=await fetch_scope(adapter,body)
                needed=set(body.collections)|{k for i in items for k in i['data'].get('collections',[])}
                sync.import_collections(s,library,[c for c in collections if not body.collections or c['key'] in needed])
                summary=sync.import_items(s,library,items)
                library.last_synced_at=now()
                return summary
    @app.get('/zotero/{id}/states')
    def states(id:int):
        with sessions() as s:
            library=required(s,RemoteLibrary,id);result=[]
            for state in s.scalars(select(SyncState).where(SyncState.library_id==id)):
                value=columns(state)
                if state.status=='In sync' and fingerprint(sync.local_value(s,library,s.get(Work,state.work_id)))!=state.local_fingerprint:value['status']='Local changes'
                value['title']=s.get(Work,state.work_id).title;result.append(value)
            return result
    @app.post('/zotero/{id}/sync')
    async def synchronize(id:int):
        async with integration_lock:
            with sessions.begin() as s:
                library,adapter=connection(s,id);await health(library,adapter)
                # Capture the version before pagination; concurrent remote edits are included next time.
                checkpoint=adapter.version
                changed={i['key']:i for i in await adapter.items(since=library.version)}
                results=[]
                for state in s.scalars(select(SyncState).where(SyncState.library_id==id)):
                    local=sync.local_value(s,library,s.get(Work,state.work_id))
                    if state.item_key in changed or fingerprint(local)!=state.local_fingerprint or state.status!='In sync':
                        try:await sync.sync_one(s,library,adapter,state)
                        except ZoteroError as error:state.status='Error';state.error=str(error)
                    results.append(columns(state))
                sync.import_items(s,library,[i for i in changed.values() if i['data'].get('itemType') in ('note','attachment')])
                library.version=checkpoint;library.last_synced_at=now();return results
    @app.post('/zotero/{id}/push')
    async def push(id:int,body:PushInput):
        async with integration_lock:
            with sessions() as s:
                library,adapter=connection(s,id);await health(library,adapter)
                if body.collection:
                    collections=await adapter.collections()
                    selected=[c for c in collections if c['key']==body.collection]
                    if not selected:raise HTTPException(422,'Destination collection not found')
                    sync.import_collections(s,library,selected)
                results=[]
                for work_id in body.work_ids:
                    work=required(s,Work,work_id)
                    state=await sync.push_new(s,library,adapter,work,body.collection,body.note,body.pdf,root)
                    s.flush();results.append(columns(state))
                s.commit()
                return results
    @app.post('/zotero/conflicts/{state_id}/resolve')
    async def resolve(state_id:int,body:ResolveInput):
        async with integration_lock:
            with sessions.begin() as s:
                state=required(s,SyncState,state_id);library,adapter=connection(s,state.library_id);await health(library,adapter)
                await sync.sync_one(s,library,adapter,state,body.model_dump());return columns(state)
    @app.post('/zotero/attachments/{attachment_id}/copy')
    async def copy(attachment_id:int):
        async with integration_lock:
            with sessions.begin() as s:
                attachment=required(s,ExternalAttachment,attachment_id);library,adapter=connection(s,attachment.library_id);await health(library,adapter)
                return await sync.copy_attachment(s,adapter,attachment,root)
    @app.get('/zotero/{id}/mappings')
    def get_mappings(id:int):
        with sessions() as s:return [columns(m) for m in sync.mappings(s,required(s,RemoteLibrary,id))]
    @app.patch('/zotero/mappings/{mapping_id}')
    def update_mapping(mapping_id:int,body:MappingInput):
        with write_lock,sessions.begin() as s:
            mapping=required(s,CollectionMapping,mapping_id);required(s,Collection,body.collection_id)
            mapping.collection_id=body.collection_id;mapping.mirror=body.mirror;return columns(mapping)
    @app.get('/diagnostics')
    def diagnose():
        with sessions() as s:return diagnostics(s,root)
    @app.post('/storage/backup')
    def create_backup(body:BackupInput):
        try:
            with write_lock,sessions.begin() as s:return backup(s,root,body.path)
        except (ValueError,OSError) as error:raise HTTPException(422,str(error)) from None
    @app.post('/storage/validate')
    def validate(body:BackupInput):
        try:return validate_backup(body.path)
        except Exception:raise HTTPException(422,'Invalid or corrupt ResearchOS backup') from None
    @app.post('/storage/restore')
    def restore_backup(body:RestoreInput):
        try:return restore(body.path,body.destination)
        except Exception:raise HTTPException(422,'Restore failed: verify backup and choose a new destination folder') from None
    @app.post('/export')
    def export(body:ExportInput):
        with sessions() as s:
            query=select(Work).where(Work.in_library.is_(True))
            if body.work_ids is not None:query=select(Work).where(Work.id.in_(body.work_ids))
            if body.collection_id is not None:query=query.where(Work.id.in_(select(CollectionWork.work_id).where(CollectionWork.collection_id==body.collection_id)))
            content,mime,extension=export_works(s.scalars(query).all(),body.format)
            return {'content':content,'mime':mime,'filename':'ResearchOS-export.'+extension}
