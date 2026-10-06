"""Explicit live-provider acceptance; never used by production as seed/fallback data."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from sqlalchemy import select
from app.adapters import federated
from app.schemas import Search
from app.canonical import upsert, doi
from app.db import initialize, Work

async def run():
    root=Path(__file__).resolve().parents[2]
    data=root/'acceptance-data'/'live'
    engine,sessions=initialize(data)
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'checks':[]}
    async def check(name,request):
        hits,errors,counts=await federated(request)
        with sessions.begin() as s:
            ids=list(dict.fromkeys(upsert(s,h).id for h in hits))
            records=[s.get(Work,id) for id in ids]
            identifiers=[w.doi for w in records if w.doi]
            assert len(identifiers)==len(set(identifiers)), 'Duplicate DOI records'
        result={'name':name,'request':request.model_dump(mode='json'),'counts':counts,'errors':errors,'canonical_count':len(ids),'raw_count':len(hits),'pass':not errors and all(counts.get(k,0)>0 for k in request.sources)}
        report['checks'].append(result)
        print(json.dumps(result),flush=True)
        return hits
    hits=await check('1-2 keyword date range and merge',Search(query='NiFe LDH alkaline water electrolysis',start='2020-01-01',end='2026-10-06',limit=20))
    paper=next(h for h in hits if h.doi and h.authors)
    await check('3 DOI',Search(query=doi(paper.doi),mode='doi'))
    await check('4 exact title',Search(query=paper.title,mode='title',limit=30))
    await check('5 author',Search(query=paper.authors[0],mode='author',limit=10))
    candidates=[h for h in hits if any(l.get('pdf_url') for l in h.oa_locations)]
    if not candidates:
        found,errors,counts=await federated(Search(query='NiFe layered double hydroxide oxygen evolution',sources=['openalex'],limit=30))
        candidates=[h for h in found if any(l.get('pdf_url') for l in h.oa_locations)]
    report['oa_candidates']=[{'title':h.title,'doi':doi(h.doi),'locations':h.oa_locations} for h in candidates[:5]]
    report['checks'].append({'name':'7 lawful OA discovery','pass':bool(candidates)})
    (root/'docs').mkdir(exist_ok=True)
    (root/'docs'/'live-acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    engine.dispose()
    if not all(c['pass'] for c in report['checks']):raise SystemExit(1)

if __name__=='__main__':asyncio.run(run())
