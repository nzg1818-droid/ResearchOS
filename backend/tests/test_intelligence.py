import fitz
from sqlalchemy import select, text
from app.db import initialize, Work, File, SourceHit
from app.intelligence.models import Document, Page, Block, Chunk
from app.intelligence.parsing import parse, retrieve
from app.importer import import_pdf

def paper(path):
    pdf=fitz.open()
    for heading, body in [('Abstract','NiFe catalyst improves oxygen evolution.'), ('Electrochemical Measurements','The overpotential was 250 mV at 100 mA cm-2 in 1 M KOH.'), ('Characterization','Ex situ XPS showed nickel oxidation. Working phase was not determined.')]:
        p=pdf.new_page();p.insert_text((60,60),heading);p.insert_text((60,100),body)
    pdf.save(path);pdf.close()

def test_parse_pages_geometry_cache_and_scoped_fts(tmp_path):
    root=tmp_path/'library';engine,sessions=initialize(root)
    source=tmp_path/'paper.pdf';paper(source)
    with sessions.begin() as s:
        result=import_pdf(s,root,source,None)
        file=s.scalar(select(File));doc=parse(s,root,file.work_id)
        assert doc.parse_status=='Parsed' and doc.page_count==3
        assert [p.page_number for p in s.scalars(select(Page))]==[1,2,3]
        blocks=list(s.scalars(select(Block)))
        assert all(0<=v<=1 for b in blocks for v in b.bbox)
        ids=list(s.scalars(select(Chunk.id)))
        assert parse(s,root,file.work_id).id==doc.id
        assert list(s.scalars(select(Chunk.id)))==ids
        matches=retrieve(s,file.work_id,doc.id,'overpotential')
        assert matches and matches[0].page_start==2
        assert not retrieve(s,file.work_id+1,doc.id,'overpotential')
    engine.dispose()

def test_abstract_scanned_failure_and_changed_source(tmp_path):
    root=tmp_path/'library';engine,sessions=initialize(root)
    with sessions.begin() as s:
        w=Work(title='Abstract paper',authors=[]);s.add(w);s.flush()
        hit=SourceHit(work_id=w.id,source='crossref',raw={'abstract':'Catalyst abstract'});s.add(hit);s.flush()
        first=parse(s,root,w.id)
        assert first.parse_status=='Abstract only' and first.file_id is None
        hit.raw={'abstract':'Changed catalyst abstract'};s.flush()
        assert parse(s,root,w.id).text_hash!=first.text_hash
        scan=tmp_path/'scan.pdf';pdf=fitz.open();pdf.new_page();pdf.save(scan);pdf.close()
        import_pdf(s,root,scan,w.id)
        assert parse(s,root,w.id).parse_status=='Needs OCR'
        file=s.scalar(select(File));(root/file.path).write_bytes(b'broken PDF')
        assert parse(s,root,w.id).parse_status=='Parse failed'
    engine.dispose()

def test_0002_upgrade_preserves_records_and_creates_backup(tmp_path):
    import sqlite3
    root=tmp_path/'library';engine,sessions=initialize(root)
    with sessions.begin() as s:s.add(Work(title='Keep me',authors=[]))
    engine.dispose()
    # Model an actual 0002 database by removing only the new empty schema.
    names=['paper_answers','paper_questions','verification_decisions','evidence_anchors','paper_extractions','extraction_runs','ai_runs','ai_provider_configs','document_chunks','document_blocks','document_pages','paper_documents']
    with sqlite3.connect(root/'researchos.db') as db:
        db.execute('DROP TABLE paper_chunks_fts')
        for name in names:db.execute('DROP TABLE '+name)
        db.execute("UPDATE alembic_version SET version_num='0002'")
    engine,sessions=initialize(root)
    with sessions() as s:
        assert s.scalar(select(Work)).title=='Keep me'
        assert s.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0003'
    assert list((root/'migration-backups').glob('*-0002.db'))
    engine.dispose()


import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from test_core import wait_job

