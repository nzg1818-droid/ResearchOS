"""Extraction orchestration, provenance, review and paper-scoped retrieval."""
import json
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy import select
from ..db import now, columns, Work, Annotation, Material
from .models import Document, Chunk, ExtractionRun, Extraction, Anchor, Decision, AIRun, ProviderConfig, Question, Answer
from .schema import PaperExtraction, fields, SCHEMA_VERSION
from .parsing import digest, retrieve
from .providers import provider, ProviderError
from .evidence import check, scientific_issues
PROMPT_VERSION='extraction-v1'
SECTIONS=list(PaperExtraction.model_fields)

def prompt(name):return (Path(__file__).parent/'prompts'/f'{name}.txt').read_text(encoding='utf-8')
def chunks_for(session,doc,section):
    terms={'synthesis':'synthesis method preparation temperature','performance':'overpotential current density voltage efficiency slope','electrochemistry':'electrochemical electrolyte electrode KOH correction','characterization':'XPS XRD SEM TEM Raman characterization','mechanism':'mechanism operando DFT active phase','materials':'catalyst composition morphology material'}
    selected=retrieve(session,doc.work_id,doc.id,terms.get(section,section.replace('_',' ')),8)
    if not selected:selected=list(session.scalars(select(Chunk).where(Chunk.document_id==doc.id).order_by(Chunk.order_index).limit(4)))
    return [{'id':c.id,'page':c.page_start,'section':c.section,'text':c.text} for c in selected]

def cache_key(doc,config,level):
    settings={k:getattr(config,k) for k in ('provider_type','endpoint','model','max_output_tokens')} if config else {'provider_type':'metadata','model':'deterministic'}
    return digest(json.dumps([doc.work_id,doc.source_hash,doc.parser_version,doc.text_hash,SCHEMA_VERSION,PROMPT_VERSION,settings,level],sort_keys=True))

async def extract(session,doc,config,level,consent=False,force=False,transport=None):
    if level=='full_text' and doc.parse_status!='Parsed':raise ValueError(doc.error or 'Full-text extraction needs a parsed text PDF')
    if level=='abstract' and doc.source_type!='abstract':raise ValueError('Abstract extraction requires the available abstract')
    key=cache_key(doc,config,level)
    if not force:
        previous=session.scalar(select(Extraction).join(ExtractionRun).join(AIRun).where(AIRun.cache_key==key,AIRun.status=='completed').order_by(Extraction.id.desc()))
        if previous:return previous,True
    if level!='metadata' and (config is None or not config.enabled):raise ProviderError('Provider not configured')
    if level!='metadata' and config.cloud and not consent:raise PermissionError('Explicit cloud consent required for this paper or selected batch')
    ai=AIRun(provider_id=config.id if config else None,provider_type=config.provider_type if config else 'metadata',model=config.model if config else 'deterministic',prompt_version=PROMPT_VERSION,schema_version=SCHEMA_VERSION,source_hash=doc.text_hash,cache_key=key,request_metadata={'level':level,'cloud_consent':bool(consent),'document_id':doc.id})
    session.add(ai);session.flush()
    run=ExtractionRun(work_id=doc.work_id,document_id=doc.id,ai_run_id=ai.id,extraction_level=level,schema_version=SCHEMA_VERSION,prompt_version=PROMPT_VERSION,provider_id=ai.provider_id,model=ai.model,source_hash=doc.text_hash,status='running')
    session.add(run);session.flush();session.commit()
    try:
        result=PaperExtraction().model_dump()
        if level=='metadata':
            result['one_minute_brief']['value']=session.get(Work,doc.work_id).title
        else:
            adapter=provider(config,transport)
            for section in SECTIONS:
                if level=='abstract' and section in ('synthesis','electrochemistry','performance'):continue
                chunks=chunks_for(session,doc,section)
                response=await adapter.structured(prompt(PROMPT_VERSION),{'section':section,'level':level,'chunks':chunks,'candidates':[{ 'chunk_id':c['id'],'reported_numbers':__import__('re').findall(r'[-+]?\d+(?:\.\d+)?\s*(?:mV|V|mA|M|%|h)\b',c['text'])} for c in chunks] if section=='performance' else [],'schema':PaperExtraction.model_json_schema()},PaperExtraction.model_json_schema())
                validated=PaperExtraction.model_validate(response.content).model_dump()
                result[section]=validated[section]
                ai.usage={k:ai.usage.get(k,0)+v for k,v in response.usage.items()}
        rules=scientific_issues(result,level)
        extraction=Extraction(run_id=run.id,payload=result,field_states={},verification_status='Unverified')
        session.add(extraction);session.flush()
        states={}
        for path,field in fields(result):
            status,anchors,issues=check(session,doc,field,path)
            if path in rules:status='Needs review';issues+=rules[path]
            states[path]={'status':status,'issues':issues}
            for chunk,quote in anchors:
                session.add(Anchor(extraction_id=extraction.id,work_id=doc.work_id,field_path=path,chunk_id=chunk.id,file_id=doc.file_id,page=chunk.page_start,section=chunk.section,quote=quote,bboxes=chunk.bboxes,evidence_type=field['origin'],confidence=field['confidence'],validation_status=status))
        extraction.field_states=states
        extraction.verification_status='Needs review' if any(v['status']=='Needs review' for v in states.values()) else 'Unverified'
        ai.status=run.status='completed';ai.finished_at=run.finished_at=now();session.commit()
        return extraction,False
    except Exception as error:
        # Do not persist provider payloads/errors (they may contain secrets or invalid prose).
        session.rollback();ai=session.get(AIRun,ai.id);run=session.get(ExtractionRun,run.id)
        safe='Invalid structured output' if isinstance(error,ValidationError) else str(error) if isinstance(error,(ProviderError,ValueError)) else 'Extraction failed'
        ai.status=run.status='failed';ai.error=run.error=safe;ai.finished_at=run.finished_at=now();session.commit()
        raise ProviderError(safe) from None

