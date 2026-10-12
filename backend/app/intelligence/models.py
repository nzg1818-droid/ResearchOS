"""Persistent, non-secret paper intelligence and immutable review provenance."""
from sqlalchemy import ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base, now

class Document(Base):
    __tablename__ = 'paper_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'), index=True)
    file_id: Mapped[int | None] = mapped_column(ForeignKey('files.id'))
    source_type: Mapped[str]
    source_hash: Mapped[str]
    parser_version: Mapped[str]
    text_hash: Mapped[str] = mapped_column(default='')
    parse_status: Mapped[str] = mapped_column(default='Parsing')
    page_count: Mapped[int] = mapped_column(default=0)
    has_text_layer: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint('work_id','source_type','source_hash','parser_version'),)

class Page(Base):
    __tablename__ = 'document_pages'
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('paper_documents.id'), index=True)
    page_number: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    width: Mapped[float]
    height: Mapped[float]
    needs_ocr: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint('document_id','page_number'),)

class Block(Base):
    __tablename__ = 'document_blocks'
    id: Mapped[str] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('paper_documents.id'), index=True)
    page_number: Mapped[int]
    block_index: Mapped[int]
    section: Mapped[str]
    heading: Mapped[str | None]
    heading_confidence: Mapped[float] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(Text)
    bbox: Mapped[list] = mapped_column(JSON)
    hash: Mapped[str]
    caption: Mapped[bool] = mapped_column(default=False)

class Chunk(Base):
    __tablename__ = 'document_chunks'
    id: Mapped[str] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('paper_documents.id'), index=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'), index=True)
    order_index: Mapped[int]
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    section: Mapped[str]
    heading: Mapped[str | None]
    text: Mapped[str] = mapped_column(Text)
    block_ids: Mapped[list] = mapped_column(JSON, default=list)
    bboxes: Mapped[list] = mapped_column(JSON, default=list)
    hash: Mapped[str]
    char_length: Mapped[int]
    token_estimate: Mapped[int]

class ProviderConfig(Base):
    __tablename__ = 'ai_provider_configs'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    provider_type: Mapped[str]
    endpoint: Mapped[str]
    model: Mapped[str]
    max_output_tokens: Mapped[int] = mapped_column(default=4000)
    timeout: Mapped[int] = mapped_column(default=60)
    concurrency: Mapped[int] = mapped_column(default=2)
    enabled: Mapped[bool] = mapped_column(default=True)
    cloud: Mapped[bool] = mapped_column(default=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    default_level: Mapped[str] = mapped_column(default='abstract')

class AIRun(Base):
    __tablename__ = 'ai_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey('ai_provider_configs.id'))
    provider_type: Mapped[str]
    model: Mapped[str]
    prompt_version: Mapped[str]
    schema_version: Mapped[str]
    source_hash: Mapped[str]
    cache_key: Mapped[str] = mapped_column(index=True)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(default='running')
    error: Mapped[str | None]
    started_at: Mapped[str] = mapped_column(default=now)
    finished_at: Mapped[str | None]

class ExtractionRun(Base):
    __tablename__ = 'extraction_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('paper_documents.id'))
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey('ai_runs.id'))
    extraction_level: Mapped[str]
    schema_version: Mapped[str]
    prompt_version: Mapped[str]
    provider_id: Mapped[int | None] = mapped_column(ForeignKey('ai_provider_configs.id'))
    model: Mapped[str]
    source_hash: Mapped[str]
    status: Mapped[str]
    started_at: Mapped[str] = mapped_column(default=now)
    finished_at: Mapped[str | None]
    error: Mapped[str | None]

class Extraction(Base):
    __tablename__ = 'paper_extractions'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('extraction_runs.id'), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    field_states: Mapped[dict] = mapped_column(JSON)
    verification_status: Mapped[str] = mapped_column(default='Unverified')
    created_at: Mapped[str] = mapped_column(default=now)

class Anchor(Base):
    __tablename__ = 'evidence_anchors'
    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[int | None] = mapped_column(ForeignKey('paper_extractions.id'), index=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'))
    field_path: Mapped[str]
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey('document_chunks.id'))
    file_id: Mapped[int | None] = mapped_column(ForeignKey('files.id'))
    page: Mapped[int | None]
    section: Mapped[str]
    quote: Mapped[str] = mapped_column(Text)
    bboxes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_type: Mapped[str]
    confidence: Mapped[float]
    validation_status: Mapped[str]

class Decision(Base):
    __tablename__ = 'verification_decisions'
    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey('paper_extractions.id'), index=True)
    field_path: Mapped[str]
    action: Mapped[str]
    old_value: Mapped[dict | list | str | float | None] = mapped_column(JSON)
    new_value: Mapped[dict | list | str | float | None] = mapped_column(JSON)
    user_note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(default=now)

class Question(Base):
    __tablename__ = 'paper_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey('works.id'), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('paper_documents.id'))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)

class Answer(Base):
    __tablename__ = 'paper_answers'
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('paper_questions.id'))
    text: Mapped[str] = mapped_column(Text)
    anchor_ids: Mapped[list] = mapped_column(JSON, default=list)
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey('ai_runs.id'))
    created_at: Mapped[str] = mapped_column(default=now)