@pytest.fixture
def intelligence(tmp_path,monkeypatch):
    secrets={}
    monkeypatch.setattr('keyring.get_password',lambda service,key:secrets.get((service,key)))
    monkeypatch.setattr('keyring.set_password',lambda service,key,value:secrets.__setitem__((service,key),value))
    monkeypatch.setattr('keyring.delete_password',lambda service,key:secrets.pop((service,key),None))
    app=create_app(tmp_path/'library','t')
    source=tmp_path/'paper.pdf';paper(source)
    with app.state.sessions.begin() as s:
        import_pdf(s,app.state.data,source,None)
        work_id=s.scalar(select(File.work_id))
    with TestClient(app,headers={'X-ResearchOS-Token':'t'}) as client:yield client,app,work_id,secrets

def run_batch(client,ids,action='parse',**kwargs):
    response=client.post('/intelligence/batches',json={'work_ids':ids,'action':action,**kwargs})
    assert response.status_code==200,response.text
    return wait_job(client,response.json()['job_id'])

def test_extraction_evidence_cache_review_export_and_ask(intelligence):
    client,app,id,secrets=intelligence
    assert run_batch(client,[id])['state']=='completed'
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'deterministic'}).json()
    result=run_batch(client,[id],'full_text',provider_id=cfg['id'])
    assert result['state']=='completed',result
    overview=client.get(f'/intelligence/works/{id}').json()
    extraction=overview['extractions'][0]
    assert extraction['effective']['performance'][0]['reported_value']['value']==250
    path='performance.0.reported_value'
    assert extraction['field_states'][path]['status']=='Evidence matched'
    assert run_batch(client,[id],'full_text',provider_id=cfg['id'])['result']['papers'][str(id)]['state']=='cached'
    url=f"/intelligence/extractions/{extraction['id']}/verify"
    assert client.post(url,json={'field_path':path,'action':'edit','value':999}).status_code==422
    review=client.post(url,json={'field_path':path,'action':'accept','note':'Checked source'});assert review.status_code==200,review.text
    knowledge=client.post(f"/intelligence/extractions/{extraction['id']}/knowledge",json={'field_path':path,'action':'accept'})
    assert knowledge.status_code==200,knowledge.text
    for format in ['json','csv']:
        exported=client.post('/intelligence/export',json={'work_ids':[id],'format':format}).json()
        assert '250' in exported['content'] and 'performance.0.reported_value' in exported['content']
    answer=client.post(f'/intelligence/works/{id}/ask',json={'question':'overpotential'}).json()
    assert answer['anchors'][0]['page']==2
    missing=client.post(f'/intelligence/works/{id}/ask',json={'question':'pineapple quasar'}).json()
    assert missing['text']=='Not found in this paper'
    assert client.post(f"/intelligence/answers/{missing['id']}/knowledge").status_code==422
    assert len(client.get(f'/intelligence/works/{id}').json()['questions'])==2

def test_cloud_consent_endpoint_and_secret_boundary(intelligence,tmp_path):
    client,app,id,secrets=intelligence
    bad=client.post('/intelligence/providers',json={'name':'Unsafe','provider_type':'openai-compatible','endpoint':'http://example.com','model':'x'})
    assert bad.status_code==422
    cfg=client.post('/intelligence/providers',json={'name':'Cloud','provider_type':'openai-compatible','endpoint':'https://example.com/v1','model':'x','key':'AI-SECRET-CANARY'}).json()
    assert 'AI-SECRET-CANARY' not in str(cfg)
    assert client.post('/intelligence/batches',json={'work_ids':[id],'action':'full_text','provider_id':cfg['id']}).status_code==403
    assert secrets
    backup=tmp_path/'backup.zip'
    assert client.post('/storage/backup',json={'path':str(backup)}).status_code==200
    import zipfile
    with zipfile.ZipFile(backup) as z:
        assert all(b'AI-SECRET-CANARY' not in z.read(n) for n in z.namelist())
    assert 'AI-SECRET-CANARY' not in (app.state.data/'researchos.log').read_text()