def view(session,extraction):
    run=session.get(ExtractionRun,extraction.run_id)
    decisions=list(session.scalars(select(Decision).where(Decision.extraction_id==extraction.id).order_by(Decision.id)))
    effective=json.loads(json.dumps(extraction.payload));states=dict(extraction.field_states)
    for d in decisions:
        node=effective
        for part in d.field_path.split('.')[:-1]:node=node[int(part)] if isinstance(node,list) else node[part]
        key=d.field_path.split('.')[-1]
        field=node[int(key)] if isinstance(node,list) else node[key]
        if d.action=='edit':field['value']=d.new_value
        states[d.field_path]={'status':{'accept':'User verified','edit':'User corrected','reject':'Rejected'}[d.action],'issues':[]}
    return {**columns(extraction),'effective':effective,'field_states':states,'run':columns(run),'decisions':[columns(d) for d in decisions],'anchors':[columns(a) for a in session.scalars(select(Anchor).where(Anchor.extraction_id==extraction.id))]}

def verify(session,extraction,path,action,new_value=None,note=''):
    current=view(session,extraction);mapping=dict(fields(current['effective']))
    if path not in mapping:raise ValueError('Unknown field path')
    field=mapping[path]
    anchors=list(session.scalars(select(Anchor).where(Anchor.extraction_id==extraction.id,Anchor.field_path==path)))
    if action in ('accept','edit'):
        candidate={**field,'value':new_value if action=='edit' else field['value']}
        doc=session.get(Document,current['run']['document_id'])
        status,valid,issues=check(session,doc,candidate,path)
        rules=scientific_issues(json.loads(json.dumps(current['effective'])),current['run']['extraction_level'])
        if path in rules:raise ValueError('Scientific validation requires review; this field cannot be verified automatically')
        if candidate['value'] is not None and (status!='Evidence matched' or not valid):
            raise ValueError('Verification requires matching source evidence; correct the value to match its source or reject it')
    session.add(Decision(extraction_id=extraction.id,field_path=path,action=action,old_value=field['value'],new_value=new_value if action=='edit' else field['value'],user_note=note))
    session.flush()
    updated=view(session,extraction)
    nonempty=[path for path,f in fields(updated['effective']) if f['value'] is not None]
    if nonempty and all(updated['field_states'][p]['status'] in ('User verified','User corrected','Rejected') for p in nonempty):
        extraction.verification_status='User verified'
        run=session.get(ExtractionRun,extraction.run_id)
        if run.extraction_level=='full_text':run.extraction_level='full_text_verified'
    return view(session,extraction)

