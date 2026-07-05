"""Document upload and management routes"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Query, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import logging
import aiofiles
import uuid
from pathlib import Path
import threading

from services.document_processor import DocumentProcessor, TextChunker, EmbeddingGenerator
from services.rag_engine import RAGEngine
from models import User, Document, DocumentChunk, Embedding
from deps import get_db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize services
processor = DocumentProcessor()
chunker = TextChunker()
embedding_gen = EmbeddingGenerator()
rag_engine = RAGEngine()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 52428800))  # 50MB default
ALLOWED_TYPES = ["pdf", "docx", "pptx", "txt", "csv", "md"]

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and process a document"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{file_ext}' not supported. Allowed: {', '.join(ALLOWED_TYPES)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
            )
        
        # Generate unique filename
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = UPLOAD_DIR / unique_name
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        # Create document record
        document = Document(
            title=file.filename,
            file_path=str(file_path),
            file_type=file_ext,
            workspace_id=workspace_id,
            owner_id=current_user.id,
            file_size=len(file_content),
            status="processing",
            chunk_count=0,
            embedding_count=0
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Schedule background processing with threading to ensure execution
        print(f"\n[UPLOAD] Scheduling background task for document {document.id}")
        thread = threading.Thread(
            target=process_document_task,
            args=(document.id, str(file_path), file_ext),
            daemon=False
        )
        thread.start()
        logger.info(f"Document uploaded: {document.id} by user {current_user.id}")
        
        return {
            "document_id": document.id,
            "filename": file.filename,
            "status": "processing",
            "file_size": len(file_content),
            "message": "Document uploaded successfully. Processing in background."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload document")

def process_document_task(doc_id: int, file_path: str, file_type: str):
    """Background task: Process document and generate embeddings with fresh DB session
    
    NOTE: This runs in a separate thread and manages its own database session.
    """
    from main import SessionLocal  # Import here to avoid circular imports
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"[PROCESSING START] Document ID: {doc_id}")
        print(f"{'='*60}\n")
        logger.info(f"Starting processing for document {doc_id}")
        
        # Step 1: Read file
        print(f"[1/6] Reading file: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "rb") as f:
            file_content = f.read()
        print(f"[1/6] ✓ File read: {len(file_content)} bytes\n")
        
        # Step 2: Extract text
        print(f"[2/6] Extracting text from {file_type}...")
        text, metadata = processor.extract_text(file_content, file_type)
        
        # Handle minimal or empty content
        if not text or len(text.strip()) < 20:
            if "error" in metadata:
                raise ValueError(f"Text extraction failed: {metadata['error']}")
            raise ValueError("Extracted text is too short or empty")
        
        print(f"[2/6] ✓ Extracted {len(text)} characters")
        
        # Warn if many pages had no text (likely images)
        if "empty_pages" in metadata and metadata["empty_pages"]:
            empty_count = len(metadata.get("empty_pages", []))
            total_pages = metadata.get("pages", 0)
            if total_pages > 0:
                percentage = (empty_count / total_pages) * 100
                print(f"[2/6] ! Warning: {percentage:.0f}% of pages are image-based")
                if percentage > 80:
                    print(f"[2/6] ! Document is mostly images/scanned - may have limited searchable content")
        print()
        
        # Step 3: Chunk text
        print(f"[3/6] Chunking text...")
        chunks = chunker.chunk_text(text)
        if not chunks:
            raise ValueError("No chunks created from document")
        print(f"[3/6] ✓ Created {len(chunks)} chunks\n")
        
        # Step 4: Generate embeddings
        print(f"[4/6] Generating embeddings for {len(chunks)} chunks...")
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = embedding_gen.generate(chunk_texts)
        if len(embeddings) != len(chunks):
            raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
        print(f"[4/6] ✓ Generated {len(embeddings)} embeddings\n")
        
        # Step 5: Get document from DB
        print(f"[5/6] Fetching document from database...")
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {doc_id} not found in database")
        print(f"[5/6] ✓ Found: {document.title}\n")
        
        # Step 6: Store chunks and embeddings
        print(f"[6/6] Storing {len(chunks)} chunks and embeddings...")
        stored_count = 0
        BATCH_SIZE = 20  # Store in batches to reduce memory usage
        
        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(chunks))
            
            for i in range(batch_start, batch_end):
                chunk = chunks[i]
                embedding = embeddings[i]
                
                try:
                    # Create chunk
                    db_chunk = DocumentChunk(
                        document_id=doc_id,
                        chunk_index=i,
                        page_number=chunk.get("page", 1),
                        content=chunk["content"]
                    )
                    db.add(db_chunk)
                    db.flush()
                    
                    # Create embedding
                    db_embedding = Embedding(
                        chunk_id=db_chunk.id,
                        vector=embedding,
                        embedding_model="bge-m3"
                    )
                    db.add(db_embedding)
                    
                    # Add to RAG engine
                    rag_engine.add_embeddings(
                        db_chunk.id,
                        embedding,
                        {
                            "content": chunk["content"],
                            "page": chunk.get("page", 1),
                            "document_id": doc_id
                        }
                    )
                    stored_count += 1
                    
                except Exception as chunk_error:
                    logger.error(f"Error storing chunk {i}: {chunk_error}")
                    db.rollback()
                    raise
            
            # Commit batch
            db.commit()
            progress = min(batch_end, len(chunks))
            print(f"   Batch {batch_end}/{len(chunks)} stored")
        
        # Update document status
        document.chunk_count = len(chunks)
        document.embedding_count = len(embeddings)
        document.status = "completed"
        document.updated_at = datetime.utcnow()
        db.commit()
        
        print(f"[6/6] ✓ Stored {stored_count} chunks\n")
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Document {doc_id} completed!")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Embeddings: {len(embeddings)}")
        print(f"{'='*60}\n")
        logger.info(f"Document {doc_id} successfully processed")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"[ERROR] Processing failed for document {doc_id}")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"{'='*60}\n")
        logger.error(f"Processing error for document {doc_id}: {str(e)}", exc_info=True)
        
        # Mark as failed
        try:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                document.status = "failed"
                document.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Document {doc_id} marked as failed")
                print(f"[STATUS] Document marked as FAILED in database")
        except Exception as update_error:
            logger.error(f"Could not update document status: {update_error}")
    
    finally:
        try:
            db.close()
        except Exception as close_error:
            logger.error(f"Error closing database session: {close_error}")

@router.get("/")
async def list_documents(
    workspace_id: int = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents in a workspace"""
    documents = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "file_type": doc.file_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "embedding_count": doc.embedding_count,
            "file_size": doc.file_size,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        }
        for doc in documents
    ]

