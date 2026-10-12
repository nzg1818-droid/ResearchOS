"""Authenticated intelligence API and resumable bounded background jobs."""
import asyncio
import csv
import io
import json
from typing import Literal
import keyring
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from ..db import Job, Work, columns
from .models import Document, Chunk, ProviderConfig, Extraction, ExtractionRun, Anchor, Question, Answer, AIRun
from .parsing import parse
from .providers import ProviderInput, SERVICE, validate_endpoint, provider, ProviderError
from . import service
from .schema import fields

class BatchInput(BaseModel):
    work_ids: list[int] = Field(min_length=1,max_length=1000)
    action: Literal['parse','metadata','abstract','full_text']
    provider_id: int | None = None
    cloud_consent: bool = False
    confirm_large_batch: bool = False
    force: bool = False
class ReviewInput(BaseModel):
    field_path: str
    action: Literal['accept','edit','reject']
    value: str | float | int | None = None
    note: str = Field(default='',max_length=4000)
class AskInput(BaseModel):
    question: str = Field(min_length=1,max_length=2000)
    provider_id: int | None = None
    cloud_consent: bool = False
class ExportInput(BaseModel):
    work_ids: list[int] = Field(min_length=1,max_length=1000)
    format: Literal['json','csv']
class ControlInput(BaseModel):
    action: Literal['pause','cancel','resume','retry']
    cloud_consent: bool = False


