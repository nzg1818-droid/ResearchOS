import asyncio
from pathlib import Path
import time
import pytest
import pymupdf
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.db import Work, File, Job, initialize
from app.canonical import upsert, doi
from app.schemas import Hit, Search
from app.importer import import_pdf
from app.adapters import Crossref, OpenAlex, get_json

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / 'data', 'test'), headers={'X-ResearchOS-Token':'test'}) as c:
        yield c

def make_pdf(path, title='A reproducible research paper', identifier='10.1234/test'):
    doc=pymupdf.open()
    for i in range(3):
        page=doc.new_page()
        page.insert_text((72,72),title)
        page.insert_text((72,110),identifier)
        page.insert_text((72,160),f'Page {i+1}: Nickel iron catalysts improve oxygen evolution.')
    doc.set_metadata({'title':title})
    doc.save(path);doc.close()

def wait_job(c,id):
    for _ in range(200):
        j=c.get(f'/jobs/{id}').json()
        if j['state'] not in ('queued','running'):return j
        time.sleep(.025)
    raise AssertionError('Task did not finish')

def test_doi_normalization():
    assert doi(' HTTPS://doi.org/10.1234/ABC ')=='10.1234/abc'
    assert doi('doi:10.1234%2FABC')=='10.1234/abc'

def test_canonical_priority_conflicts(tmp_path):
    engine,session=initialize(tmp_path)
    with session.begin() as s:
        a=upsert(s,Hit(source='openalex',source_id='W1',doi='HTTPS://doi.org/10.1234/ABC',title='Catalyst paper',authors=['Alice'],year=2024,citations=1))
        b=upsert(s,Hit(source='crossref',source_id='10.1234/abc',doi='10.1234/abc',title='Catalyst paper',authors=['Alice'],year=2024,citations=2))
        assert a.id==b.id and b.citations==2 and b.conflicts
        c=upsert(s,Hit(source='other',source_id='1',title='Catalyst PAPER!',authors=['Alice'],year=2024))
        assert a.id==c.id
        distinct=upsert(s,Hit(source='other',source_id='2',doi='10.1234/different',title='Catalyst paper',authors=['Alice'],year=2024))
        assert distinct.id!=a.id
        assert len(list(s.scalars(select(Work))))==2
    engine.dispose()

def test_pdf_matching_hash_and_wrong_work(tmp_path):
    engine,session=initialize(tmp_path/'data')
    path=tmp_path/'paper.pdf';make_pdf(path)
    with session.begin() as s:
        w=upsert(s,Hit(source='crossref',source_id='test',doi='10.1234/test',title='Paper'))
        result=import_pdf(s,tmp_path/'data',path)
        assert result['work_id']==w.id
        assert import_pdf(s,tmp_path/'data',path)['duplicate']
        other=upsert(s,Hit(source='crossref',source_id='other',doi='10.1234/other',title='Other'))
        with pytest.raises(ValueError,match='already belongs'):
            import_pdf(s,tmp_path/'data',path,other.id)
        assert len(list(s.scalars(select(File))))==1
    engine.dispose()

def test_late_doi_bridge_keeps_library_and_pdf_backlinks(tmp_path):
    engine, sessions = initialize(tmp_path / 'data')
    path = tmp_path / 'p.pdf'; make_pdf(path, identifier='No DOI in this example')
    with sessions.begin() as s:
        first = upsert(s, Hit(source='openalex', source_id='W1', title='Incomplete source title'))
        first.notes = 'User note'; first.tags = ['OER']; first.starred = True
        f = import_pdf(s, tmp_path / 'data', path, first.id)
        canonical = upsert(s, Hit(source='crossref', source_id='10.1234/late', doi='10.1234/late', title='Corrected title'))
        result = upsert(s, Hit(source='openalex', source_id='W1', doi='10.1234/late', title='Corrected title'))
        assert result.id == canonical.id
        assert len(list(s.scalars(select(Work)))) == 1
        assert result.in_library and result.starred and result.notes == 'User note'
        assert s.get(File, f['file_id']).work_id == result.id
    engine.dispose()

def test_import_folder_survives_bad_pdf_and_deduplicates(client,tmp_path):
    folder=tmp_path/'papers';folder.mkdir()
    for i in range(100):make_pdf(folder/f'{i}.pdf',f'Paper {i}',f'10.1234/paper{i}')
    (folder/'broken.pdf').write_text('not pdf')
    job=wait_job(client,client.post('/imports',json={'paths':[str(folder)]}).json()['job_id'])
    assert job['state']=='partial'
    assert len(job['result']['imports'])==100 and len(job['result']['errors'])==1
    job2=wait_job(client,client.post(f"/jobs/{job['id']}/retry").json()['job_id'])
    assert all(x['duplicate'] for x in job2['result']['imports'])
    assert len(client.get('/works?library=true').json())==100

