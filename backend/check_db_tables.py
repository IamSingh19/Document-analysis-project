#!/usr/bin/env python
"""Check database tables"""
import sqlite3
import os

db_path = 'docmind.db'

if not os.path.exists(db_path):
    print(f"Database file does not exist: {db_path}")
    print("Creating tables...")
    from main import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Tables created")

# List tables
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"\nTables in database: {len(tables)}")
for table in tables:
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  - {table}: {count} rows")

conn.close()
