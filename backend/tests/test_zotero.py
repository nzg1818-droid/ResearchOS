import copy
import json
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.db import Work, File, initialize
from app.phase2_models import ExternalAttachment
from app.integrations.zotero.mapping import from_remote
from test_core import make_pdf

def remote(key='ITEM0001',doi='10.1234/zotero'):
    return {'key':key,'version':1,'data':{'key':key,'version':1,'itemType':'journalArticle','title':'Catalyst paper','DOI':doi,'creators':[{'creatorType':'author','name':'Alice'}],'date':'2024','publicationTitle':'Journal','tags':[{'tag':'OER'}],'extra':'','collections':['COLL0001'],'url':'https://example.org/paper'}}

class Server:
    def __init__(self):self.items={'ITEM0001':remote()};self.version=1;self.calls=[];self.race=False;self.pdf=b''
    def route(self,r):
        self.calls.append(r);path=r.url.path;headers={'Last-Modified-Version':str(self.version)}
        if r.method=='GET' and path.endswith('/collections'):return httpx.Response(200,json=[{'key':'COLL0001','version':1,'data':{'name':'Test collection','parentCollection':False}}],headers=headers)
        if path.endswith('/children'):return httpx.Response(200,json=[i for i in self.items.values() if i['data'].get('parentItem')==path.split('/')[-2]],headers=headers)
        if path.endswith('/file'):
            if r.method=='GET':return httpx.Response(200,content=self.pdf,headers=headers)
            return httpx.Response(200,json={'exists':1},headers=headers)
        if r.method=='GET' and path.endswith('/items'):
            items=list(self.items.values());since=int(r.url.params.get('since','0'));items=[i for i in items if i['version']>since]
            return httpx.Response(200,json=items[:int(r.url.params.get('limit','100'))],headers=headers)
        if r.method=='POST' and path.endswith('/items'):
            data=json.loads(r.content)[0];key=f'NEW{len(self.items):05}';self.version+=1;item={'key':key,'version':self.version,'data':data};self.items[key]=item
            return httpx.Response(200,json={'successful':{'0':item},'failed':{}},headers={'Last-Modified-Version':str(self.version)})
        key=path.split('/')[-1]
        if key not in self.items:return httpx.Response(404)
        item=self.items[key]
        if r.method=='GET':return httpx.Response(200,json=copy.deepcopy(item),headers=headers)
        if r.method=='PATCH':
            if self.race:self.race=False;self.edit(key,title='Concurrent remote edit');return httpx.Response(412)
            if r.headers.get('If-Unmodified-Since-Version')!=str(item['version']):return httpx.Response(412)
            self.edit(key,**json.loads(r.content));return httpx.Response(204,headers={'Last-Modified-Version':str(self.version)})
        return httpx.Response(400)
    def edit(self,key='ITEM0001',**values):self.version+=1;self.items[key]['version']=self.version;self.items[key]['data'].update(values)

@pytest.fixture
def environment(tmp_path,monkeypatch):
    secrets={}
    monkeypatch.setattr('keyring.get_password',lambda service,key:secrets.get((service,key)))
    monkeypatch.setattr('keyring.set_password',lambda service,key,value:secrets.__setitem__((service,key),value))
    monkeypatch.setattr('keyring.delete_password',lambda service,key:secrets.pop((service,key),None))
    server=Server();app=create_app(tmp_path/'library','t');app.state.zotero_transport=httpx.MockTransport(server.route)
    with TestClient(app,headers={'X-ResearchOS-Token':'t'}) as client:
        yield client,server,app,secrets

def connect(client,mode='web'):
    response=client.post('/zotero/connections',json={'mode':mode,'library_id':'123' if mode=='web' else '0','key':'SECRET-CANARY-ZOTERO'})
    assert response.status_code==200,response.text
    return response.json()['id']

def imported(client,id):
    result=client.post(f'/zotero/{id}/import',json={'collections':['COLL0001']});assert result.status_code==200,result.text
    return client.get('/works?library=true').json()[0]

