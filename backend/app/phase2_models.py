from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now

class SearchRun(Base):
    __tablename__ = 'search_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey('jobs.id'))
    query: Mapped[str]
    mode: Mapped[str]
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)
    finished_at: Mapped[str | None]

class SearchRunHit(Base):
    __tablename__ = 'search_run_hits'
    __table_args__ = (UniqueConstraint('run_id','source','source_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('search_runs.id'))
    source_hit_id: Mapped[int] = mapped_column(ForeignKey('source_hits.id'))
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    source: Mapped[str]
    source_id: Mapped[str]

class RemoteLibrary(Base):
    __tablename__ = 'remote_libraries'
    id: Mapped[int] = mapped_column(primary_key=True)
    identity: Mapped[str] = mapped_column(unique=True)
    mode: Mapped[str]
    library_type: Mapped[str]
    library_id: Mapped[str]
    endpoint: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=True)
    server_id: Mapped[str] = mapped_column(default='')
    version: Mapped[int] = mapped_column(default=0)
    last_synced_at: Mapped[str | None]

class SyncState(Base):
    __tablename__ = 'zotero_sync_state'
    __table_args__ = (UniqueConstraint('library_id','item_key'), UniqueConstraint('library_id','work_id'))
    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('remote_libraries.id'))
    item_key: Mapped[str]
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    remote_version: Mapped[int] = mapped_column(default=0)
    local_fingerprint: Mapped[str] = mapped_column(default='')
    base: Mapped[dict] = mapped_column(JSON, default=dict)
    remote_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(default='In sync')
    conflicts: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None]
    last_synced_at: Mapped[str | None]

class ExternalAttachment(Base):
    __tablename__ = 'external_attachments'
    __table_args__ = (UniqueConstraint('library_id','item_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('remote_libraries.id'))
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    item_key: Mapped[str]
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    managed_file_id: Mapped[int | None] = mapped_column(ForeignKey('files.id'))

class RemoteNote(Base):
    __tablename__ = 'remote_notes'
    __table_args__ = (UniqueConstraint('library_id','item_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('remote_libraries.id'))
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    item_key: Mapped[str]
    content: Mapped[str]
    version: Mapped[int]

class CollectionMapping(Base):
    __tablename__ = 'collection_mappings'
    __table_args__ = (UniqueConstraint('library_id','remote_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('remote_libraries.id'))
    collection_id: Mapped[int] = mapped_column(ForeignKey('collections.id'))
    remote_key: Mapped[str]
    remote_name: Mapped[str]
    parent_key: Mapped[str | None]
    mirror: Mapped[bool] = mapped_column(default=False)

class MaintenanceEvent(Base):
    __tablename__ = 'maintenance_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)