@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document details"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": document.id,
        "title": document.title,
        "file_type": document.file_type,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "embedding_count": document.embedding_count,
        "file_size": document.file_size,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
        "owner_id": document.owner_id,
        "workspace_id": document.workspace_id
    }

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Delete file
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete chunks and embeddings
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        for chunk in chunks:
            db.query(Embedding).filter(Embedding.chunk_id == chunk.id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Delete document
        db.delete(document)
        db.commit()
        
        logger.info(f"Document {document_id} deleted by user {current_user.id}")
        
        return {"message": "Document deleted successfully"}
    
    except Exception as e:
        logger.error(f"Delete error for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")

@router.get("/{document_id}/summary")
async def summarize_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI summary of document"""
    from services.llm_handler import LLMHandler
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail="Document is not yet processed")
    
    try:
        # Get chunks
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).limit(20).all()
        
        if not chunks:
            return {
                "document_id": document_id,
                "executive_summary": "No content available for summarization",
                "key_findings": [],
                "action_items": []
            }
        
        content = "\n".join([chunk.content for chunk in chunks])
        
        llm = LLMHandler()
        summary = await llm.summarize_document(content)
        
        return {
            "document_id": document_id,
            **summary
        }
    
    except Exception as e:
        logger.error(f"Summarization error for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to summarize document")
