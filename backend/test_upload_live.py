#!/usr/bin/env python
"""Live test upload and monitor processing"""
import requests
import time
import json

API_URL = "http://localhost:8000"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# Step 1: Register/Login
log("Step 1: Getting auth token...")
response = requests.post(
    f"{API_URL}/auth/login",
    json={"email": "testuser@test.com", "password": "TestPass123!"}
)
if response.status_code != 200:
    response = requests.post(
        f"{API_URL}/auth/register",
        json={"email": "testuser@test.com", "username": "testuser", "password": "TestPass123!"}
    )

token = response.json()["access_token"]
log(f"[OK] Got token")

# Step 2: Get workspace
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{API_URL}/workspaces/", headers=headers)
workspace_id = response.json()[0]["id"]
log(f"[OK] Using workspace {workspace_id}")

# Step 3: Create test file
test_file = "test_upload_simple.txt"
with open(test_file, "w") as f:
    f.write("This is a test document for upload testing.\n" * 50)

log(f"[OK] Created test file: {test_file}")

# Step 4: Upload
log("Step 4: Uploading file...")
with open(test_file, "rb") as f:
    files = {"file": f}
    response = requests.post(
        f"{API_URL}/documents/upload?workspace_id={workspace_id}",
        headers=headers,
        files=files,
        timeout=120
    )

if response.status_code != 200:
    log(f"[FAIL] Upload failed: {response.status_code}")
    log(f"Response: {response.text}")
    exit(1)

upload_resp = response.json()
doc_id = upload_resp["document_id"]
log(f"[OK] Upload response: {json.dumps(upload_resp, indent=2)}")

# Step 5: Poll for status
log(f"\nStep 5: Monitoring document {doc_id} processing...")
print("=" * 60)

for i in range(60):  # Poll for up to 60 seconds
    response = requests.get(
        f"{API_URL}/documents/{doc_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        log(f"[FAIL] Status check failed: {response.status_code}")
        break
    
    doc = response.json()
    status = doc["status"]
    chunks = doc["chunk_count"]
    embeddings = doc["embedding_count"]
    
    print(f"Status: {status:12} | Chunks: {chunks:3} | Embeddings: {embeddings:3}")
    
    if status == "completed":
        log("[OK] Document processing completed!")
        log(f"Final: {chunks} chunks, {embeddings} embeddings")
        print("=" * 60)
        break
    elif status == "failed":
        log("[FAIL] Document processing failed!")
        print("=" * 60)
        break
    
    time.sleep(1)
else:
    log("[TIMEOUT] Processing did not complete within 60 seconds")

# Step 6: Check database
log("\nStep 6: Verifying in database...")
import sqlite3
conn = sqlite3.connect("docmind.db")
cursor = conn.execute("SELECT COUNT(*) FROM document")
count = cursor.fetchone()[0]
print(f"Total documents in DB: {count}")

cursor = conn.execute("SELECT id, title, status, chunk_count FROM document ORDER BY id DESC LIMIT 3")
print("Recent documents:")
for row in cursor:
    print(f"  ID {row[0]}: {row[1]} - {row[2]} ({row[3]} chunks)")
conn.close()
