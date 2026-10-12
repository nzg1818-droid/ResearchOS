"""Local deterministic parsing. No network and no OCR."""
import hashlib
import math
import re
import fitz
from sqlalchemy import select, text
from ..db import Work, File, SourceHit, now
from ..storage import Storage
from .models import Document, Page, Block, Chunk

PARSER_VERSION = 'pymupdf-blocks-v1'
def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()

HEADINGS = {
    'abstract': 'Abstract', 'introduction': 'Introduction',
    'experimental': 'Experimental / Methods', 'methods': 'Experimental / Methods',
    'materials and methods': 'Experimental / Methods',
    'results': 'Results and Discussion', 'results and discussion': 'Results and Discussion',
    'discussion': 'Results and Discussion', 'characterization': 'Characterization',
    'electrochemical measurements': 'Electrochemical Measurements',
    'electrochemical characterization': 'Electrochemical Measurements',
    'conclusion': 'Conclusions', 'conclusions': 'Conclusions',
    'supporting information': 'Supporting/Other',
}

def abstract_for(session, work_id):
    for hit in session.scalars(select(SourceHit).where(SourceHit.work_id == work_id).order_by(SourceHit.id.desc())):
        raw = hit.raw
        abstract = raw.get('abstract')
        if isinstance(abstract, str) and abstract.strip():
            return re.sub('<[^>]+>', '', abstract).strip()
        inverted = raw.get('abstract_inverted_index')
        if isinstance(inverted, dict):
            words = {int(i): word for word, positions in inverted.items() for i in positions}
            return ' '.join(words[i] for i in sorted(words))
    return ''

def parse(session, root, work_id, source='auto'):
    work = session.get(Work, work_id)
    if work is None: raise ValueError('Work not found')
    file = session.scalar(select(File).where(File.work_id == work_id).order_by(File.id)) if source != 'abstract' else None
    abstract = abstract_for(session, work_id)
    path = Storage(root).resolve(file.path) if file else None
    usable = path is not None and path.is_file()
    source_type = 'pdf' if usable else 'abstract' if abstract else 'metadata'
    source_hash = Storage.hash(path) if usable else digest(abstract if abstract else work.title)
    existing = session.scalar(select(Document).where(Document.work_id == work_id, Document.source_type == source_type, Document.source_hash == source_hash, Document.parser_version == PARSER_VERSION))
    if existing: return existing
    doc = Document(work_id=work_id, file_id=file.id if usable else None, source_type=source_type, source_hash=source_hash, parser_version=PARSER_VERSION)
    session.add(doc); session.flush()
    if not usable:
        content = abstract or work.title
        doc.text_hash = digest(content)
        doc.parse_status = 'Abstract only' if abstract else 'Not parsed'
        doc.error = None if abstract else 'No PDF or abstract available; metadata only'
        add_chunk(session, doc, 0, content, None, 'Abstract' if abstract else 'Metadata', None, [], [])
        return doc
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass: raise ValueError('Encrypted PDF')
            doc.page_count = len(pdf)
            section, heading = 'Supporting/Other', None
            texts = []
            has_scanned_page = False
            order = 0
            for number, page in enumerate(pdf, 1):
                content = page.get_text('text', sort=True)
                texts.append(content)
                scanned = len(content.strip()) < 10 and bool(page.get_images())
                has_scanned_page |= scanned
                session.add(Page(document_id=doc.id, page_number=number, text=content, width=page.rect.width, height=page.rect.height, needs_ocr=scanned))
                for index, raw in enumerate(page.get_text('blocks', sort=True)):
                    if len(raw) > 6 and raw[6] != 0: continue
                    body = raw[4].strip()
                    if not body: continue
                    candidate = re.sub(r'^\s*[\d.]+\s*', '', body).strip().lower().rstrip(':')
                    confidence = 0.0
                    if candidate in HEADINGS:
                        section, heading, confidence = HEADINGS[candidate], body, 0.9
                    bbox = [max(0.0, min(1.0, raw[0]/page.rect.width)), max(0.0, min(1.0, raw[1]/page.rect.height)), max(0.0, min(1.0, raw[2]/page.rect.width)), max(0.0, min(1.0, raw[3]/page.rect.height))]
                    block_id = digest(f'{doc.id}:{number}:{index}:{body}')
                    session.add(Block(id=block_id, document_id=doc.id, page_number=number, block_index=index, section=section, heading=heading, heading_confidence=confidence, text=body, bbox=bbox, hash=digest(body), caption=bool(re.match(r'^(fig(?:ure)?\.?|table)\s*\d', body, re.I))))
                    # Bound chunks without losing source geometry; each segment retains its block.
                    for start in range(0, len(body), 1800):
                        segment = body[start:start+1800]
                        add_chunk(session, doc, order, segment, number, section, heading, [block_id], [{'page': number, 'rect': bbox}])
                        order += 1
            doc.text_hash = digest('\f'.join(texts))
            doc.has_text_layer = any(t.strip() for t in texts)
            doc.parse_status = 'Needs OCR' if has_scanned_page or not doc.has_text_layer else 'Parsed'
            doc.error = 'Scanned pages require OCR; OCR is not included in this phase' if doc.parse_status == 'Needs OCR' else None
    except Exception:
        doc.parse_status = 'Parse failed'
        doc.error = 'PDF parser failed; check that the file is a readable, unencrypted PDF'
    doc.updated_at = now()
    session.flush()
    return doc

def add_chunk(session, doc, order, content, page, section, heading, blocks, boxes):
    key = digest(f'{doc.id}:{order}:{content}')
    chunk = Chunk(id=key, document_id=doc.id, work_id=doc.work_id, order_index=order, page_start=page, page_end=page, section=section, heading=heading, text=content, block_ids=blocks, bboxes=boxes, hash=digest(content), char_length=len(content), token_estimate=math.ceil(len(content)/4))
    session.add(chunk); session.flush()
    session.execute(text('INSERT INTO paper_chunks_fts(chunk_id,work_id,document_id,text) VALUES (:c,:w,:d,:t)'), dict(c=key,w=doc.work_id,d=doc.id,t=content))
    return chunk

def retrieve(session, work_id, document_id, question, limit=6):
    tokens = re.findall(r'[^\W_]+', question, re.UNICODE)[:24]
    if not tokens: return []
    query = ' OR '.join('"' + t.replace('"','') + '"' for t in tokens)
    rows = session.execute(text('SELECT chunk_id FROM paper_chunks_fts WHERE paper_chunks_fts MATCH :q AND work_id=:w AND document_id=:d ORDER BY rank LIMIT :n'), dict(q=query,w=work_id,d=document_id,n=limit))
    return [session.get(Chunk, row[0]) for row in rows]