def test_numeric_unit_and_foreign_anchor_rejected(intelligence):
    client,app,id,secrets=intelligence
    run_batch(client,[id])
    from app.intelligence.evidence import check
    with app.state.sessions() as s:
        doc=s.scalar(select(Document));c=s.scalar(select(Chunk).where(Chunk.text.contains('250')))
        field={'value':999,'origin':'source_reported','evidence':[{'chunk_id':c.id,'page':2,'quote':c.text}]}
        assert check(s,doc,field,'performance.0.reported_value')[0]=='Needs review'
        field['value']='kg'
        assert check(s,doc,field,'performance.0.reported_unit')[0]=='Needs review'
        field['value']=250;field['evidence'][0]['page']=99
        assert check(s,doc,field,'performance.0.reported_value')[0]=='Needs review'
        field['evidence'][0]['chunk_id']='nonexistent'
        assert check(s,doc,field,'performance.0.reported_value')[0]=='Needs review'


def test_provider_protocols_and_sanitized_failures(intelligence):
    import asyncio,httpx
    from app.intelligence.models import ProviderConfig
    from app.intelligence.providers import provider,ProviderError
    client,app,id,secrets=intelligence
    for kind,endpoint in [('openai-compatible','https://example.com/v1'),('ollama','http://127.0.0.1:11434')]:
        c=ProviderConfig(id=90,name='test',provider_type=kind,endpoint=endpoint,model='test',timeout=5,max_output_tokens=1000,enabled=True)
        calls=[]
        def route(r):
            calls.append(r)
            if r.method=='GET':return httpx.Response(200,json={'models':[{'name':'test'}]} if kind=='ollama' else {'data':[{'id':'test'}]})
            import json
            body=json.loads(r.content);assert body['model']=='test'
            return httpx.Response(200,json={'message':{'content':'{}'},'thinking':'MUST NOT PERSIST'} if kind=='ollama' else {'choices':[{'message':{'content':'{}','reasoning_content':'MUST NOT PERSIST'}}]})
        adapter=provider(c,httpx.MockTransport(route))
        assert asyncio.run(adapter.health())['ok']
        assert asyncio.run(adapter.structured('test',{},{})).content=={}
        assert calls[-1].url.path.endswith('/api/chat' if kind=='ollama' else '/chat/completions')
        for code,message in [(401,'auth error'),(429,'rate limit'),(500,'request failed')]:
            adapter=provider(c,httpx.MockTransport(lambda r:httpx.Response(code,text='SECRET-CANARY')))
            with pytest.raises(ProviderError,match=message) as error:asyncio.run(adapter.health())
            assert 'SECRET-CANARY' not in str(error.value)
        def timeout(r):raise httpx.ReadTimeout('PRIVATE',request=r)
        with pytest.raises(ProviderError,match='timeout'):asyncio.run(provider(c,httpx.MockTransport(timeout)).health())

def test_invalid_schema_failure_isolated_and_force_versions(intelligence,monkeypatch):
    from app.intelligence.providers import MockProvider,Result
    from app.intelligence import service
    client,app,id,secrets=intelligence
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'test'}).json()
    original=MockProvider.structured
    async def invalid(self,*args):return Result({'hallucinated_field':'PRIVATE'}, {})
    monkeypatch.setattr(MockProvider,'structured',invalid)
    result=run_batch(client,[id],'full_text',provider_id=cfg['id'])
    assert result['result']['papers'][str(id)]['error']=='Invalid structured output'
    assert client.get(f'/intelligence/works/{id}').json()['extractions']==[]
    monkeypatch.setattr(MockProvider,'structured',original)
    first=run_batch(client,[id],'full_text',provider_id=cfg['id'])
    second=run_batch(client,[id],'full_text',provider_id=cfg['id'],force=True)
    assert first['result']['papers'][str(id)]['extraction_id']!=second['result']['papers'][str(id)]['extraction_id']
    with app.state.sessions() as s:
        from app.intelligence.models import ProviderConfig
        doc=s.scalar(select(Document));config=s.get(ProviderConfig,cfg['id']);key=service.cache_key(doc,config,'full_text')
        monkeypatch.setattr(service,'SCHEMA_VERSION','changed');assert key!=service.cache_key(doc,config,'full_text')
        monkeypatch.setattr(service,'SCHEMA_VERSION','paper-intelligence-1')
        monkeypatch.setattr(service,'PROMPT_VERSION','changed');assert key!=service.cache_key(doc,config,'full_text')