def save_knowledge(session,work_id,text,anchors,origin):
    if not anchors or any(a.work_id!=work_id or a.file_id is None or a.page is None for a in anchors):raise ValueError('Knowledge requires PDF evidence from this paper')
    first=anchors[0]
    annotation=Annotation(work_id=work_id,file_id=first.file_id,page=first.page,text=first.quote,rects=[{'x':b['rect'][0],'y':b['rect'][1],'width':b['rect'][2]-b['rect'][0],'height':b['rect'][3]-b['rect'][1]} for b in first.bboxes if b['page']==first.page],note=text)
    session.add(annotation);session.flush()
    work=session.get(Work,work_id)
    material=Material(annotation_id=annotation.id,kind='claim',provenance={'work_id':work_id,'file_id':first.file_id,'page':first.page,'title':work.title,'doi':work.doi,'authors':work.authors,'year':work.year,'filename':'Evidence PDF','text':text,'origin':origin,'evidence_anchors':[columns(a) for a in anchors]})
    session.add(material);session.flush();return columns(material)

async def ask(session,doc,question,config=None,consent=False,transport=None):
    chunks=retrieve(session,doc.work_id,doc.id,question)
    q=Question(work_id=doc.work_id,document_id=doc.id,text=question);session.add(q);session.flush()
    answer='Not found in this paper';anchors=[];ai=None
    if chunks:
        payload={'question':question,'chunks':[{'id':c.id,'text':c.text,'page':c.page_start} for c in chunks]}
        if config:
            if config.cloud and not consent:raise PermissionError('Explicit cloud consent required')
            ai=AIRun(provider_id=config.id,provider_type=config.provider_type,model=config.model,prompt_version='answer-v1',schema_version=SCHEMA_VERSION,source_hash=doc.text_hash,cache_key=digest(json.dumps([doc.text_hash,question,config.model,'answer-v1'])),request_metadata={'document_id':doc.id,'chunk_ids':[c.id for c in chunks],'cloud_consent':bool(consent),'purpose':'ask'})
            session.add(ai);session.flush()
            result=await provider(config,transport).answer(prompt('answer-v1'),payload)
            ai.usage=result.usage;ai.status='completed';ai.finished_at=now()
            answer=result.content.get('answer','Not found in this paper');citations=result.content.get('citations',[])
        else:
            answer='Source excerpts (offline retrieval): '+chunks[0].text
            citations=[{'chunk_id':chunks[0].id,'page':chunks[0].page_start,'quote':chunks[0].text}]
        from .schema import PaperAnswer
        try:
            validated=PaperAnswer.model_validate({'answer':answer,'citations':citations})
            answer=validated.answer;citations=[c.model_dump() for c in validated.citations]
        except ValidationError:raise ProviderError('Invalid structured output') from None
        status,valid,issues=check(session,doc,{'value':answer,'evidence':citations},'answer')
        allowed={c.id for c in chunks}
        if issues or not valid or any(c.id not in allowed for c,t in valid) or not isinstance(answer,str):answer='Not found in this paper'
        else:
            for c,quote in valid:
                anchor=Anchor(work_id=doc.work_id,field_path='answer',chunk_id=c.id,file_id=doc.file_id,page=c.page_start,section=c.section,quote=quote,bboxes=c.bboxes,evidence_type='source_reported' if not config else 'ai_interpretation',confidence=0.0,validation_status='Evidence matched')
                session.add(anchor);session.flush();anchors.append(anchor)
    saved=Answer(question_id=q.id,text=answer,anchor_ids=[a.id for a in anchors],ai_run_id=ai.id if ai else None);session.add(saved);session.flush()
    return {**columns(saved),'anchors':[columns(a) for a in anchors]}