@pytest.mark.parametrize('mode',['local','web'])
def test_import_metadata_children_and_repeat(environment,mode):
    c,server,app,secrets=environment
    server.items['NOTE0001']={'key':'NOTE0001','version':1,'data':{'itemType':'note','parentItem':'ITEM0001','note':'<p>Zotero source note</p>'}}
    server.items['FILE0001']={'key':'FILE0001','version':1,'data':{'itemType':'attachment','parentItem':'ITEM0001','contentType':'application/pdf','filename':'paper.pdf'}}
    id=connect(c,mode);assert c.post(f'/zotero/{id}/test').status_code==200
    preview=c.post(f'/zotero/{id}/preview',json={'collections':['COLL0001']}).json();assert preview['summary']['created']==1
    work=imported(c,id)
    assert work['tags']==['OER'] and work['collections']
    assert work['zotero_notes'][0]['content']=='<p>Zotero source note</p>'
    assert work['external_attachments'] and not work['files']
    assert c.post(f'/zotero/{id}/import',json={}).json()['skipped']==1
    assert len(c.get('/works?library=true').json())==1

@pytest.mark.parametrize('identifier,expected',[('10.1234/zotero','matched'),(None,'matched'),('10.1234/different','conflicts')])
def test_import_matching_and_explicit_doi_conflict(environment,identifier,expected):
    c,server,app,secrets=environment
    if identifier is None:server.items['ITEM0001']['data']['DOI']=''
    c.post('/works',json={'title':'Catalyst paper','authors':['Alice'],'year':2024,'doi':identifier})
    id=connect(c);result=c.post(f'/zotero/{id}/import',json={}).json()
    assert result[expected]==1
    assert len(c.get('/works').json())==1
    if expected=='conflicts':assert c.get('/works').json()[0]['doi']==identifier

def test_new_push_destination_and_tag_roundtrip(environment):
    c,server,app,secrets=environment;id=connect(c)
    work=c.post('/works',json={'title':'New local work','authors':['Bob'],'year':2025,'tags':['test']}).json()
    result=c.post(f'/zotero/{id}/push',json={'work_ids':[work['id']],'collection':'COLL0001'});assert result.status_code==200,result.text
    remote=server.items[result.json()[0]['item_key']]
    assert remote['data']['collections']==['COLL0001'] and remote['data']['tags']==[{'tag':'test'}]

def test_local_remote_both_changes_and_field_resolution(environment):
    c,server,app,secrets=environment;id=connect(c);work=imported(c,id)
    c.patch(f"/works/{work['id']}",json={'title':'Local title'})
    assert c.get(f'/zotero/{id}/states').json()[0]['status']=='Local changes'
    assert c.post(f'/zotero/{id}/sync').json()[0]['status']=='In sync'
    assert server.items['ITEM0001']['data']['title']=='Local title'
    server.edit(title='Remote title')
    assert c.post(f'/zotero/{id}/sync').json()[0]['status']=='In sync'
    assert c.get(f"/works/{work['id']}").json()['title']=='Remote title'
    c.patch(f"/works/{work['id']}",json={'title':'Local conflict'})
    server.edit(title='Remote conflict')
    state=c.post(f'/zotero/{id}/sync').json()[0];assert state['status']=='Conflict'
    assert c.get(f"/works/{work['id']}").json()['title']=='Local conflict'
    fields={field:'remote' for field in state['conflicts']};fields['title']='local'
    result=c.post(f"/zotero/conflicts/{state['id']}/resolve",json={'version':state['remote_snapshot']['version'],'fields':fields})
    assert result.status_code==200,result.text
    assert result.json()['status']=='In sync' and server.items['ITEM0001']['data']['title']=='Local conflict'
    assert all('if-unmodified-since-version' in r.headers for r in server.calls if r.method=='PATCH')

def test_optimistic_concurrency_and_doi_change_never_overwrite(environment):
    c,server,app,secrets=environment;id=connect(c);work=imported(c,id)
    c.patch(f"/works/{work['id']}",json={'title':'Local'})
    server.race=True
    state=c.post(f'/zotero/{id}/sync').json()[0]
    assert state['status']=='Conflict' and server.items['ITEM0001']['data']['title']=='Concurrent remote edit'
    server.edit(DOI='10.1234/other')
    state=c.post(f'/zotero/{id}/sync').json()[0]
    assert 'doi' in state['conflicts'] and c.get(f"/works/{work['id']}").json()['doi']=='10.1234/zotero'

