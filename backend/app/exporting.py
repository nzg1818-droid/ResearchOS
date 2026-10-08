import json
import re

def clean(value):return re.sub(r'[\r\n]+',' ',str(value or ''))
def bib(value):
    # Escape BibTeX delimiters and TeX control characters in user metadata.
    return ''.join({'\\':r'\textbackslash{}','{':r'\{','}':r'\}','%':r'\%','&':r'\&','#':r'\#','_':r'\_','$':r'\$'}.get(c,c) for c in clean(value))
def export_works(works,format):
    if format=='csl-json':
        return json.dumps([dict(id=str(w.id),type='article-journal',title=w.title,author=[{'literal':a} for a in w.authors],**({'issued':{'date-parts':[[w.year]]}} if w.year else {}),**{'container-title':w.journal or ''},DOI=w.doi or '',URL=w.publisher_url or '') for w in works],ensure_ascii=False,indent=2),'application/json','json'
    if format=='ris':
        records=[]
        for w in works:
            lines=['TY  - JOUR','TI  - '+clean(w.title)]+['AU  - '+clean(a) for a in w.authors]
            for key,value in [('PY',w.year),('JO',w.journal),('DO',w.doi),('UR',w.publisher_url),('N1',w.notes)]:
                if value:lines.append(f'{key}  - {clean(value)}')
            lines+=['KW  - '+clean(t) for t in w.tags]+['ER  - ']
            records.append('\r\n'.join(lines))
        return '\r\n\r\n'.join(records),'application/x-research-info-systems','ris'
    if format=='bibtex':
        records=[]
        for w in works:
            fields={'title':w.title,'author':' and '.join(w.authors),'year':w.year,'journal':w.journal,'doi':w.doi,'url':w.publisher_url}
            records.append('@article{researchos'+str(w.id)+',\n'+',\n'.join(f'  {k} = {{{bib(v)}}}' for k,v in fields.items() if v)+'\n}')
        return '\n\n'.join(records),'application/x-bibtex','bib'
    raise ValueError('Choose ris, bibtex or csl-json')
