"""Smoke-test the frozen Windows sidecar with isolated synthetic data."""
import json, os, secrets, subprocess, sys, time
from pathlib import Path
import httpx
import fitz
root=Path(__file__).resolve().parents[1]
data=root/'acceptance-data'/('frozen-'+str(time.time_ns()));data.mkdir(parents=True)
pdf=fitz.open();page=pdf.new_page();page.insert_text((60,60),'Electrochemical Measurements');page.insert_text((60,100),'The overpotential was 250 mV at 100 mA cm-2 in 1 M KOH.');source=data/'fixture.pdf';pdf.save(source);pdf.close()
token=secrets.token_urlsafe(24)
env={**os.environ,'RESEARCHOS_TOKEN':token,'RESEARCHOS_DATA_DIR':str(data/'library'),'RESEARCHOS_PORT':'8766'}
log=(data/'sidecar.log').open('w',encoding='utf-8')
process=subprocess.Popen([str(root/'backend/dist/researchos-backend/researchos-backend.exe')],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    with httpx.Client(base_url='http://127.0.0.1:8766',headers={'X-ResearchOS-Token':token},trust_env=False,timeout=30) as client:
        for _ in range(60):
            try:
                health=client.get('/health');health.raise_for_status();break
            except httpx.HTTPError:time.sleep(.25)
        else:raise RuntimeError('Frozen sidecar did not start')
        def post(url,body):
            r=client.post(url,json=body);r.raise_for_status();return r.json()
        def wait(id):
            for _ in range(100):
                r=client.get(f'/jobs/{id}').json()
                if r['state'] not in ('queued','running'):return r
                time.sleep(.1)
            raise RuntimeError('Task timed out')
        imported=wait(post('/imports',{'paths':[str(source)]})['job_id']);assert imported['state']=='completed',imported
        work=client.get('/works?library=true').json()[0]
        cfg=post('/intelligence/providers',{'name':'Offline smoke fixture','provider_type':'mock','model':'deterministic'})
        result=wait(post('/intelligence/batches',{'work_ids':[work['id']],'action':'full_text','provider_id':cfg['id']})['job_id']);assert result['state']=='completed',result
        overview=client.get(f"/intelligence/works/{work['id']}").json();extraction=overview['extractions'][0]
        assert extraction['effective']['performance'][0]['reported_value']['value']==250
        answer=post(f"/intelligence/works/{work['id']}/ask",{'question':'overpotential'});assert answer['anchors'][0]['page']==1
        summary={'health':health.json(),'extraction_id':extraction['id'],'field_status':extraction['field_states']['performance.0.reported_value'],'answer_page':1,'result':'PASS','boundary':'Frozen Windows sidecar with synthetic PDF and local mock; not real-provider/manual acceptance'}
        (root/'release/phase2b1-frozen-smoke.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps(summary))
finally:
    process.terminate();process.wait(timeout=15);log.close()
