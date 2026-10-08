import hashlib
import re
import shutil
from pathlib import Path
import pymupdf
from sqlalchemy import select
from .db import File, Work
from .canonical import doi, normalized, upsert
from .schemas import Hit
from .storage import Storage

def import_pdf(session, data: Path, path: Path, work_id=None):
    path = path.resolve(strict=True)
    if path.suffix.lower() != '.pdf' or not path.is_file():
        raise ValueError('Choose a PDF file')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    existing = session.scalar(select(File).where(File.sha256 == digest))
    if existing:
        if work_id is not None and existing.work_id != work_id:
            raise ValueError(f'This PDF already belongs to Work {existing.work_id}; no duplicate created')
        return {'file_id': existing.id, 'work_id': existing.work_id, 'duplicate': True}
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError('Password-protected PDF: unlock your copy manually before importing')
        if doc.page_count < 1: raise ValueError('Empty PDF')
        text = '\n'.join(doc[p].get_text() for p in range(min(3, doc.page_count)))
        match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)
        extracted_doi = doi(match.group()) if match else None
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 12]
        title = (doc.metadata or {}).get('title') or (lines[0] if lines else path.stem)
        pages = doc.page_count
    work = session.get(Work, work_id) if work_id else None
    if work_id and work is None: raise ValueError('Selected Work does not exist')
    if work is None and extracted_doi:
        work = session.scalar(select(Work).where(Work.doi == extracted_doi))
    if work is None:
        matches = [w for w in session.scalars(select(Work).where(Work.title_key == normalized(title))) if not extracted_doi or not w.doi or w.doi == extracted_doi]
        if len(matches) == 1: work = matches[0]
    if work is None:
        work = upsert(session, Hit(source='local_pdf', source_id=digest, doi=extracted_doi, title=title, raw={'filename': path.name, 'sha256': digest}))
    work.in_library = True
    destination = Storage(data).copy(path, digest)
    file = File(work_id=work.id, sha256=digest, path=destination, name=path.name, pages=pages, extracted_doi=extracted_doi, extracted_title=title)
    session.add(file)
    session.flush()
    return {'file_id': file.id, 'work_id': work.id, 'duplicate': False}
