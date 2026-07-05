"""Analytics routes with authentication"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from deps import get_db
from routes.auth import get_current_user
from models import Document, Workspace, DocumentChunk, Embedding, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/workspace/{workspace_id}")
async def get_workspace_analytics(
    workspace_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a workspace (requires authentication)"""
    
    # Verify access
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get statistics
    total_documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).count()
    
    completed_documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id,
        Document.status == "completed"
    ).count()
    
    processing_documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id,
        Document.status == "processing"
    ).count()
    
    failed_documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id,
        Document.status == "failed"
    ).count()
    
    # Get chunk and embedding counts
    total_chunks = db.query(DocumentChunk).join(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).count()
    
    total_embeddings = db.query(Embedding).join(DocumentChunk).join(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).count()
    
    # Get storage used
    documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).all()
    
    storage_used = sum(doc.file_size or 0 for doc in documents)
    
    # Get questions asked
    questions_asked = db.query(Message).join(
        DocumentChunk, Message.session_id == DocumentChunk.id, isouter=True
    ).filter(
        Message.role == "user",
        Message.created_at >= start_date
    ).count()
    
    logger.info(f"Analytics retrieved for workspace {workspace_id} by user {current_user.id}")
    
    return {
        "workspace_id": workspace_id,
        "period_days": days,
        "documents": {
            "total": total_documents,
            "completed": completed_documents,
            "processing": processing_documents,
            "failed": failed_documents
        },
        "storage": {
            "total_bytes": storage_used,
            "total_mb": round(storage_used / (1024 * 1024), 2)
        },
        "processing": {
            "total_chunks": total_chunks,
            "total_embeddings": total_embeddings
        },
        "usage": {
            "questions_asked": questions_asked,
            "period_start": start_date.isoformat(),
            "period_end": datetime.utcnow().isoformat()
        }
    }

@router.get("/user")
async def get_user_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall analytics for current user (requires authentication)"""
    
    # Calculate date range
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all user workspaces
    workspaces = db.query(Workspace).filter(
        Workspace.owner_id == current_user.id
    ).all()
    
    workspace_ids = [ws.id for ws in workspaces]
    
    # Get statistics across all workspaces
    total_documents = db.query(Document).filter(
        Document.owner_id == current_user.id
    ).count()
    
    completed_documents = db.query(Document).filter(
        Document.owner_id == current_user.id,
        Document.status == "completed"
    ).count()
    
    total_chunks = db.query(DocumentChunk).join(Document).filter(
        Document.owner_id == current_user.id
    ).count()
    
    total_embeddings = db.query(Embedding).join(DocumentChunk).join(Document).filter(
        Document.owner_id == current_user.id
    ).count()
    
    # Get storage used
    documents = db.query(Document).filter(
        Document.owner_id == current_user.id
    ).all()
    
    storage_used = sum(doc.file_size or 0 for doc in documents)
    
    # Get questions asked
    questions_asked = db.query(Message).filter(
        Message.role == "user",
        Message.created_at >= start_date
    ).count()
    
    logger.info(f"User analytics retrieved for user {current_user.id}")
    
    return {
        "user_id": current_user.id,
        "workspaces_count": len(workspaces),
        "period_days": days,
        "documents": {
            "total": total_documents,
            "completed": completed_documents
        },
        "storage": {
            "total_bytes": storage_used,
            "total_mb": round(storage_used / (1024 * 1024), 2)
        },
        "processing": {
            "total_chunks": total_chunks,
            "total_embeddings": total_embeddings
        },
        "usage": {
            "questions_asked": questions_asked,
            "period_start": start_date.isoformat(),
            "period_end": datetime.utcnow().isoformat()
        }
    }
