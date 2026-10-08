import json
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from test_core import make_pdf, wait_job

def test_backup_restore_and_manifest_tampering(tmp_path):
    pdf=tmp_path/'paper.pdf';make_pdf(pdf)
    root=tmp_path/'data';bundle=tmp_path/'backup.zip'
    with TestClient(create_app(root,'t'),headers={'X-ResearchOS-Token':'t'}) as c:
        item=wait_job(c,c.post('/imports',json={'paths':[str(pdf)]}).json()['job_id'])['result']['imports'][0]
        result=c.post('/annotations',json={'file_id':item['file_id'],'page':2,'text':'Nickel iron catalysts','context':'before Nickel iron catalysts after','kind':'evidence','rects':[{'x':.1,'y':.2,'width':.3,'height':.02}]})
        assert result.status_code==200
        backup=c.post('/storage/backup',json={'path':str(bundle)});assert backup.status_code==200,backup.text
        assert c.post('/storage/backup',json={'path':str(bundle)}).status_code==422
        destination=tmp_path/'restored'
        response=c.post('/storage/restore',json={'path':str(bundle),'destination':str(destination)});assert response.status_code==200,response.text
        assert c.post('/storage/restore',json={'path':str(bundle),'destination':str(destination)}).status_code==422
        corrupt=tmp_path/'corrupt.zip'
        with zipfile.ZipFile(bundle) as original,zipfile.ZipFile(corrupt,'w') as modified:
            for name in original.namelist():modified.writestr(name,b'bad bytes' if name.endswith('.pdf') else original.read(name))
        assert c.post('/storage/validate',json={'path':str(corrupt)}).status_code==422
        assert c.post('/storage/restore',json={'path':str(corrupt),'destination':str(tmp_path/'no-create')}).status_code==422
        assert not (tmp_path/'no-create').exists()
    with TestClient(create_app(destination,'t'),headers={'X-ResearchOS-Token':'t'}) as c:
        assert c.get(f"/files/{item['file_id']}/content").content==pdf.read_bytes()
        material=c.get('/materials').json()[0]
        assert material['annotation']['page']==2 and material['annotation']['context_before']=='before '
        managed=next((destination/'files').glob('*.pdf'));managed.write_bytes(b'corrupted')
        assert c.get('/diagnostics').json()['corrupt_files']==[item['file_id']]
        managed.unlink()
        assert c.get('/diagnostics').json()['missing_files']==[item['file_id']]

def test_exports_single_selected_collection_and_library(tmp_path):
    with TestClient(create_app(tmp_path,'t'),headers={'X-ResearchOS-Token':'t'}) as c:
        a=c.post('/works',json={'title':'Catalyst {A} & B','authors':['Alice Smith'],'year':2024,'doi':'10.1234/a','tags':['OER']}).json()
        b=c.post('/works',json={'title':'Second paper'}).json()
        col=c.post('/collections',json={'name':'Subset'}).json();c.post(f"/collections/{col['id']}/works/{a['id']}")
        for format in ['ris','bibtex','csl-json']:
            for selection in [{'work_ids':[a['id']]},{'work_ids':[a['id'],b['id']]},{'collection_id':col['id']},{}]:
                result=c.post('/export',json={'format':format,**selection});assert result.status_code==200
                content=result.json()['content'];assert 'Catalyst' in content
                if format=='ris':assert 'ER  -' in content and 'AU  - Alice Smith' in content
                if format=='bibtex':assert r'\{A\}' in content and r'\&' in content
                if format=='csl-json':assert json.loads(content)[0]['DOI']=='10.1234/a'
                assert ('Second paper' in content)==('work_ids' in selection and len(selection['work_ids'])==2 or not selection)
