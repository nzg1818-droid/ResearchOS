"""Portable file references, indexed identities, run provenance and Zotero sync state."""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from app.db import Base
from app import phase2_models
from app.textutils import normalized
revision='0002'
down_revision='0001'

def upgrade():
    op.add_column('works',sa.Column('title_key',sa.String(),nullable=False,server_default=''))
    op.add_column('works',sa.Column('author_key',sa.String(),nullable=False,server_default=''))
    connection=op.get_bind()
    for row in connection.execute(sa.text('SELECT id,title,authors FROM works')).mappings():
        authors=json.loads(row['authors'] or '[]')
        connection.execute(sa.text('UPDATE works SET title_key=:title,author_key=:author WHERE id=:id'),{'title':normalized(row['title']),'author':normalized(authors[0]) if authors else '', 'id':row['id']})
    op.create_index('ix_works_title_identity','works',['title_key','author_key','year'])
    op.add_column('source_hits',sa.Column('snapshot_hash',sa.String(),nullable=True))
    op.create_index('ix_source_hits_snapshot_hash','source_hits',['snapshot_hash'])
    op.add_column('annotations',sa.Column('context_before',sa.Text(),nullable=False,server_default=''))
    op.add_column('annotations',sa.Column('context_after',sa.Text(),nullable=False,server_default=''))
    root=Path(op.get_context().config.attributes['data_root'])
    from app.storage import Storage
    storage=Storage(root)
    for row in connection.execute(sa.text('SELECT id,path,sha256 FROM files')).mappings():
        key=storage.key(row['sha256']);destination=storage.resolve(key)
        original=Path(row['path'])
        # Copies of a whole Phase 1 data folder already contain files/<hash>.pdf.
        # If not, recover the original managed file by copying, never moving it.
        if not destination.exists() and original.is_absolute() and original.is_file():
            storage.copy(original,row['sha256'])
        connection.execute(sa.text('UPDATE files SET path=:path WHERE id=:id'),{'path':key,'id':row['id']})
    names=['search_runs','search_run_hits','remote_libraries','zotero_sync_state','external_attachments','remote_notes','collection_mappings','maintenance_events']
    for name in names: Base.metadata.tables[name].create(connection)
    # Legacy history has no reliable query-to-hit mapping. Label it honestly.
    from app.db import now
    legacy = connection.execute(sa.text('SELECT id,work_id,source FROM source_hits')).mappings().all()
    if legacy:
        result = connection.execute(Base.metadata.tables['search_runs'].insert().values(query='Legacy Phase 1 provenance (query unknown)',mode='legacy',filters={},sources=sorted({r['source'] for r in legacy}),errors={},created_at=now()))
        run_id = result.inserted_primary_key[0]
        connection.execute(Base.metadata.tables['search_run_hits'].insert(),[dict(run_id=run_id,source_hit_id=r['id'],work_id=r['work_id'],source=r['source'],source_id='legacy:'+str(r['id'])) for r in legacy])

def downgrade():
    raise RuntimeError('Restore the automatic pre-migration backup to downgrade safely')
