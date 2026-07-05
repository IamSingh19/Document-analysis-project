#!/usr/bin/env python
"""Test authentication and document creation flow"""
import requests
import json

API_URL = "http://localhost:8000"

def log(msg):
    print(f"[TEST] {msg}".encode('utf-8', errors='replace').decode('utf-8'))

# Step 1: Register user
log("Step 1: Registering user...")
response = requests.post(
    f"{API_URL}/auth/register",
    json={"email": "testuser@test.com", "username": "testuser", "password": "TestPass123!"}
)

if response.status_code == 200:
    token = response.json()["access_token"]
    log("[OK] User registered, got token")
elif response.status_code == 400:
    log("[*] User already exists, logging in...")
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": "testuser@test.com", "password": "TestPass123!"}
    )
    token = response.json()["access_token"]
    log("[OK] User logged in, got token")
else:
    log(f"[FAIL] Auth failed: {response.status_code} - {response.text}")
    exit(1)

# Step 2: Get workspaces
log("\nStep 2: Getting workspaces...")
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{API_URL}/workspaces/", headers=headers)
if response.status_code == 200:
    workspaces = response.json()
    log(f"[OK] Got {len(workspaces)} workspaces")
    if workspaces:
        workspace_id = workspaces[0]["id"]
        log(f"  Using workspace ID: {workspace_id}")
    else:
        log("[FAIL] No workspaces found")
        exit(1)
else:
    log(f"[FAIL] Failed: {response.status_code} - {response.text}")
    exit(1)

# Step 3: Check current documents
log("\nStep 3: Checking existing documents...")
response = requests.get(f"{API_URL}/documents/?workspace_id={workspace_id}", headers=headers)
if response.status_code == 200:
    docs = response.json()
    log(f"[OK] Found {len(docs)} existing documents")
    for doc in docs:
        print(f"   - {doc['title']}: {doc['status']} (chunks: {doc['chunk_count']})")
else:
    log(f"[FAIL] Failed: {response.status_code} - {response.text}")

# Step 4: Check database directly
log("\nStep 4: Checking database directly...")
from models import User, Document, Workspace
from main import SessionLocal

db = SessionLocal()
users = db.query(User).all()
log(f"Users in DB: {len(users)}")
for user in users:
    print(f"   - {user.username} ({user.email})")

workspaces = db.query(Workspace).all()
log(f"Workspaces in DB: {len(workspaces)}")
for ws in workspaces:
    print(f"   - {ws.name} (owner: {ws.owner_id})")

documents = db.query(Document).all()
log(f"Documents in DB: {len(documents)}")
for doc in documents:
    print(f"   - {doc.title}: {doc.status} (chunks: {doc.chunk_count}, owner: {doc.owner_id})")

db.close()

log("\nTest complete!")
