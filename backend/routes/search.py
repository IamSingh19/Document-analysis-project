"""Search routes with full authentication"""
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from services.rag_engine import RAGEngine, SemanticSearch
from services.document_processor import EmbeddingGenerator
from deps import get_db
from models import DocumentChunk, Document, Workspace

# Import get_current_user from routes.auth
def get_current_user():
    from routes.auth import get_current_user as _get_current_user
    return _get_current_user

get_current_user = get_current_user()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

rag_engine = RAGEngine()
semantic_search = SemanticSearch(rag_engine)
embedding_gen = EmbeddingGenerator()

# Import auth dependency
from routes.auth import get_current_user

@router.get("/")
async def search(
    query: str = Query(..., min_length=1),
    workspace_id: int = Query(...),
    document_ids: Optional[List[int]] = Query(None),
    search_type: str = Query("hybrid", regex="^(semantic|keyword|hybrid)$"),
    filter_file_type: Optional[str] = Query(None),
    filter_date_from: Optional[str] = Query(None),
    filter_date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Advanced search across documents (requires authentication)"""
    
    # Verify user has access to workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    # Build query
    q = db.query(DocumentChunk).join(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id,
        Document.status == "completed"
    )
    
    # Filter by documents if specified
    if document_ids:
        q = q.filter(DocumentChunk.document_id.in_(document_ids))
    
    # Filter by file type
    if filter_file_type:
        q = q.filter(Document.file_type == filter_file_type)
    
    # Filter by date range
    if filter_date_from:
        try:
            date_from = datetime.fromisoformat(filter_date_from)
            q = q.filter(Document.created_at >= date_from)
        except:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    if filter_date_to:
        try:
            date_to = datetime.fromisoformat(filter_date_to)
            q = q.filter(Document.created_at <= date_to)
        except:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    chunks = q.offset(skip).limit(limit).all()
    
    if not chunks:
        return {
            "query": query,
            "search_type": search_type,
            "results": [],
            "total": 0,
            "skip": skip,
            "limit": limit
        }
    
    # Perform search based on type
    if search_type == "semantic":
        # Generate embedding for query
        query_embedding = embedding_gen.generate_single(query)
        
        # Search
        results = rag_engine.search(query_embedding, k=limit)
    
    elif search_type == "keyword":
        # Keyword search in chunk content
        query_terms = set(query.lower().split())
        results = []
        
        for chunk in chunks:
            content = chunk.content.lower()
            score = sum(1 for term in query_terms if term in content)
            if score > 0:
                results.append({
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "page": chunk.page_number,
                    "document_id": chunk.document_id,
                    "score": score / len(query_terms) if query_terms else 0
                })
        
        results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
    
    else:  # hybrid
        # Combine semantic and keyword search
        query_embedding = embedding_gen.generate_single(query)
        results = semantic_search.hybrid_search(query, query_embedding, chunks, k=limit)
    
    logger.info(f"Search performed by user {current_user.id}: {query}")
    
    return {
        "query": query,
        "search_type": search_type,
        "results": results,
        "total": len(results),
        "skip": skip,
        "limit": limit
    }

@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=100),
    workspace_id: int = Query(...),
    limit: int = Query(5, ge=1, le=10),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on documents (requires authentication)"""
    
    # Verify access
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get chunks containing query terms
    query_terms = set(query.lower().split())
    
    chunks = db.query(DocumentChunk).join(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).all()
    
    suggestions = []
    for chunk in chunks:
        content = chunk.content.lower()
        if any(term in content for term in query_terms):
            suggestions.append({
                "text": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                "document_id": chunk.document_id
            })
    
    return {
        "query": query,
        "suggestions": suggestions[:limit]
    }

@router.get("/filters")
async def get_search_filters(
    workspace_id: int = Query(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available filters for search (requires authentication)"""
    
    # Verify access
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get file types
    file_types = db.query(Document.file_type).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).distinct().all()
    
    # Get date range
    documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).all()
    
    dates = [doc.created_at for doc in documents]
    
    return {
        "file_types": [ft[0] for ft in file_types if ft[0]],
        "date_range": {
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None
        }
    }
