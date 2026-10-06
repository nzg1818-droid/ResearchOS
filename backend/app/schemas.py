from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Search(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    mode: Literal['keyword', 'title', 'author', 'doi'] = 'keyword'
    start: date | None = None
    end: date | None = None
    limit: int = Field(default=20, ge=1, le=100)
    sources: list[Literal['openalex', 'crossref']] = Field(default_factory=lambda: ['openalex', 'crossref'], min_length=1)
    @model_validator(mode='after')
    def dates(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError('Start date must precede end date')
        if not self.query.strip():
            raise ValueError('Enter a query')
        return self

class Hit(BaseModel):
    source: str
    source_id: str
    doi: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    publication_date: str | None = None
    journal: str | None = None
    publisher_url: str | None = None
    citations: int | None = None
    oa_locations: list[dict] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)

class LibraryPatch(BaseModel):
    in_library: bool | None = None
    starred: bool | None = None
    status: Literal['unread', 'reading', 'completed'] | None = None
    notes: str | None = None
    tags: list[str] | None = None

class ImportRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=1000)
    work_id: int | None = None

class Rect(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

class AnnotationInput(BaseModel):
    file_id: int
    page: int = Field(ge=1)
    text: str = Field(min_length=1)
    context: str = ''
    rects: list[Rect] = Field(default_factory=list)
    note: str = ''
    tags: list[str] = Field(default_factory=list)
    kind: Literal['highlight', 'evidence', 'writing'] = 'highlight'
