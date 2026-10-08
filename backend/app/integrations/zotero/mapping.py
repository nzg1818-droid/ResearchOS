import hashlib
import json
import re
from ...canonical import doi

FIELDS=('title','authors','doi','journal','date','year','tags','notes','collections')
def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def from_remote(item):
    data=item['data'];date=data.get('date','');year=re.search(r'\b(1[5-9]\d{2}|20\d{2})\b',date)
    return dict(title=data.get('title','Untitled'),authors=[c.get('name') or ' '.join(filter(None,[c.get('firstName'),c.get('lastName')])) for c in data.get('creators',[]) if c.get('creatorType','author')=='author'],doi=doi(data.get('DOI')),journal=data.get('publicationTitle',''),date=date,year=int(year.group()) if year else None,tags=sorted({t['tag'] for t in data.get('tags',[])}),notes=data.get('extra',''),collections=sorted(data.get('collections',[])))
def to_remote(value):
    return dict(title=value['title'],creators=[{'creatorType':'author','name':a} for a in value['authors']],DOI=value['doi'] or '',publicationTitle=value['journal'] or '',date=value['date'] or str(value['year'] or ''),tags=[{'tag':t} for t in value['tags']],extra=value['notes'],collections=value['collections'])
def stable_ids(item):
    extra=item['data'].get('extra','')
    pairs=[]
    for name,pattern in [('pmid',r'(?im)^PMID:\s*(\d+)'),('arxiv',r'(?im)^arXiv:\s*([^\s]+)')]:
        match=re.search(pattern,extra)
        if match:pairs.append(name+':'+match.group(1).lower())
    return pairs