def test_annotation_material_and_restart(tmp_path):
    data=tmp_path/'data';path=tmp_path/'p.pdf';make_pdf(path)
    with TestClient(create_app(data,'token'),headers={'X-ResearchOS-Token':'token'}) as c:
        job=wait_job(c,c.post('/imports',json={'paths':[str(path)]}).json()['job_id'])
        f=job['result']['imports'][0]
        c.patch(f"/works/{f['work_id']}",json={'notes':'Mechanistic catalyst evidence','tags':['OER'],'starred':True,'status':'reading'})
        col=c.post('/collections',json={'name':'Electrolysis'}).json()
        assert c.post(f"/collections/{col['id']}/works/{f['work_id']}").status_code==200
        payload={'file_id':f['file_id'],'page':2,'text':'Nickel iron catalysts','context':'Page 2 context','rects':[{'x':.1,'y':.2,'width':.3,'height':.02}],'note':'Important','tags':['OER'],'kind':'evidence'}
        annotation=c.post('/annotations',json=payload).json()
        assert annotation['page']==2
        assert c.post('/annotations',json={**payload,'page':99}).status_code==422
        assert len(c.get('/works?q=Mechanistic').json())==1
    with TestClient(create_app(data,'new-token'),headers={'X-ResearchOS-Token':'new-token'}) as c:
        materials=c.get('/materials').json();assert len(materials)==1
        m=materials[0];assert m['annotation']['id']==annotation['id']
        assert m['provenance']['doi']=='10.1234/test'
        assert m['provenance']['page']==2 and m['provenance']['rects']==payload['rects']
        assert c.get(f"/files/{f['file_id']}/content").content.startswith(b'%PDF')
        w=c.get(f"/works/{f['work_id']}").json()
        assert w['starred'] and w['notes']=='Mechanistic catalyst evidence' and w['collections']==[col['id']]
        assert c.get('/health',headers={'X-ResearchOS-Token':'token'}).status_code==401

def test_search_job_with_partial_provider_failure(client,monkeypatch):
    async def fake(_):
        return [Hit(source='crossref',source_id='x',doi='10.1234/x',title='Found')],{'openalex':'Rate limited'},{'crossref':1}
    monkeypatch.setattr('app.main.federated',fake)
    j=wait_job(client,client.post('/search',json={'query':'nickel'}).json()['job_id'])
    assert j['state']=='partial' and j['result']['errors']['openalex']=='Rate limited'
    assert len(j['result']['work_ids'])==1

def test_invalid_search_and_auth(client):
    assert client.post('/search',json={'query':'x','start':'2025-01-01','end':'2024-01-01'}).status_code==422
    assert client.post('/search',json={'query':' '}).status_code==422
    assert client.get('/works',headers={'X-ResearchOS-Token':''}).status_code==401

def test_interrupted_jobs_recover(tmp_path):
    e,sessions=initialize(tmp_path)
    with sessions.begin() as s:s.add(Job(kind='search',state='running',request={'query':'x'}))
    e.dispose()
    e,sessions=initialize(tmp_path)
    with sessions() as s:
        j=s.scalar(select(Job));assert j.state=='interrupted' and j.request=={'query':'x'}
    e.dispose()

def test_adapters_real_response_shapes_and_parameters(monkeypatch):
    monkeypatch.setattr('keyring.get_password',lambda *_:None)
    seen=[]
    def route(r):
        seen.append(str(r.url))
        if 'crossref' in r.url.host:
            item={'DOI':'10.1234/ABC','title':['Exact title'],'author':[{'given':'Alice','family':'Smith'}],'published':{'date-parts':[[2024,2,3]]},'container-title':['Journal'],'resource':{'primary':{'URL':'https://publisher.example/paper'}}}
            return httpx.Response(200,json={'message':item if '/10.' in r.url.path else {'items':[item]}})
        if r.url.path=='/authors':return httpx.Response(200,json={'results':[{'id':'https://openalex.org/A1'}]})
        return httpx.Response(200,json={'results':[{'id':'https://openalex.org/W1','doi':'https://doi.org/10.1234/ABC','title':'Exact title','publication_year':2024,'publication_date':'2024-02-03','authorships':[{'author':{'display_name':'Alice Smith'}}],'locations':[{'is_oa':True,'pdf_url':'https://repository.example/paper.pdf','license':'cc-by'}]}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(route)) as c:
            for mode,q in [('keyword','catalyst'),('title','Exact title'),('doi','10.1234/ABC'),('author','Alice Smith')]:
                request=Search(query=q,mode=mode,start='2024-01-01',end='2024-12-31')
                for adapter in (Crossref(c),OpenAlex(c)):
                    hits=await adapter.search(request);assert len(hits)==1 and hits[0].title=='Exact title'
            assert not await Crossref(c).search(Search(query='wrong title',mode='title'))
    asyncio.run(run())
    assert any('query.author=' in x for x in seen)
    assert any('authorships.author.id' in x for x in seen)
    assert any('from-pub-date' in x for x in seen)

def test_retry_rate_limit_then_success():
    calls=[]
    def route(_):
        calls.append(1)
        return httpx.Response(429,headers={'Retry-After':'0'}) if len(calls)==1 else httpx.Response(200,json={'ok':True})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(route)) as c:
            assert await get_json(c,'https://example.org')=={'ok':True}
    asyncio.run(run());assert len(calls)==2
