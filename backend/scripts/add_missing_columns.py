"""
Add missing columns to database tables based on model definitions.
Only adds columns (never drops), always nullable for safety.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
from sqlalchemy import inspect, text
from app import models
import sqlalchemy.orm

insp = inspect(engine)

# Collect all ADD COLUMN statements needed
alter_stmts = []
for cls_name in sorted(dir(models)):
    cls = getattr(models, cls_name)
    if not (isinstance(cls, type) and hasattr(cls, '__tablename__')):
        continue
    table = cls.__tablename__
    if table not in insp.get_table_names():
        continue
    db_cols = set(c['name'] for c in insp.get_columns(table))
    mapper = sqlalchemy.inspect(cls)
    for attr in mapper.column_attrs:
        col = attr.columns[0]
        col_name = col.key
        if col_name in db_cols:
            continue
        # Determine SQL type
        col_type = col.type.compile(engine.dialect)
        alter_stmts.append(
            f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type} NULL'
        )

print(f"Total ALTER statements: {len(alter_stmts)}")

# Execute all
success = 0
errors = 0
with engine.begin() as conn:
    for stmt in alter_stmts:
        try:
            conn.execute(text(stmt))
            success += 1
        except Exception as e:
            print(f"  [ERROR] {stmt}: {e}")
            errors += 1

print(f"Done: {success} columns added, {errors} errors")
