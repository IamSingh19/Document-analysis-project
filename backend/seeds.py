"""Seed database with test data"""

from main import SessionLocal, User, Workspace, Document, ChatSession, Message
import bcrypt
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def seed_data():
    db = SessionLocal()
    
    # Clear existing data (careful in production!)
    # db.query(User).delete()
    # db.commit()
    
    # Create test users
    users = [
        User(
            email="admin@docmind.com",
            username="admin",
            hashed_password=hash_password("admin123"),
            is_active=True,
            is_verified=True,
            role="admin"
        ),
        User(
            email="user@docmind.com",
            username="testuser",
            hashed_password=hash_password("user123"),
            is_active=True,
            is_verified=True,
            role="user"
        ),
    ]
    
    for user in users:
        existing = db.query(User).filter(User.email == user.email).first()
        if not existing:
            db.add(user)
    
    db.commit()
    
    # Get users
    admin = db.query(User).filter(User.email == "admin@docmind.com").first()
    testuser = db.query(User).filter(User.email == "user@docmind.com").first()
    
    # Create workspaces
    workspaces = [
        Workspace(
            name="Admin's Workspace",
            owner_id=admin.id,
            is_personal=True
        ),
        Workspace(
            name="Test User Workspace",
            owner_id=testuser.id,
            is_personal=True
        ),
    ]
    
    for ws in workspaces:
        existing = db.query(Workspace).filter(Workspace.name == ws.name).first()
        if not existing:
            db.add(ws)
    
    db.commit()
    
    admin_ws = db.query(Workspace).filter(Workspace.owner_id == admin.id).first()
    
    # Create test documents
    documents = [
        Document(
            title="Sample Research Paper",
            file_path="/uploads/research.pdf",
            file_type="pdf",
            workspace_id=admin_ws.id,
            owner_id=admin.id,
            file_size=1024000,
            chunk_count=50,
            embedding_count=50,
            status="completed"
        ),
        Document(
            title="Contract Template",
            file_path="/uploads/contract.docx",
            file_type="docx",
            workspace_id=admin_ws.id,
            owner_id=admin.id,
            file_size=512000,
            chunk_count=30,
            embedding_count=30,
            status="completed"
        ),
    ]
    
    for doc in documents:
        existing = db.query(Document).filter(Document.title == doc.title).first()
        if not existing:
            db.add(doc)
    
    db.commit()
    
    print("✅ Seed data created successfully")
    print(f"  - Created {len(users)} users")
    print(f"  - Created {len(workspaces)} workspaces")
    print(f"  - Created {len(documents)} documents")
    print("\nTest credentials:")
    print("  Admin: admin@docmind.com / admin123")
    print("  User: user@docmind.com / user123")

if __name__ == "__main__":
    seed_data()