def register(app,sessions,root,write_lock,tasks):
    running=set()
    def required(s,cls,id):
        value=s.get(cls,id)
        if value is None:raise HTTPException(404,'Record not found')
        return value
    def config(s,id):
        return required(s,ProviderConfig,id) if id else None
    def safe_error(e):
        if isinstance(e,(ValueError,PermissionError,ProviderError)):return str(e)
        return 'Paper processing failed; retry or inspect the source file'
    def parse_one(work_id,source):
        with write_lock,sessions.begin() as s:return parse(s,root,work_id,source).id
    def update_job(id,**kwargs):
        with write_lock,sessions.begin() as s:
            j=s.get(Job,id)
            for k,v in kwargs.items():setattr(j,k,v)
    async def run_batch(id,consent):
        try:
            with sessions() as s:
                j=required(s,Job,id);payload=j.request;cfg=config(s,payload.get('provider_id'))
                concurrency=cfg.concurrency if cfg else 2
                results=dict(j.result.get('papers',{}))
            update_job(id,state='running',error=None)
            queue=asyncio.Queue()
            for work_id in payload['work_ids']:
                if results.get(str(work_id),{}).get('state') not in ('completed','cached','needs review'):queue.put_nowait(work_id)
            async def worker():
                while not queue.empty():
                    with sessions() as s:
                        if s.get(Job,id).state in ('paused','cancelled'):return
                    work_id=queue.get_nowait()
                    results[str(work_id)]={'state':'running'}
                    update_job(id,result={'papers':dict(results)})
                    try:
                        document_id=await asyncio.to_thread(parse_one,work_id,'abstract' if payload['action']=='abstract' else 'auto')
                        with sessions() as s:
                            doc=required(s,Document,document_id)
                            if payload['action']=='parse':
                                result={'state':'completed' if doc.parse_status in ('Parsed','Abstract only') else 'failed','document_id':doc.id,'parse_status':doc.parse_status,'error':doc.error}
                            else:
                                extraction,cached=await service.extract(s,doc,config(s,payload.get('provider_id')),payload['action'],consent,payload.get('force',False),getattr(app.state,'ai_transport',None))
                                result={'state':'cached' if cached else 'needs review' if extraction.verification_status=='Needs review' else 'completed','extraction_id':extraction.id}
                        results[str(work_id)]=result
                    except Exception as e:results[str(work_id)]={'state':'failed','error':safe_error(e)}
                    done=sum(r['state'] not in ('running','queued') for r in results.values())
                    update_job(id,result={'papers':dict(results)},progress=int(100*done/len(payload['work_ids'])))
            await asyncio.gather(*(worker() for _ in range(min(concurrency,queue.qsize()))))
            with sessions() as s:state=s.get(Job,id).state
            if state not in ('paused','cancelled'):
                update_job(id,state='partial' if any(r['state']=='failed' for r in results.values()) else 'completed',progress=100)
        finally:running.discard(id)
    def launch(id,consent):
        if id in running:raise HTTPException(409,'Wait for in-flight papers to finish before resuming')
        running.add(id)
        task=asyncio.create_task(run_batch(id,consent));tasks.add(task);task.add_done_callback(tasks.discard)

    @app.get('/intelligence/providers')
    def providers():
        with sessions() as s:return [{**columns(c),'configured':bool(keyring.get_password(SERVICE,str(c.id)))} for c in s.scalars(select(ProviderConfig))]
    @app.post('/intelligence/providers')
    def add_provider(body:ProviderInput):
        try:endpoint=validate_endpoint(body.provider_type,body.endpoint)
        except ValueError as e:raise HTTPException(422,str(e)) from None
        with write_lock,sessions.begin() as s:
            if body.is_default:
                for c in s.scalars(select(ProviderConfig)):c.is_default=False
            values=body.model_dump(exclude={'key'});values['endpoint']=endpoint
            c=ProviderConfig(**values,cloud=body.provider_type=='openai-compatible');s.add(c);s.flush()
            if body.key:keyring.set_password(SERVICE,str(c.id),body.key.get_secret_value())
            return columns(c)
    @app.put('/intelligence/providers/{id}')
    def edit_provider(id:int,body:ProviderInput):
        try:endpoint=validate_endpoint(body.provider_type,body.endpoint)
        except ValueError as e:raise HTTPException(422,str(e)) from None
        with write_lock,sessions.begin() as s:
            c=required(s,ProviderConfig,id)
            if body.is_default:
                for other in s.scalars(select(ProviderConfig)):other.is_default=False
            # Never forward an old secret to a changed host or provider.
            if c.endpoint!=endpoint or c.provider_type!=body.provider_type:
                if keyring.get_password(SERVICE,str(c.id)):keyring.delete_password(SERVICE,str(c.id))
            for k,v in body.model_dump(exclude={'key'}).items():setattr(c,k,v)
            c.endpoint=endpoint;c.cloud=body.provider_type=='openai-compatible'
            if body.key is not None:
                if body.key.get_secret_value():keyring.set_password(SERVICE,str(c.id),body.key.get_secret_value())
                elif keyring.get_password(SERVICE,str(c.id)):keyring.delete_password(SERVICE,str(c.id))
            return columns(c)
    @app.post('/intelligence/providers/{id}/test')
    async def test_provider(id:int):
        with sessions() as s:
            try:return await provider(required(s,ProviderConfig,id),getattr(app.state,'ai_transport',None)).health()
            except ProviderError as e:raise HTTPException(502,str(e)) from None
    @app.post('/intelligence/cache/clear')
    def clear_cache():
        with write_lock,sessions.begin() as s:
            # Preserve extraction and verification history; remove only reuse eligibility.
            for r in s.scalars(select(AIRun).where(AIRun.status=='completed')):r.cache_key='cleared:'+str(r.id)
        return {'cleared':True}
    @app.post('/intelligence/batches')
    async def batch(body:BatchInput):
        ids=list(dict.fromkeys(body.work_ids))
        if len(ids)>50 and not body.confirm_large_batch:raise HTTPException(422,'Confirm batches larger than 50 papers explicitly')
        with write_lock,sessions.begin() as s:
            for id in ids:required(s,Work,id)
            cfg=config(s,body.provider_id)
            if body.action not in ('parse','metadata'):
                if cfg is None or not cfg.enabled:raise HTTPException(422,'Provider not configured')
                if cfg.cloud and not body.cloud_consent:raise HTTPException(403,'Explicit cloud consent required for the selected papers')
            payload=body.model_dump(exclude={'cloud_consent'});payload['work_ids']=ids
            payload['provider_label']=f'{cfg.name} / {cfg.model}' if cfg else 'Offline'
            payload['cloud']=bool(cfg and cfg.cloud)
            j=Job(kind='intelligence',request=payload,result={'papers':{str(id):{'state':'queued'} for id in ids}});s.add(j);s.flush();id=j.id
        launch(id,body.cloud_consent);return {'job_id':id}
    @app.post('/intelligence/jobs/{id}/control')
    async def control(id:int,body:ControlInput):
        with write_lock,sessions.begin() as s:
            j=required(s,Job,id)
            if j.kind!='intelligence':raise HTTPException(422,'Not an intelligence task')
            if body.action in ('pause','cancel'):
                j.state='paused' if body.action=='pause' else 'cancelled'
                return {'state':j.state,'message':'Current papers finish safely; no further papers start'}
            cfg=config(s,j.request.get('provider_id'))
            if cfg and cfg.cloud and not body.cloud_consent:raise HTTPException(403,'Confirm cloud consent again to resume')
        launch(id,body.cloud_consent);return {'state':'running'}
    @app.get('/intelligence/works/{work_id}')
    def overview(work_id:int):
        with sessions() as s:
            required(s,Work,work_id)
            docs=list(s.scalars(select(Document).where(Document.work_id==work_id).order_by(Document.id.desc())))
            extractions=list(s.scalars(select(Extraction).join(ExtractionRun).where(ExtractionRun.work_id==work_id).order_by(Extraction.id.desc())))
            return {'documents':[{**columns(d),'chunks':s.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id==d.id)),'characters':s.scalar(select(func.sum(Chunk.char_length)).where(Chunk.document_id==d.id)) or 0} for d in docs],'extractions':[service.view(s,e) for e in extractions[:10]],'questions':[{**columns(q),'answers':[{**columns(a),'anchors':[columns(s.get(Anchor,id)) for id in a.anchor_ids]} for a in s.scalars(select(Answer).where(Answer.question_id==q.id))]} for q in s.scalars(select(Question).where(Question.work_id==work_id))]}
    @app.post('/intelligence/extractions/{id}/verify')
    def verify(id:int,body:ReviewInput):
        with write_lock,sessions.begin() as s:
            try:return service.verify(s,required(s,Extraction,id),body.field_path,body.action,body.value,body.note)
            except ValueError as e:raise HTTPException(422,str(e)) from None
    @app.post('/intelligence/extractions/{id}/knowledge')
    def knowledge(id:int,body:ReviewInput):
        with write_lock,sessions.begin() as s:
            e=required(s,Extraction,id);v=service.view(s,e)
            if v['field_states'].get(body.field_path,{}).get('status') not in ('User verified','User corrected'):raise HTTPException(422,'Verify this field before saving to Knowledge')
            anchors=list(s.scalars(select(Anchor).where(Anchor.extraction_id==id,Anchor.field_path==body.field_path)))
            try:return service.save_knowledge(s,v['run']['work_id'],str(dict(fields(v['effective']))[body.field_path]['value']),anchors,'ai-generated; user verified')
            except ValueError as e:raise HTTPException(422,str(e)) from None
    @app.post('/intelligence/works/{work_id}/ask')
    async def ask(work_id:int,body:AskInput):
        with sessions.begin() as s:
            doc=s.scalar(select(Document).where(Document.work_id==work_id,Document.parse_status.in_(['Parsed','Abstract only'])).order_by(Document.id.desc()))
            if not doc:raise HTTPException(422,'Parse this paper first')
            try:return await service.ask(s,doc,body.question,config(s,body.provider_id),body.cloud_consent,getattr(app.state,'ai_transport',None))
            except PermissionError as e:raise HTTPException(403,str(e)) from None
            except ProviderError as e:raise HTTPException(502,str(e)) from None
    @app.post('/intelligence/answers/{id}/knowledge')
    def answer_knowledge(id:int):
        with write_lock,sessions.begin() as s:
            answer=required(s,Answer,id);q=s.get(Question,answer.question_id)
            try:return service.save_knowledge(s,q.work_id,answer.text,[s.get(Anchor,a) for a in answer.anchor_ids],'paper answer; user saved')
            except ValueError as e:raise HTTPException(422,str(e)) from None
    @app.post('/intelligence/export')
    def export(body:ExportInput):
        with sessions() as s:
            records=[]
            for id in dict.fromkeys(body.work_ids):
                extraction=s.scalar(select(Extraction).join(ExtractionRun).where(ExtractionRun.work_id==id).order_by(Extraction.id.desc()))
                if extraction:records.append({'work_id':id,**service.view(s,extraction)})
            if body.format=='json':return {'content':json.dumps(records,ensure_ascii=False,indent=2),'mime':'application/json','filename':'ResearchOS-intelligence.json'}
            out=io.StringIO();writer=csv.writer(out);writer.writerow(['work_id','extraction_id','field_path','value','origin','status','pages','quotes'])
            for record in records:
                for path,field in fields(record['effective']):
                    anchors=[a for a in record['anchors'] if a['field_path']==path]
                    value=str(field['value'] if field['value'] is not None else '')
                    if value.startswith(('=','+','-','@')):value="'"+value
                    writer.writerow([record['work_id'],record['id'],path,value,field['origin'],record['field_states'][path]['status'],';'.join(str(a['page']) for a in anchors),json.dumps([a['quote'] for a in anchors],ensure_ascii=False)])
            return {'content':out.getvalue(),'mime':'text/csv','filename':'ResearchOS-intelligence.csv'}
