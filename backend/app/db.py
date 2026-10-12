from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sys
from sqlalchemy import create_engine, event, String, Integer, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from alembic.config import Config
from alembic import command

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

class Work(Base):
    __tablename__ = 'works'
    id: Mapped[int] = mapped_column(primary_key=True)
    doi: Mapped[str | None] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(Text)
    title_key: Mapped[str] = mapped_column(default='')
    author_key: Mapped[str] = mapped_column(default='')
    authors: Mapped[list] = mapped_column(JSON, default=list)
    year: Mapped[int | None]
    publication_date: Mapped[str | None]
    journal: Mapped[str | None]
    publisher_url: Mapped[str | None]
    citations: Mapped[int | None]
    oa_locations: Mapped[list] = mapped_column(JSON, default=list)
    conflicts: Mapped[list] = mapped_column(JSON, default=list)
    in_library: Mapped[bool] = mapped_column(Boolean, default=False)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(default='unread')
    notes: Mapped[str] = mapped_column(Text, default='')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(default=now)

class Identifier(Base):
    __tablename__ = 'identifiers'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))

class SourceHit(Base):
    __tablename__ = 'source_hits'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    source: Mapped[str]
    raw: Mapped[dict] = mapped_column(JSON)
    snapshot_hash: Mapped[str | None] = mapped_column(index=True)
    retrieved_at: Mapped[str] = mapped_column(default=now)

class File(Base):
    __tablename__ = 'files'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    sha256: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    path: Mapped[str]
    pages: Mapped[int]
    extracted_doi: Mapped[str | None]
    extracted_title: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=now)

class Collection(Base):
    __tablename__ = 'collections'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

class CollectionWork(Base):
    __tablename__ = 'collection_works'
    collection_id: Mapped[int] = mapped_column(ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'), primary_key=True)

class Annotation(Base):
    __tablename__ = 'annotations'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    file_id: Mapped[int] = mapped_column(ForeignKey('files.id'))
    page: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default='')
    context_before: Mapped[str] = mapped_column(Text, default='')
    context_after: Mapped[str] = mapped_column(Text, default='')
    rects: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default='')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(default=now)

class Material(Base):
    __tablename__ = 'materials'
    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_id: Mapped[int] = mapped_column(ForeignKey('annotations.id'), unique=True)
    kind: Mapped[str]
    provenance: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str]
    state: Mapped[str] = mapped_column(default='queued')
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None]
    progress: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(default=now)

def initialize(data: Path):
    from . import phase2_models
    from .intelligence import models
    import sqlite3
    from contextlib import closing
    data = data.resolve()
    data.mkdir(parents=True, exist_ok=True)
    (data / 'files').mkdir(exist_ok=True)
    database = data / 'researchos.db'
    if database.exists():
        with closing(sqlite3.connect(database)) as old:
            version = old.execute("SELECT version_num FROM alembic_version").fetchone()
            if version and version[0] in ('0001', '0002'):
                backup = data / 'migration-backups' / (now().replace(':','-') + '-' + version[0] + '.db')
                backup.parent.mkdir(exist_ok=True)
                with closing(sqlite3.connect(backup)) as target: old.backup(target)
    engine = create_engine('sqlite:///' + (data / 'researchos.db').as_posix(), connect_args={'check_same_thread': False, 'timeout': 30})
    @event.listens_for(engine, 'connect')
    def pragmas(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    cfg = Config(str(root / 'alembic.ini'))
    cfg.set_main_option('script_location', str(root / 'migrations'))
    cfg.attributes['data_root'] = str(data)
    with engine.begin() as conn:
        cfg.attributes['connection'] = conn
        command.upgrade(cfg, 'head')
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        for job in session.query(Job).filter(Job.state.in_(['running', 'queued'])):
            job.state = 'interrupted'
            job.error = 'Application stopped. Retry to resume safely; completed imports are deduplicated.'
    return engine, factory

def columns(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@event.listens_for(Work, 'before_insert')
@event.listens_for(Work, 'before_update')
def index_identity(mapper, connection, work):
    from .textutils import normalized
    work.title_key = normalized(work.title)
    work.author_key = normalized(work.authors[0]) if work.authors else ''
