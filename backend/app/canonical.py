import re
import unicodedata
from urllib.parse import unquote
from sqlalchemy import select
from .db import Work, Identifier, SourceHit, File, Annotation, Material, CollectionWork
from .schemas import Hit

def doi(value):
    value = unquote(value or '').strip().lower()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value)
    return value.rstrip(' .,;') or None

def normalized(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value or '').casefold())

def fingerprint(title, authors, year):
    if not title or not authors or not year:
        return None
    return f'{normalized(title)}|{normalized(authors[0])}|{year}'

def merge_work(session, winner, duplicate):
    """Resolve a later DOI bridge while preserving library data and source backlinks."""
    for cls in (Identifier, SourceHit, File, Annotation):
        for record in session.scalars(select(cls).where(cls.work_id == duplicate.id)):
            record.work_id = winner.id
    for member in session.scalars(select(CollectionWork).where(CollectionWork.work_id == duplicate.id)):
        if not session.get(CollectionWork, (member.collection_id, winner.id)):
            session.add(CollectionWork(collection_id=member.collection_id, work_id=winner.id))
        session.delete(member)
    for material in session.scalars(select(Material)):
        if material.provenance.get('work_id') == duplicate.id:
            material.provenance = {**material.provenance, 'work_id': winner.id}
    winner.in_library = winner.in_library or duplicate.in_library
    winner.starred = winner.starred or duplicate.starred
    winner.tags = list(dict.fromkeys(winner.tags + duplicate.tags))
    if duplicate.notes and duplicate.notes not in winner.notes:
        winner.notes = '\n\n'.join(filter(None, [winner.notes, duplicate.notes]))
    if winner.status == 'unread': winner.status = duplicate.status
    for field in ('authors', 'year', 'publication_date', 'journal', 'publisher_url', 'citations'):
        if getattr(winner, field) in (None, [], ''):
            setattr(winner, field, getattr(duplicate, field))
    winner.oa_locations = winner.oa_locations + [x for x in duplicate.oa_locations if x not in winner.oa_locations]
    winner.conflicts = winner.conflicts + duplicate.conflicts
    session.flush()
    session.delete(duplicate)
    session.flush()

def upsert(session, hit: Hit):
    identifier = doi(hit.doi)
    key = hit.source + ':' + hit.source_id
    work = session.scalar(select(Work).where(Work.doi == identifier)) if identifier else None
    source = session.get(Identifier, key)
    if work is not None and source and source.work_id != work.id:
        candidate = session.get(Work, source.work_id)
        if not candidate.doi or candidate.doi == identifier:
            merge_work(session, work, candidate)
    if work is None and source:
        candidate = session.get(Work, source.work_id)
        if not identifier or not candidate.doi or identifier == candidate.doi:
            work = candidate
    fp = fingerprint(hit.title, hit.authors, hit.year)
    if work is None and fp:
        for candidate in session.scalars(select(Work).where(Work.year == hit.year)):
            if candidate.doi and identifier and candidate.doi != identifier:
                continue
            if fingerprint(candidate.title, candidate.authors, candidate.year) == fp:
                work = candidate
                break
    fields = ('title', 'authors', 'year', 'publication_date', 'journal', 'publisher_url', 'citations')
    if work is None:
        work = Work(doi=identifier, **{f: getattr(hit, f) for f in fields}, oa_locations=hit.oa_locations)
        session.add(work)
        session.flush()
    else:
        if not work.doi:
            work.doi = identifier
        conflicts = list(work.conflicts)
        for field in fields:
            incoming, existing = getattr(hit, field), getattr(work, field)
            if incoming is not None and incoming != [] and incoming != '':
                if existing is None or existing == [] or existing == '':
                    setattr(work, field, incoming)
                elif incoming != existing:
                    conflict = {'field': field, 'source': hit.source, 'value': incoming}
                    if conflict not in conflicts:
                        conflicts.append(conflict)
                    if field == 'citations':
                        work.citations = max(incoming, existing)
        work.conflicts = conflicts
        locations = list(work.oa_locations)
        for location in hit.oa_locations:
            if location not in locations:
                locations.append(location)
        work.oa_locations = locations
    if source is None:
        session.add(Identifier(key=key, work_id=work.id))
    session.add(SourceHit(work_id=work.id, source=hit.source, raw=hit.raw))
    session.flush()
    return work
