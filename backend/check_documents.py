#!/usr/bin/env python
"""Check document status in database"""
from models import Document
from main import SessionLocal

db = SessionLocal()
docs = db.query(Document).order_by(Document.id.desc()).limit(10).all()

print(f"Total documents checked: {len(docs)}\n")
print("Recent documents:")
print("-" * 80)

for doc in docs:
    status_icon = "✓" if doc.status == "completed" else "✗" if doc.status == "failed" else "⏳"
    print(f"{status_icon} ID: {doc.id}")
    print(f"   Title: {doc.title}")
    print(f"   Status: {doc.status}")
    print(f"   Chunks: {doc.chunk_count} | Embeddings: {doc.embedding_count}")
    print(f"   File: {doc.file_path}")
    print()

db.close()
