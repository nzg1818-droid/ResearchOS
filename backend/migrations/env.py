from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base

config = context.config
target_metadata = Base.metadata

def run():
    connection = config.attributes.get('connection')
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.', poolclass=pool.NullPool)
        with engine.connect() as conn:
            context.configure(connection=conn, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()

run()