def test_scientific_rules_abstract_and_unknowns():
    from app.intelligence.schema import PaperExtraction
    from app.intelligence.evidence import scientific_issues
    payload=PaperExtraction.model_validate({'synthesis':[{'temperature':{'value':900}}],'electrochemistry':[{}],'performance':[{'metric':{'value':'overpotential'},'reported_value':{'value':250},'reported_unit':{'value':'kg'}}],'mechanism':[{'claim':{'value':'Ex-situ XPS supports a mechanism'}}]}).model_dump()
    issues=scientific_issues(payload,'full_text')
    assert 'performance.0.reported_value' in issues
    assert payload['electrochemistry'][0]['ir_correction']['value'] is None
    assert payload['electrochemistry'][0]['normalization_basis']['value'] is None
    assert payload['electrochemistry'][0]['reference_conversion']['value'] is None
    assert 'ex-situ only' in payload['mechanism'][0]['limitation']['value']
    scientific_issues(payload,'abstract')
    assert payload['synthesis'][0]['temperature']['value'] is None
    assert payload['performance'][0]['reported_value']['value'] is None

def test_fifty_paper_batch_is_bounded_resumable_and_isolates_errors(intelligence):
    import tracemalloc
    from app.db import Job
    from sqlalchemy import func
    client,app,id,secrets=intelligence
    ids=[]
    with app.state.sessions.begin() as s:
        for index in range(49):
            w=Work(title=f'Abstract {index}',authors=[]);s.add(w);s.flush();ids.append(w.id)
            if index!=0:s.add(SourceHit(work_id=w.id,source='fixture',raw={'abstract':f'Catalyst study {index}.'}))
    tracemalloc.start()
    result=run_batch(client,[id]+ids)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(result['result']['papers'])==50
    assert result['result']['papers'][str(ids[0])]['state']=='failed'
    assert result['result']['papers'][str(id)]['state']=='completed'
    assert peak<100*1024*1024
    with app.state.sessions.begin() as s:
        job=s.get(Job,result['id']);job.state='interrupted'
    assert client.post(f"/intelligence/jobs/{result['id']}/control",json={'action':'resume'}).status_code==200
    finished=wait_job(client,result['id'])
    with app.state.sessions() as s:assert s.scalar(select(func.count()).select_from(Document))==50
    assert client.post(f"/jobs/{result['id']}/retry").status_code==422

def test_metadata_abstract_levels_and_restart_review(intelligence):
    from app.intelligence.models import Extraction,Decision
    client,app,id,secrets=intelligence
    run_batch(client,[id],'metadata')
    assert client.get(f'/intelligence/works/{id}').json()['extractions'][0]['run']['extraction_level']=='metadata'
    with app.state.sessions.begin() as s:s.add(SourceHit(work_id=id,source='fixture',raw={'abstract':'A catalyst paper abstract.'}))
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'test'}).json()
    run_batch(client,[id],'abstract',provider_id=cfg['id'])
    overview=client.get(f'/intelligence/works/{id}').json();e=overview['extractions'][0]
    assert e['run']['extraction_level']=='abstract'
    response=client.post(f"/intelligence/extractions/{e['id']}/verify",json={'field_path':'one_minute_brief','action':'edit','value':'A catalyst paper abstract.','note':'Human correction'})
    assert response.status_code==200,response.text
    engine,sessions=initialize(app.state.data)
    with sessions() as s:
        from app.intelligence.service import view
        restored=view(s,s.get(Extraction,e['id']))
        assert restored['field_states']['one_minute_brief']['status']=='User corrected'
        assert restored['decisions'][0]['created_at']
        assert s.get(Extraction,e['id']).payload==e['payload']
    engine.dispose()


