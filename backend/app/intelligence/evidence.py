"""Deterministic source checks. Evidence matching is not scientific truth verification."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from .models import Chunk, Page

def normalized(text):
    text=unicodedata.normalize('NFKC',str(text)).casefold().replace('−','-').replace('–','-')
    return re.sub(r'\s+',' ',text).strip()
def numbers(text):
    result=set()
    for item in re.findall(r'(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?',normalized(text)):
        try:result.add(Decimal(item.replace(',','')))
        except InvalidOperation:pass
    return result

def check(session,doc,field,path):
    valid=[];issues=[]
    for citation in field.get('evidence',[]):
        c=session.get(Chunk,citation['chunk_id'])
        if not c or c.document_id!=doc.id or c.work_id!=doc.work_id:
            issues.append('Evidence belongs to another document');continue
        page=citation.get('page')
        if page!=c.page_start or (page is not None and not 1<=page<=doc.page_count):
            issues.append('Evidence page mismatch');continue
        quote=citation['quote']
        if not quote.strip() or normalized(quote) not in normalized(c.text):
            issues.append('Evidence snippet mismatch');continue
        valid.append((c,quote))
    value=field.get('value')
    if value is None:return 'Unverified',valid,issues
    if not valid:issues.append('Evidence missing')
    if path.endswith(('.product','.composition','.phase')) and valid and not any(normalized(value) in normalized(q) for c,q in valid):
        issues.append('Product/composition/phase must be explicitly supported by its source')
    wanted=numbers(value)
    if wanted and not wanted.issubset(set().union(*(numbers(q) for c,q in valid))):issues.append('Numeric evidence mismatch')
    if path.startswith('performance.') and path.endswith(('unit','reported_unit','normalized_unit')) and valid:
        def unit(s):return re.sub(r'[\s^·⋅]','',normalized(s)).replace('cm-2','cm-2')
        if not any(unit(value) in unit(q) for c,q in valid):issues.append('Unit evidence mismatch')
    if field.get('origin')=='app_computed':
        # No conversion action is offered in this phase. Model-generated arithmetic is never trusted.
        issues.append('Computed value requires an explicit, reproducible user computation')
    return ('Needs review' if issues else 'Evidence matched'),valid,issues

def scientific_issues(payload,level):
    issues={}
    from .schema import fields
    for path,field in fields(payload):
        if field.get('value') is None:continue
        if level=='abstract' and path.startswith(('synthesis.','electrochemistry.','performance.')):
            field['value']=None;field['evidence']=[];continue
        if path.endswith('reference_conversion') or (field.get('origin')=='app_computed'):
            issues[path]=['Conversion not performed by this application; review required']
        if path.startswith('mechanism.') and path.endswith('claim'):
            text=normalized(field['value'])
            if any(phrase in text for phrase in ('amorphous is better','more elements is better','precatalyst is the active phase')):
                issues[path]=['Unsupported automatic scientific conclusion']
    for i,row in enumerate(payload.get('performance',[])):
        metric=normalized(row['metric']['value'] or '')
        unit=normalized(row['reported_unit']['value'] or '').replace(' ','')
        units={'overpotential':{'mv','v'},'cell voltage':{'mv','v'},'tafel':{'mvdec-1','mv/dec','mvdec^-1'},'efficiency':{'%','percent'},'selectivity':{'%','percent'},'duration':{'h','s','min','hours'}}
        for term,allowed in units.items():
            if term in metric and unit and unit not in allowed:
                issues[f'performance.{i}.reported_unit']=['Unit incompatible with metric']
                issues[f'performance.{i}.reported_value']=['Unit incompatible with metric']
    for i,row in enumerate(payload.get('mechanism',[])):
        combined=' '.join(str(v.get('value') or '') for v in row.values()).lower()
        if ('ex situ' in combined or 'ex-situ' in combined) and not any(x in combined for x in ('in situ','in-situ','operando')):
            row['limitation']['value']='Mechanism evidence is ex-situ only; working-state assignment is unverified'
            row['limitation']['origin']='ai_interpretation'
            issues[f'mechanism.{i}.limitation']=['Ex-situ-only mechanism limitation']
    return issues
