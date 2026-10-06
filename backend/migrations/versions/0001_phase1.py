"""Phase 1 initial schema and local full-text index."""
from alembic import op
from app.db import Base
revision = '0001'
down_revision = None

def upgrade():
    Base.metadata.create_all(op.get_bind())
    op.execute('CREATE VIRTUAL TABLE works_fts USING fts5(title, notes, content=works, content_rowid=id)')
    op.execute("CREATE TRIGGER works_ai AFTER INSERT ON works BEGIN INSERT INTO works_fts(rowid,title,notes) VALUES (new.id,new.title,new.notes); END")
    op.execute("CREATE TRIGGER works_ad AFTER DELETE ON works BEGIN INSERT INTO works_fts(works_fts,rowid,title,notes) VALUES ('delete',old.id,old.title,old.notes); END")
    op.execute("CREATE TRIGGER works_au AFTER UPDATE ON works BEGIN INSERT INTO works_fts(works_fts,rowid,title,notes) VALUES ('delete',old.id,old.title,old.notes); INSERT INTO works_fts(rowid,title,notes) VALUES (new.id,new.title,new.notes); END")

def downgrade():
    for name in ('works_ai', 'works_ad', 'works_au'):
        op.execute('DROP TRIGGER ' + name)
    op.execute('DROP TABLE works_fts')
    Base.metadata.drop_all(op.get_bind())