def test_mismatched_output_never_becomes_verified(intelligence,monkeypatch):
    from app.intelligence.providers import MockProvider
    client,app,id,secrets=intelligence
    original=MockProvider.structured
    async def mismatch(self,system,payload,schema):
        result=await original(self,system,payload,schema)
        if result.content.get('performance'):result.content['performance'][0]['reported_value']['value']=999
        return result
    monkeypatch.setattr(MockProvider,'structured',mismatch)
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'test'}).json()
    run_batch(client,[id],'full_text',provider_id=cfg['id'])
    e=client.get(f'/intelligence/works/{id}').json()['extractions'][0];path='performance.0.reported_value'
    assert e['field_states'][path]['status']=='Needs review'
    assert client.post(f"/intelligence/extractions/{e['id']}/verify",json={'field_path':path,'action':'accept'}).status_code==422
    rejected=client.post(f"/intelligence/extractions/{e['id']}/verify",json={'field_path':path,'action':'reject','note':'Source says 250'})
    assert rejected.json()['field_states'][path]['status']=='Rejected'
    corrected=client.post(f"/intelligence/extractions/{e['id']}/verify",json={'field_path':path,'action':'edit','value':250})
    assert corrected.status_code==200
    assert corrected.json()['payload']['performance'][0]['reported_value']['value']==999
    assert corrected.json()['effective']['performance'][0]['reported_value']['value']==250

def test_all_verified_full_text_promotes_without_losing_run(intelligence):
    from app.intelligence.schema import fields
    client,app,id,secrets=intelligence
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'test'}).json()
    run_batch(client,[id],'full_text',provider_id=cfg['id'])
    e=client.get(f'/intelligence/works/{id}').json()['extractions'][0]
    for path,field in fields(e['effective']):
        if field['value'] is not None:
            r=client.post(f"/intelligence/extractions/{e['id']}/verify",json={'field_path':path,'action':'accept'})
            assert r.status_code==200,r.text
    v=client.get(f'/intelligence/works/{id}').json()['extractions'][0]
    assert v['run']['extraction_level']=='full_text_verified'
    assert v['run']['id']==e['run']['id'] and v['payload']==e['payload']

def test_pause_cancel_and_resume_batch(intelligence,monkeypatch):
    import asyncio,time
    from app.intelligence.providers import MockProvider
    client,app,id,secrets=intelligence
    cfg=client.post('/intelligence/providers',json={'name':'Mock','provider_type':'mock','model':'test','concurrency':1}).json()
    original=MockProvider.structured
    async def slow(self,*args):
        await asyncio.sleep(.02)
        return await original(self,*args)
    monkeypatch.setattr(MockProvider,'structured',slow)
    ids=[id]
    with app.state.sessions.begin() as s:
        for index in range(4):
            w=Work(title=f'Batch abstract {index}',authors=[]);s.add(w);s.flush();ids.append(w.id)
            s.add(SourceHit(work_id=w.id,source='fixture',raw={'abstract':'Catalyst abstract'}))
        s.add(SourceHit(work_id=id,source='fixture',raw={'abstract':'Catalyst abstract'}))
    job=client.post('/intelligence/batches',json={'work_ids':ids,'action':'abstract','provider_id':cfg['id']}).json()['job_id']
    assert client.post(f'/intelligence/jobs/{job}/control',json={'action':'pause'}).status_code==200
    time.sleep(.4)
    assert client.get(f'/jobs/{job}').json()['state']=='paused'
    assert client.post(f'/intelligence/jobs/{job}/control',json={'action':'cancel'}).status_code==200
    assert client.get(f'/jobs/{job}').json()['state']=='cancelled'
    assert client.post(f'/intelligence/jobs/{job}/control',json={'action':'resume'}).status_code==200
    assert wait_job(client,job)['state']=='completed'
