import fitz
from sqlalchemy import select, text
from app.db import initialize, Work, File, SourceHit
from app.intelligence.models import Document, Page, Block, Chunk
from app.intelligence.parsing import parse, retrieve
from app.importer import import_pdf

def paper(path):
    pdf=fitz.open()
    for heading, body in [('Abstract','NiFe catalyst improves oxygen evolution.'), ('Electrochemical Measurements','The overpotential was 250 mV at 100 mA cm-2 in 1 M KOH.'), ('Characterization','Ex situ XPS showed nickel oxidation. Working phase was not determined.')]:
        p=pdf.new_page();p.insert_text((60,60),heading);p.insert_text((60,100),body)
    pdf.save(path);pdf.close()

def test_parse_pages_geometry_cache_and_scoped_fts(tmp_path):
    root=tmp_path/'library';engine,sessions=initialize(root)
    source=tmp_path/'paper.pdf';paper(source)
    with sessions.begin() as s:
        result=import_pdf(s,root,source,None)
        file=s.scalar(select(File));doc=parse(s,root,file.work_id)
        assert doc.parse_status=='Parsed' and doc.page_count==3
        assert [p.page_number for p in s.scalars(select(Page))]==[1,2,3]
        blocks=list(s.scalars(select(Block)))
        assert all(0<=v<=1 for b in blocks for v in b.bbox)
        ids=list(s.scalars(select(Chunk.id)))
        assert parse(s,root,file.work_id).id==doc.id
        assert list(s.scalars(select(Chunk.id)))==ids
        matches=retrieve(s,file.work_id,doc.id,'overpotential')
        assert matches and matches[0].page_start==2
        assert not retrieve(s,file.work_id+1,doc.id,'overpotential')
    engine.dispose()

def test_abstract_scanned_failure_and_changed_source(tmp_path):
    root=tmp_path/'library';engine,sessions=initialize(root)
    with sessions.begin() as s:
        w=Work(title='Abstract paper',authors=[]);s.add(w);s.flush()
        hit=SourceHit(work_id=w.id,source='crossref',raw={'abstract':'Catalyst abstract'});s.add(hit);s.flush()
        first=parse(s,root,w.id)
        assert first.parse_status=='Abstract only' and first.file_id is None
        hit.raw={'abstract':'Changed catalyst abstract'};s.flush()
        assert parse(s,root,w.id).text_hash!=first.text_hash
        scan=tmp_path/'scan.pdf';pdf=fitz.open();pdf.new_page();pdf.save(scan);pdf.close()
        import_pdf(s,root,scan,w.id)
        assert parse(s,root,w.id).parse_status=='Needs OCR'
        file=s.scalar(select(File));(root/file.path).write_bytes(b'broken PDF')
        assert parse(s,root,w.id).parse_status=='Parse failed'
    engine.dispose()

def test_0002_upgrade_preserves_records_and_creates_backup(tmp_path):
    import sqlite3
    root=tmp_path/'library';engine,sessions=initialize(root)
    with sessions.begin() as s:s.add(Work(title='Keep me',authors=[]))
    engine.dispose()
    # Model an actual 0002 database by removing only the new empty schema.
    names=['paper_answers','paper_questions','verification_decisions','evidence_anchors','paper_extractions','extraction_runs','ai_runs','ai_provider_configs','document_chunks','document_blocks','document_pages','paper_documents']
    with sqlite3.connect(root/'researchos.db') as db:
        db.execute('DROP TABLE paper_chunks_fts')
        for name in names:db.execute('DROP TABLE '+name)
        db.execute("UPDATE alembic_version SET version_num='0002'")
    engine,sessions=initialize(root)
    with sessions() as s:
        assert s.scalar(select(Work)).title=='Keep me'
        assert s.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0003'
    assert list((root/'migration-backups').glob('*-0002.db'))
    engine.dispose()
