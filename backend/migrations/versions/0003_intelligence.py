"""Paper documents, evidence, immutable decisions and non-secret AI provenance."""
from alembic import op
from app.db import Base
from app.intelligence import models
revision = '0003'
down_revision = '0002'
NAMES = ['paper_documents','document_pages','document_blocks','document_chunks','ai_provider_configs','ai_runs','extraction_runs','paper_extractions','evidence_anchors','verification_decisions','paper_questions','paper_answers']
def upgrade():
    connection = op.get_bind()
    for name in NAMES:
        Base.metadata.tables[name].create(connection)
    op.execute("CREATE VIRTUAL TABLE paper_chunks_fts USING fts5(chunk_id UNINDEXED, work_id UNINDEXED, document_id UNINDEXED, text, tokenize='unicode61')")
def downgrade():
    raise RuntimeError('Restore the pre-migration backup to downgrade without losing evidence')
