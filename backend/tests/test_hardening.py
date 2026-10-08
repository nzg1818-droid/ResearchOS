import json
import shutil
import sqlite3
import time
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, event
from app.db import initialize, Work, File, SourceHit
from app.main import create_app
from app.canonical import upsert
from app.schemas import Hit
from app.storage import Storage
from app.textutils import local_context
from app.importer import import_pdf
from test_core import make_pdf, wait_job

def test_phase1_migration_and_move_preserves_backlinks(tmp_path):
    root=tmp_path/'old';root.mkdir();(root/'files').mkdir()
    source=tmp_path/'original.pdf';make_pdf(source)
    digest=Storage.hash(source);managed=root/'files'/f'{digest}.pdf';shutil.copyfile(source,managed)
    engine=create_engine('sqlite:///'+(root/'researchos.db').as_posix())
    cfg=Config('alembic.ini');cfg.set_main_option('script_location','migrations')
    with engine.begin() as c:
        cfg.attributes['connection']=c;command.upgrade(cfg,'0001')
        c.execute(text("INSERT INTO works(id,doi,title,authors,oa_locations,conflicts,in_library,starred,status,notes,tags,created_at) VALUES(1,'10.1234/test','Legacy title','[\"Alice\"]','[]','[]',1,0,'reading','Keep note','[]','old')"))
        c.execute(text("INSERT INTO files(id,work_id,sha256,name,path,pages,created_at) VALUES(1,1,:hash,'old.pdf',:path,3,'old')"),{'hash':digest,'path':str(managed)})
        c.execute(text("INSERT INTO annotations(id,work_id,file_id,page,text,context,rects,note,tags,created_at) VALUES(1,1,1,2,'selected','legacy context','[]','keep','[]','old')"))
        c.execute(text("INSERT INTO materials(id,annotation_id,kind,provenance,created_at) VALUES(1,1,'evidence',:p,'old')"),{'p':json.dumps({'file_id':1,'page':2,'work_id':1})})
    engine.dispose()
    engine,sessions=initialize(root)
    assert len(list((root/'migration-backups').glob('*.db')))==1
    with sessions() as s:
        assert s.get(File,1).path==f'files/{digest}.pdf'
        assert s.get(Work,1).notes=='Keep note'
    engine.dispose()
    moved=tmp_path/'moved';shutil.copytree(root,moved)
    # The old folder is deliberately absent to expose any absolute-path fallback.
    root.rename(tmp_path/'old-unavailable')
    with TestClient(create_app(moved,'t'),headers={'X-ResearchOS-Token':'t'}) as c:
        assert c.get('/files/1/content').content==source.read_bytes()
        material=c.get('/materials').json()[0]
        assert material['annotation']['page']==2
        assert material['annotation']['context']=='legacy context'
        assert material['provenance']['file_id']==1
    assert Storage.hash(source)==digest

def test_indexed_matching_10000(tmp_path):
    engine,sessions=initialize(tmp_path/'data')
    with sessions.begin() as s:
        s.add_all([Work(title=f'Paper {i}',authors=['Alice'],year=2024) for i in range(10000)])
    statements=[]
    @event.listens_for(engine,'before_cursor_execute')
    def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    source=tmp_path/'p.pdf';make_pdf(source,'Paper 9876','No DOI')
    started=time.perf_counter()
    with sessions.begin() as s:
        result=import_pdf(s,tmp_path/'data',source)
        assert s.get(Work,result['work_id']).title=='Paper 9876'
        match=upsert(s,Hit(source='test',source_id='9876',title='Paper 9876',authors=['Alice'],year=2024))
        assert match.id==result['work_id']
        plan=s.execute(text("EXPLAIN QUERY PLAN SELECT id FROM works WHERE title_key='paper9876' AND author_key='alice' AND year=2024")).all()
        assert any('ix_works_title_identity' in str(p) for p in plan)
    elapsed=time.perf_counter()-started
    assert elapsed<3, f'Indexed PDF+metadata match target <3 seconds; actual {elapsed:.3f}s'
    assert all('WHERE' in sql.upper() for sql in statements if sql.lstrip().upper().startswith('SELECT') and 'FROM works' in sql)
    engine.dispose()

def test_repeated_search_reuses_snapshot_and_retains_runs(tmp_path,monkeypatch):
    async def results(_): return [Hit(source='crossref',source_id='x',title='Title',raw={'title':'Title'})],{}, {'crossref':1}
    monkeypatch.setattr('app.main.federated',results)
    app=create_app(tmp_path,'t')
    with TestClient(app,headers={'X-ResearchOS-Token':'t'}) as c:
        for _ in range(3): assert wait_job(c,c.post('/search',json={'query':'Title'}).json()['job_id'])['state']=='completed'
        runs=c.get('/search-runs').json()
        assert len(runs)==3 and all(len(r['hits'])==1 for r in runs)
        assert len({r['hits'][0]['source_hit_id'] for r in runs})==1
        with app.state.sessions() as s: assert len(s.scalars(select(SourceHit)).all())==1

def test_bounded_annotation_context():
    context=local_context('A'*400+' selected phrase '+'Z'*400,'selected phrase')
    assert len(context['before'])==240 and len(context['after'])==240
    assert context['context']==context['before']+'selected phrase'+context['after']

@pytest.mark.parametrize('path',['../outside.pdf','files/../../outside.pdf','C:/private.pdf','/files/a.pdf'])
def test_storage_rejects_escape(tmp_path,path):
    with pytest.raises(ValueError): Storage(tmp_path).resolve(path)