def test_pdf_copy_deduplicates_and_credentials_not_persisted(environment,tmp_path):
    c,server,app,secrets=environment
    pdf=tmp_path/'p.pdf';make_pdf(pdf);server.pdf=pdf.read_bytes()
    server.items['FILE0001']={'key':'FILE0001','version':1,'data':{'itemType':'attachment','parentItem':'ITEM0001','contentType':'application/pdf','filename':'paper.pdf'}}
    id=connect(c);work=imported(c,id);attachment=work['external_attachments'][0]
    first=c.post(f"/zotero/attachments/{attachment['id']}/copy");assert first.status_code==200,first.text
    second=c.post(f"/zotero/attachments/{attachment['id']}/copy").json();assert second['duplicate']
    assert len(list((app.state.data/'files').glob('*.pdf')))==1
    bundle=tmp_path/'backup.zip';response=c.post('/storage/backup',json={'path':str(bundle)});assert response.status_code==200,response.text
    import zipfile
    with zipfile.ZipFile(bundle) as archive:
        assert all(b'SECRET-CANARY-ZOTERO' not in archive.read(n) for n in archive.namelist())
    assert all(b'SECRET-CANARY-ZOTERO' not in p.read_bytes() for p in app.state.data.glob('*') if p.is_file())
    assert 'SECRET-CANARY-ZOTERO' not in c.get('/zotero/connections').text
    assert c.post(f'/zotero/{id}/clear-credentials').json()['cleared'] and not secrets

def test_reject_non_loopback_and_unauthed_requests(environment):
    c,*_=environment
    assert c.post('/zotero/connections',json={'mode':'local','endpoint':'http://evil.example/api'}).status_code==422
    assert c.get('/zotero/connections',headers={'X-ResearchOS-Token':'bad'}).status_code==401

def test_reimport_pulls_remote_only_but_does_not_push_local_changes(environment):
    c,server,app,secrets=environment;id=connect(c);work=imported(c,id)
    server.edit(title='Reimported remote title')
    result=c.post(f'/zotero/{id}/import',json={}).json()
    assert result['updated']==1
    assert c.get(f"/works/{work['id']}").json()['title']=='Reimported remote title'
    c.patch(f"/works/{work['id']}",json={'title':'Local edits'})
    server.edit(title='Another remote edit')
    assert c.post(f'/zotero/{id}/import',json={}).json()['conflicts']==1
    assert server.items['ITEM0001']['data']['title']=='Another remote edit'
    assert not any(r.method=='PATCH' for r in server.calls)

def test_author_edit_preserves_remote_editor_and_refreshes_child_metadata(environment):
    c,server,app,secrets=environment;id=connect(c);work=imported(c,id)
    editor={'creatorType':'editor','name':'Existing Editor'}
    server.items['ITEM0001']['data']['creators'].append(editor)
    c.patch(f"/works/{work['id']}",json={'authors':['Bob']})
    assert c.post(f'/zotero/{id}/sync').json()[0]['status']=='In sync'
    assert editor in server.items['ITEM0001']['data']['creators']
    server.version+=1
    server.items['NOTE0002']={'key':'NOTE0002','version':server.version,'data':{'itemType':'note','parentItem':'ITEM0001','note':'New remote note'}}
    c.post(f'/zotero/{id}/sync')
    assert c.get(f"/works/{work['id']}").json()['zotero_notes'][0]['content']=='New remote note'

def test_remote_named_note_edit_is_not_silently_overwritten(environment):
    c,server,app,secrets=environment;id=connect(c)
    work=c.post('/works',json={'title':'Note roundtrip','notes':'Original note'}).json()
    payload={'work_ids':[work['id']],'note':True}
    assert c.post(f'/zotero/{id}/push',json=payload).status_code==200
    note=next(i for i in server.items.values() if i['data'].get('itemType')=='note')
    server.edit(note['key'],note='<h1>ResearchOS note</h1><p>User remote edit</p>')
    result=c.post(f'/zotero/{id}/push',json=payload)
    assert result.status_code==409
    assert 'User remote edit' in server.items[note['key']]['data']['note']
    assert len([i for i in server.items.values() if i['data'].get('title')=='Note roundtrip'])==1
