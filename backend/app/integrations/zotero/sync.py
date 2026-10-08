"""Three-way comparison. Remote writes always follow a fresh versioned read."""
import html
from pathlib import Path
import uuid
from sqlalchemy import select
from ...db import Work, Identifier, Collection, CollectionWork, File, now
from ...phase2_models import SyncState, CollectionMapping, ExternalAttachment, RemoteNote
from ...canonical import normalized
from ...storage import Storage
from ...importer import import_pdf
from .mapping import FIELDS, fingerprint, from_remote, to_remote, stable_ids
from .base import ZoteroError

def mappings(session,library):return session.scalars(select(CollectionMapping).where(CollectionMapping.library_id==library.id)).all()
def local_value(session,library,work):
    memberships=set(session.scalars(select(CollectionWork.collection_id).where(CollectionWork.work_id==work.id)))
    return dict(title=work.title,authors=work.authors,doi=work.doi,journal=work.journal or '',date=work.publication_date or str(work.year or ''),year=work.year,tags=sorted(work.tags),notes=work.notes,collections=sorted(m.remote_key for m in mappings(session,library) if m.collection_id in memberships))

def apply_local(session,library,work,value):
    for field in ('title','authors','doi','year','tags','notes'):setattr(work,field,value[field])
    work.journal=value['journal'];work.publication_date=value['date'] or None
    for mapping in mappings(session,library):
        member=session.get(CollectionWork,(mapping.collection_id,work.id))
        if mapping.remote_key in value['collections'] and member is None:session.add(CollectionWork(collection_id=mapping.collection_id,work_id=work.id))
        elif mapping.remote_key not in value['collections'] and member and mapping.mirror:session.delete(member)

def mark_synced(session,library,state,work,remote):
    value=from_remote(remote)
    state.remote_version=remote['version'];state.remote_snapshot=remote;state.base=value
    state.local_fingerprint=fingerprint(local_value(session,library,work))
    state.status='In sync';state.conflicts={};state.error=None;state.last_synced_at=now()

def record_conflict(state,local,remote,base,reason='Both sides changed'):
    state.status='Conflict';state.remote_snapshot=remote
    value=from_remote(remote)
    state.conflicts={f:{'local':local[f],'remote':value[f],'base':base.get(f)} for f in FIELDS if local[f]!=value[f]}
    state.error=reason

def import_collections(session,library,collections):
    for item in collections:
        data=item['data'];mapping=session.scalar(select(CollectionMapping).where(CollectionMapping.library_id==library.id,CollectionMapping.remote_key==item['key']))
        if mapping:
            mapping.remote_name=data['name'];mapping.parent_key=data.get('parentCollection') or None
            continue
        # Names are unique in Phase 1; remote keys prevent flattening collisions.
        name=data['name'];existing=session.scalar(select(Collection).where(Collection.name==name))
        if existing:name=f"{name} [Zotero {library.id}/{item['key']}]"
        collection=Collection(name=name);session.add(collection);session.flush()
        session.add(CollectionMapping(library_id=library.id,collection_id=collection.id,remote_key=item['key'],remote_name=data['name'],parent_key=data.get('parentCollection') or None))
    session.flush()

def find_match(session,item):
    value=from_remote(item)
    if value['doi']:
        match=session.scalar(select(Work).where(Work.doi==value['doi']))
        if match:return match,False
    for key in stable_ids(item):
        record=session.get(Identifier,key)
        if record:
            work=session.get(Work,record.work_id)
            return work,bool(work.doi and value['doi'] and work.doi!=value['doi'])
    if value['authors'] and value['year']:
        candidates=session.scalars(select(Work).where(Work.title_key==normalized(value['title']),Work.author_key==normalized(value['authors'][0]),Work.year==value['year'])).all()
        if len(candidates)==1:
            work=candidates[0];return work,bool(work.doi and value['doi'] and work.doi!=value['doi'])
    return None,False

