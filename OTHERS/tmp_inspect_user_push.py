from sqlalchemy import create_engine, inspect, text
from app.conf.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)
print('DATABASE_URL=', settings.DATABASE_URL)
print('tables=', inspector.get_table_names())
for table in ['users', 'user_push_tokens']:
    if table in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns(table)]
        print(f'\n{table} columns=', cols)
        idxs = inspector.get_indexes(table)
        print(f'{table} indexes=', [(i['name'], i.get('column_names')) for i in idxs])
        with engine.connect() as conn:
            res = conn.execute(text(f'SHOW CREATE TABLE {table}')).fetchone()
            print(res[1])
    else:
        print(f'\n{table} not found')
