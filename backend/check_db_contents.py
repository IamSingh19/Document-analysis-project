#!/usr/bin/env python
"""Check actual database contents"""
import sqlite3
import os

db_file = "docmind.db"

if not os.path.exists(db_file):
    print(f"Database file not found: {db_file}")
    exit(1)

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"Tables in {db_file}:")
print(f"Total: {len(tables)}\n")

for (table_name,) in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  {table_name}: {count} rows")
    
    # Show columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns[:5]:  # Show first 5 columns
        print(f"    - {col[1]}: {col[2]}")
    if len(columns) > 5:
        print(f"    ... and {len(columns)-5} more columns")

conn.close()
