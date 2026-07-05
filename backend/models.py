"""Database models for DocMind AI"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="user")  # admin, manager, user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspaces = relationship("Workspace", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="user")
    
class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_personal = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="workspaces")
    documents = relationship("Document", back_populates="workspace")
    members = relationship("WorkspaceMember", back_populates="workspace")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    file_path = Column(String)
    file_type = Column(String)  # pdf, docx, etc
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    file_size = Column(Integer)
    chunk_count = Column(Integer, default=0)
    embedding_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="documents")
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    sessions = relationship("ChatSession", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    page_number = Column(Integer)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk")

class Embedding(Base):
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"))
    vector = Column(JSON)  # Store as JSON for now
    embedding_model = Column(String, default="bge-m3")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chunk = relationship("DocumentChunk", back_populates="embeddings")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="chat_sessions")
    document = relationship("Document", back_populates="sessions")
    messages = relationship("Message", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # user, assistant
    content = Column(Text)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, default="member")  # owner, manager, member
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="members")

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    total_documents = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    total_embeddings = Column(Integer, default=0)
    questions_asked = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0)
    storage_used = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    resource_type = Column(String)
    resource_id = Column(Integer)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
