#!/usr/bin/env python
"""Check which database is actually being used"""
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")
print(f"DATABASE_URL from .env: {database_url}")

# Try to connect
from sqlalchemy import create_engine, text

engine = create_engine(database_url)

# Get the actual database file
if "sqlite:///" in database_url:
    db_file = database_url.replace("sqlite:///", "")
    print(f"SQLite database file: {db_file}")
    print(f"File exists: {os.path.exists(db_file)}")
    if os.path.exists(db_file):
        print(f"File size: {os.path.getsize(db_file)} bytes")

# Try to query
try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT COUNT(*) FROM document"))
        count = result.fetchone()[0]
        print(f"Documents in actual database: {count}")
except Exception as e:
    print(f"Error querying: {e}")