def import_items(session,library,items):
    counts=dict(created=0,matched=0,updated=0,skipped=0,conflicts=0,errors=0)
    parents={}
    for item in items:
        if item['data'].get('itemType') in ('attachment','note','annotation'):continue
        state=session.scalar(select(SyncState).where(SyncState.library_id==library.id,SyncState.item_key==item['key']))
        if state:
            parents[item['key']]=state.work_id;counts['skipped']+=1;continue
        work,conflict=find_match(session,item);created=work is None
        if created:
            work=Work(title=from_remote(item)['title'],in_library=True);session.add(work);session.flush()
        already=session.scalar(select(SyncState).where(SyncState.library_id==library.id,SyncState.work_id==work.id))
        if already:counts['skipped']+=1;continue
        local=local_value(session,library,work);value=from_remote(item)
        state=SyncState(library_id=library.id,item_key=item['key'],work_id=work.id,remote_version=item['version'],base=value,remote_snapshot=item)
        session.add(state);parents[item['key']]=work.id
        if conflict:
            record_conflict(state,local,item,{},'Conflicting DOI: explicit resolution required');counts['conflicts']+=1
        elif not created and any(local[f] not in ('',None,[]) and local[f]!=value[f] and value[f] not in ('',None,[]) for f in ('title','authors','journal','date','notes')):
            record_conflict(state,local,item,{},'Existing ResearchOS metadata differs; choose fields before synchronization');counts['conflicts']+=1
        else:
            merged={f:(value[f] if value[f] not in ('',None,[]) else local[f]) for f in FIELDS}
            merged['tags']=sorted(set(local['tags']+value['tags']))
            apply_local(session,library,work,merged);work.in_library=True
            work.publisher_url=item['data'].get('url') or work.publisher_url
            session.flush();mark_synced(session,library,state,work,item)
            # Local-only retained fields must remain visible as pending changes.
            if local_value(session,library,work)!=value:state.status='Local changes';state.local_fingerprint=fingerprint(value)
        for key in stable_ids(item):
            if session.get(Identifier,key) is None:session.add(Identifier(key=key,work_id=work.id))
        counts['created' if created else 'matched']+=1
    session.flush()
    for item in items:
        data=item['data'];parent=data.get('parentItem')
        work_id=parents.get(parent)
        if work_id is None:
            state=session.scalar(select(SyncState).where(SyncState.library_id==library.id,SyncState.item_key==parent)) if parent else None
            work_id=state.work_id if state else None
        if not work_id:continue
        if data.get('itemType')=='attachment':
            record=session.scalar(select(ExternalAttachment).where(ExternalAttachment.library_id==library.id,ExternalAttachment.item_key==item['key']))
            if record:record.metadata_json=data
            else:session.add(ExternalAttachment(library_id=library.id,work_id=work_id,item_key=item['key'],metadata_json=data))
        if data.get('itemType')=='note':
            record=session.scalar(select(RemoteNote).where(RemoteNote.library_id==library.id,RemoteNote.item_key==item['key']))
            if record:record.content=data.get('note','');record.version=item['version']
            else:session.add(RemoteNote(library_id=library.id,work_id=work_id,item_key=item['key'],content=data.get('note',''),version=item['version']))
    return counts

async def sync_one(session,library,adapter,state,resolution=None):
    work=session.get(Work,state.work_id)
    remote=await adapter.item(state.item_key);remote_value=from_remote(remote);local=local_value(session,library,work)
    local_changed=fingerprint(local)!=state.local_fingerprint
    remote_changed=remote_value!=state.base
    doi_conflict=bool(local['doi'] and remote_value['doi'] and local['doi']!=remote_value['doi'])
    if resolution is not None:
        if remote['version']!=resolution['version']:
            record_conflict(state,local,remote,state.base,'Remote changed while resolving; review again');return
        chosen={}
        for field in FIELDS:
            choice=resolution['fields'].get(field)
            if choice=='local':chosen[field]=local[field]
            elif choice=='remote':chosen[field]=remote_value[field]
            elif choice=='merge' and field in ('tags','collections'):chosen[field]=sorted(set(local[field]+remote_value[field]))
            elif local[field]==remote_value[field]:chosen[field]=local[field]
            else:raise ZoteroError(422,f'Choose a resolution for {field}')
        if chosen['doi']:
            other=session.scalar(select(Work).where(Work.doi==chosen['doi'],Work.id!=work.id))
            if other:raise ZoteroError(409,'DOI belongs to another Work; choose the existing local DOI or resolve identity manually')
        local=chosen;local_changed=True;remote_changed=False
    elif doi_conflict or (local_changed and remote_changed) or state.status=='Conflict':
        record_conflict(state,local,remote,state.base,'Conflicting DOI' if doi_conflict else 'Both sides changed');return
    if local_changed:
        state.status='Local changes'
        payload=to_remote(local);original=to_remote(remote_value)
        patch={k:v for k,v in payload.items() if original.get(k)!=v}
        # Preserve remote memberships not represented by a ResearchOS mapping.
        mapped={m.remote_key for m in mappings(session,library)}
        if 'collections' in patch:patch['collections']=sorted(set(patch['collections'])|{k for k in remote_value['collections'] if k not in mapped})
        if patch:
            try:remote=await adapter.update(state.item_key,remote['version'],patch)
            except ZoteroError as error:
                if error.status==412:
                    record_conflict(state,local,await adapter.item(state.item_key),state.base,'Remote changed during write');return
                raise
        apply_local(session,library,work,local);session.flush()
    elif remote_changed:
        state.status='Remote changes';apply_local(session,library,work,remote_value);session.flush()
    mark_synced(session,library,state,work,remote)

