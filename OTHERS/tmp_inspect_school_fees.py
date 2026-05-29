from sqlalchemy import create_engine, inspect, text
from app.conf.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)
print('DATABASE_URL=', settings.DATABASE_URL)
print('tables=', inspector.get_table_names())
if 'school_fees' in inspector.get_table_names():
    cols = [c['name'] for c in inspector.get_columns('school_fees')]
    print('columns=', cols)
    idxs = inspector.get_indexes('school_fees')
    print('indexes=', [(i['name'], i.get('column_names')) for i in idxs])
    with engine.connect() as conn:
        res = conn.execute(text('SHOW CREATE TABLE school_fees')).fetchone()
        print(res[1])
else:
    print('school_fees table not found')
