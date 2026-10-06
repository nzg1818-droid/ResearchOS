import asyncio
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
from threading import Lock
import keyring
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from .db import initialize, Work, File, Collection, CollectionWork, Annotation, Material, Job, SourceHit, columns
from .schemas import Search, LibraryPatch, ImportRequest, AnnotationInput
from .canonical import upsert
from .adapters import federated
from .importer import import_pdf

def create_app(data_dir=None, token=None):
    data = Path(data_dir or os.environ.get('RESEARCHOS_DATA_DIR') or Path(os.getenv('LOCALAPPDATA', Path.home())) / 'ResearchOS')
    auth = token or os.environ.get('RESEARCHOS_TOKEN') or secrets.token_urlsafe(32)
    engine, sessions = initialize(data)
    tasks = set()
    write_lock = Lock()
    logger = logging.getLogger('researchos.' + str(id(engine)))
    handler = RotatingFileHandler(data / 'researchos.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @asynccontextmanager
    async def lifespan(app):
        yield
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        engine.dispose()
        handler.close()
        logger.removeHandler(handler)

    async def authorize(request: Request):
        if not secrets.compare_digest(request.headers.get('X-ResearchOS-Token', ''), auth):
            raise HTTPException(401, 'Invalid local session')

    app = FastAPI(title='ResearchOS', lifespan=lifespan, dependencies=[Depends(authorize)])
    app.state.sessions, app.state.data = sessions, data
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173', 'null'], allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Content-Type','X-ResearchOS-Token'])

    def required(session, cls, id):
        item = session.get(cls, id)
        if item is None: raise HTTPException(404, 'Record not found')
        return item

    def serialize_work(session, w):
        result = columns(w)
        result['files'] = [{k:v for k,v in columns(f).items() if k != 'path'} for f in session.scalars(select(File).where(File.work_id == w.id))]
        result['sources'] = sorted(set(session.scalars(select(SourceHit.source).where(SourceHit.work_id == w.id))))
        result['collections'] = list(session.scalars(select(CollectionWork.collection_id).where(CollectionWork.work_id == w.id)))
        return result

    def job_update(id, **values):
        with write_lock, sessions.begin() as s:
            j = s.get(Job, id)
            for k,v in values.items(): setattr(j, k, v)

    def import_job(id, payload):
        paths = []
        for name in payload['paths']:
            p = Path(name)
            paths.extend(sorted(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() == '.pdf') if p.is_dir() else [p])
        imported, errors = [], []
        for index, path in enumerate(paths):
            try:
                with write_lock, sessions.begin() as s:
                    imported.append(import_pdf(s, data, path, payload.get('work_id')))
            except Exception as e:
                errors.append({'file': path.name, 'error': str(e)})
            job_update(id, progress=int(100*(index+1)/len(paths)))
        return {'imports': imported, 'errors': errors}

    async def run_job(id):
        with sessions() as s:
            j = required(s, Job, id)
            kind, payload = j.kind, j.request
        job_update(id, state='running')
        try:
            if kind == 'search':
                hits, errors, counts = await federated(Search(**payload))
                with write_lock, sessions.begin() as s:
                    ids = list(dict.fromkeys(upsert(s, hit).id for hit in hits))
                    surviving = set(s.scalars(select(Work.id).where(Work.id.in_(ids))))
                    ids = [id for id in ids if id in surviving]
                result = {'work_ids': ids, 'errors': errors, 'source_counts': counts}
                state = 'partial' if errors and counts else 'failed' if errors else 'completed'
            else:
                result = await asyncio.to_thread(import_job, id, payload)
                state = 'partial' if result['errors'] and result['imports'] else 'failed' if result['errors'] else 'completed'
            job_update(id, state=state, result=result, progress=100)
            logger.info('job=%s kind=%s state=%s', id, kind, state)
        except Exception as e:
            logger.error('job=%s failed=%s', id, type(e).__name__)
            job_update(id, state='failed', error=str(e).split(' for url')[0])

    def launch(id):
        task = asyncio.create_task(run_job(id))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def submit(kind, payload):
        with write_lock, sessions.begin() as s:
            j = Job(kind=kind, request=payload)
            s.add(j)
            s.flush()
            id = j.id
        launch(id)
        return {'job_id': id}

    @app.get('/health')
    def health(): return {'status': 'ok', 'version': '0.1.0', 'data_dir': str(data)}

    @app.post('/search')
    async def search(body: Search): return submit('search', body.model_dump(mode='json'))

    @app.post('/imports')
    async def imports(body: ImportRequest): return submit('import', body.model_dump())

    @app.get('/jobs')
    def jobs():
        with sessions() as s: return [columns(j) for j in s.scalars(select(Job).order_by(Job.id.desc()).limit(100))]

    @app.get('/jobs/{id}')
    def job(id: int):
        with sessions() as s: return columns(required(s, Job, id))

    @app.post('/jobs/{id}/retry')
    async def retry(id: int):
        with sessions() as s:
            j = required(s, Job, id)
            if j.state in ('queued', 'running'): raise HTTPException(409, 'Task is already running')
            return submit(j.kind, j.request)

    @app.get('/works')
    def works(library: bool = False, q: str = '', ids: str = '', collection: int | None = None):
        with sessions() as s:
            query = select(Work).order_by(Work.id.desc())
            if library: query = query.where(Work.in_library.is_(True))
            if ids:
                try: wanted = [int(x) for x in ids.split(',')]
                except ValueError: raise HTTPException(422, 'Invalid Work IDs')
                query = query.where(Work.id.in_(wanted))
            if q.strip():
                phrase = '"' + q.replace('"', '""') + '"'
                found = s.execute(text('SELECT rowid FROM works_fts WHERE works_fts MATCH :q'), {'q': phrase}).scalars().all()
                query = query.where(Work.id.in_(found))
            if collection:
                query = query.where(Work.id.in_(select(CollectionWork.work_id).where(CollectionWork.collection_id == collection)))
            results = [serialize_work(s, w) for w in s.scalars(query)]
            if ids:
                order = {id: index for index, id in enumerate(wanted)}
                results.sort(key=lambda w: order[w['id']])
            return results

    @app.get('/works/{id}')
    def work(id: int):
        with sessions() as s: return serialize_work(s, required(s, Work, id))

    @app.patch('/works/{id}')
    def patch_work(id: int, body: LibraryPatch):
        with write_lock, sessions.begin() as s:
            w = required(s, Work, id)
            for k,v in body.model_dump(exclude_none=True).items(): setattr(w, k, v)
            s.flush()
            return serialize_work(s, w)

    @app.post('/works/{id}/oa')
    async def oa(id: int):
        with sessions() as s:
            w = required(s, Work, id)
            query, mode = (w.doi, 'doi') if w.doi else (w.title, 'title')
        hits, errors, counts = await federated(Search(query=query, mode=mode, sources=['openalex']))
        with write_lock, sessions.begin() as s:
            for hit in hits: upsert(s, hit)
            w = required(s, Work, id)
            return {'locations': w.oa_locations, 'errors': errors, 'source_counts': counts}

    @app.get('/collections')
    def collections():
        with sessions() as s: return [columns(c) for c in s.scalars(select(Collection))]

    class Name(BaseModel):
        name: str = Field(min_length=1, max_length=150)

    @app.post('/collections')
    def add_collection(body: Name):
        with write_lock, sessions.begin() as s:
            found = s.scalar(select(Collection).where(Collection.name == body.name.strip()))
            if found: return columns(found)
            c = Collection(name=body.name.strip())
            s.add(c); s.flush()
            return columns(c)

    @app.post('/collections/{id}/works/{work_id}')
    def collect(id: int, work_id: int):
        with write_lock, sessions.begin() as s:
            required(s, Collection, id); required(s, Work, work_id)
            if not s.get(CollectionWork, (id, work_id)): s.add(CollectionWork(collection_id=id, work_id=work_id))
            return {'ok': True}

    @app.delete('/collections/{id}/works/{work_id}')
    def uncollect(id: int, work_id: int):
        with write_lock, sessions.begin() as s:
            c = s.get(CollectionWork, (id, work_id))
            if c: s.delete(c)
            return {'ok': True}

    @app.get('/files/{id}/content')
    def content(id: int):
        with sessions() as s:
            f = required(s, File, id)
            if not Path(f.path).is_file(): raise HTTPException(404, 'Managed PDF is missing')
            return FileResponse(f.path, media_type='application/pdf')

    @app.get('/files/{id}/annotations')
    def annotations(id: int):
        with sessions() as s: return [columns(a) for a in s.scalars(select(Annotation).where(Annotation.file_id == id))]

    @app.post('/annotations')
    def add_annotation(body: AnnotationInput):
        with write_lock, sessions.begin() as s:
            f = required(s, File, body.file_id)
            if body.page > f.pages: raise HTTPException(422, 'Page is outside this PDF')
            w = required(s, Work, f.work_id)
            a = Annotation(work_id=w.id, **body.model_dump(exclude={'kind'}))
            s.add(a); s.flush()
            if body.kind != 'highlight':
                s.add(Material(annotation_id=a.id, kind=body.kind, provenance={'work_id': w.id, 'title': w.title, 'doi': w.doi, 'authors': w.authors, 'year': w.year, 'file_id': f.id, 'sha256': f.sha256, 'filename': f.name, 'page': a.page, 'text': a.text, 'context': a.context, 'rects': a.rects, 'note': a.note, 'tags': a.tags, 'timestamp': a.created_at}))
            return columns(a)

    @app.get('/materials')
    def materials():
        with sessions() as s:
            return [{**columns(m), 'annotation': columns(s.get(Annotation, m.annotation_id))} for m in s.scalars(select(Material).order_by(Material.id.desc()))]

    class APIKey(BaseModel):
        key: str = Field(max_length=1000)

    @app.post('/settings/openalex')
    def set_key(body: APIKey):
        try:
            if body.key: keyring.set_password('ResearchOS', 'openalex', body.key)
            else:
                try: keyring.delete_password('ResearchOS', 'openalex')
                except keyring.errors.PasswordDeleteError: pass
        except keyring.errors.KeyringError: raise HTTPException(503, 'Windows credential store unavailable')
        return {'configured': bool(body.key)}

    return app