async def push_new(session,library,adapter,work,collection=None,note=False,pdf=False,root=None):
    state=session.scalar(select(SyncState).where(SyncState.library_id==library.id,SyncState.work_id==work.id))
    if state:
        if collection:
            mapping=session.scalar(select(CollectionMapping).where(CollectionMapping.library_id==library.id,CollectionMapping.remote_key==collection))
            if mapping and not session.get(CollectionWork,(mapping.collection_id,work.id)):
                session.add(CollectionWork(collection_id=mapping.collection_id,work_id=work.id));session.flush()
        await sync_one(session,library,adapter,state)
        if state.status=='Conflict':return state
    else:
        value=local_value(session,library,work)
        if collection:value['collections']=sorted(set(value['collections']+[collection]))
        remote=await adapter.create({'itemType':'journalArticle',**to_remote(value),'url':work.publisher_url or ''})
        state=SyncState(library_id=library.id,work_id=work.id,item_key=remote['key']);session.add(state)
        apply_local(session,library,work,value);session.flush();mark_synced(session,library,state,work,remote)
    # Persist a successful remote identity before optional child uploads. A failed
    # upload must never turn the next retry into a duplicate parent-item creation.
    session.commit()
    if note and work.notes:
        existing=await adapter.children(state.item_key)
        marker='<h1>ResearchOS note</h1>'
        body=marker+'<p>'+html.escape(work.notes).replace('\n','<br/>')+'</p>'
        target=next((i for i in existing if i['data'].get('itemType')=='note' and i['data'].get('note','').startswith(marker)),None)
        if target:
            prior=session.scalar(select(RemoteNote).where(RemoteNote.library_id==library.id,RemoteNote.item_key==target['key']))
            if target['data'].get('note')!=body:
                if prior is None or prior.content!=target['data'].get('note'):
                    raise ZoteroError(409,'ResearchOS note was edited in Zotero. Import and review the remote note before sending a replacement')
                target=await adapter.update(target['key'],target['version'],{'note':body})
            if prior:prior.content=body;prior.version=target['version']
        else:
            target=await adapter.create({'itemType':'note','parentItem':state.item_key,'note':body,'tags':[]})
            session.add(RemoteNote(library_id=library.id,work_id=work.id,item_key=target['key'],content=body,version=target['version']))
        session.commit()
    if pdf:
        children=await adapter.children(state.item_key)
        for file in session.scalars(select(File).where(File.work_id==work.id)):
            marker='ResearchOS SHA-256: '+file.sha256
            attachment=next((i for i in children if i['data'].get('title')==marker),None)
            if attachment and attachment['data'].get('md5'):continue
            if attachment is None:attachment=await adapter.create({'itemType':'attachment','parentItem':state.item_key,'linkMode':'imported_file','title':marker,'filename':file.name,'contentType':'application/pdf','tags':[]})
            await adapter.upload(attachment['key'],Storage(root).resolve(file.path),file.name)
    return state

async def copy_attachment(session,adapter,attachment,root):
    content=await adapter.download(attachment.item_key)
    if not content.startswith(b'%PDF'):raise ZoteroError(422,'Attachment is not a PDF')
    temp=Path(root)/('import-'+uuid.uuid4().hex+'.pdf')
    try:
        temp.write_bytes(content);digest=Storage.hash(temp)
        existing=session.scalar(select(File).where(File.sha256==digest))
        if existing:
            attachment.managed_file_id=existing.id
            return {'file_id':existing.id,'duplicate':True,'work_id':existing.work_id}
        result=import_pdf(session,Path(root),temp,attachment.work_id)
        attachment.managed_file_id=result['file_id'];return result
    finally:temp.unlink(missing_ok=True)
