#!/usr/bin/env python
"""Test script to verify document upload and processing"""
import sys
import time
import requests
import json

# Configuration
API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def test_health():
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            log("✓ Backend is running")
            return True
        else:
            log("✗ Backend health check failed", "ERROR")
            return False
    except Exception as e:
        log(f"✗ Backend not responding: {e}", "ERROR")
        return False

def register_user():
    """Register a test user"""
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPassword123!"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            log(f"✓ User registered successfully")
            return token
        elif response.status_code == 400:
            log("! User already exists (using existing token from login)")
            # Try to login
            response = requests.post(
                f"{API_URL}/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPassword123!"
                },
                timeout=10
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                log(f"✓ User logged in successfully")
                return token
        
        log(f"✗ Auth failed: {response.text}", "ERROR")
        return None
    except Exception as e:
        log(f"✗ Auth error: {e}", "ERROR")
        return None

def create_test_file():
    """Create a test text file"""
    try:
        with open("test_document.txt", "w") as f:
            f.write("This is a test document.\n")
            f.write("It contains multiple sentences.\n")
            f.write("Each sentence is on its own line.\n")
            f.write("This helps test the chunking functionality.\n")
            f.write("The document processor should extract this text.\n")
            f.write("Then it will create chunks from the text.\n")
            f.write("Embeddings will be generated for each chunk.\n")
            f.write("Finally, the document status should be 'completed'.\n")
        
        log("✓ Test file created")
        return "test_document.txt"
    except Exception as e:
        log(f"✗ Failed to create test file: {e}", "ERROR")
        return None

def get_workspace(token):
    """Get user's workspace"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/workspaces/",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            workspaces = response.json()
            if workspaces:
                workspace_id = workspaces[0]["id"]
                log(f"✓ Got workspace {workspace_id}")
                return workspace_id
        
        log(f"✗ Failed to get workspace: {response.text}", "ERROR")
        return None
    except Exception as e:
        log(f"✗ Workspace error: {e}", "ERROR")
        return None

def upload_document(token, workspace_id, file_path):
    """Upload a document"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{API_URL}/documents/upload?workspace_id={workspace_id}",
                headers=headers,
                files=files,
                timeout=60  # Allow 60 seconds for upload
            )
        
        if response.status_code == 200:
            data = response.json()
            doc_id = data["document_id"]
            log(f"✓ Document uploaded: ID={doc_id}, Status={data['status']}")
            return doc_id
        else:
            log(f"✗ Upload failed: {response.status_code} - {response.text}", "ERROR")
            return None
    except Exception as e:
        log(f"✗ Upload error: {e}", "ERROR")
        return None

def check_document_status(token, workspace_id, doc_id, max_wait=30):
    """Poll document status until it's processed"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(
                f"{API_URL}/documents/{doc_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data["status"]
                chunks = data["chunk_count"]
                embeddings = data["embedding_count"]
                
                log(f"Status: {status}, Chunks: {chunks}, Embeddings: {embeddings}")
                
                if status == "completed":
                    log(f"✓ Document processing completed!")
                    return True
                elif status == "failed":
                    log(f"✗ Document processing failed", "ERROR")
                    return False
                else:
                    # Still processing
                    time.sleep(2)
                    continue
            else:
                log(f"✗ Status check failed: {response.text}", "ERROR")
                return False
        
        log(f"✗ Document processing timed out after {max_wait}s", "ERROR")
        return False
    except Exception as e:
        log(f"✗ Status check error: {e}", "ERROR")
        return False

def main():
    """Run all tests"""
    log("=" * 60)
    log("DocMind Upload Test Suite")
    log("=" * 60)
    
    # Check backend
    if not test_health():
        log("Backend is not running. Start it with: python backend/main.py", "ERROR")
        return False
    
    # Register/Login
    token = register_user()
    if not token:
        return False
    
    # Create test file
    file_path = create_test_file()
    if not file_path:
        return False
    
    # Get workspace
    workspace_id = get_workspace(token)
    if not workspace_id:
        return False
    
    # Upload
    log("\nUploading document...")
    doc_id = upload_document(token, workspace_id, file_path)
    if not doc_id:
        return False
    
    # Wait for processing
    log(f"\nWaiting for document {doc_id} to process...")
    if not check_document_status(token, workspace_id, doc_id):
        return False
    
    log("\n" + "=" * 60)
    log("✓ All tests passed!")
    log("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
