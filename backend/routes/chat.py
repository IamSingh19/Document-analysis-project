"""Chat and conversation routes with RAG integration"""
from fastapi import APIRouter, Depends, Query, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, AsyncGenerator
from datetime import datetime
import json
import logging
import asyncio

from services.llm_handler import LLMHandler
from services.rag_engine import RAGEngine, SemanticSearch, ContextBuilder, RAGConfig
from services.document_processor import EmbeddingGenerator
from models import User, ChatSession, Message, Document, DocumentChunk, Workspace
from deps import get_db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize RAG components
rag_config = RAGConfig()
rag_engine = RAGEngine()
llm_handler = LLMHandler()
semantic_search = SemanticSearch(rag_engine)
embedding_gen = EmbeddingGenerator()

# WebSocket connection management
class ConnectionManager:
    """Manage WebSocket connections for real-time chat"""
    
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, session_id: int, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.debug(f"WebSocket connected for session {session_id}")
    
    async def disconnect(self, session_id: int):
        """Remove WebSocket connection"""
        self.active_connections.pop(session_id, None)
        logger.debug(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: int, message: str):
        """Send message to connected client"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                await self.disconnect(session_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        disconnected = []
        for session_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(session_id)
        
        for session_id in disconnected:
            await self.disconnect(session_id)

manager = ConnectionManager()

# ============ REST Endpoints ============

@router.post("/sessions")
async def create_chat_session(
    workspace_id: int = Query(...),
    document_ids: Optional[List[int]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new chat session
    
    Args:
        workspace_id: Workspace to create session in
        document_ids: Optional list of documents for this session
    """
    try:
        
        logger.info(f"Creating session for user {current_user.id}, workspace {workspace_id}, docs {document_ids}")
        
        # Verify workspace exists and user has access
        workspace = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        ).first()
        
        if not workspace:
            logger.error(f"Workspace {workspace_id} not found for user {current_user.id}")
            raise HTTPException(status_code=403, detail="Access denied to workspace")
        
        # Create session
        session = ChatSession(
            user_id=current_user.id,
            document_id=document_ids[0] if document_ids else None,
            title=f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Chat session {session.id} created for user {current_user.id} with docs {document_ids}")
        
        return {
            "session_id": session.id,
            "workspace_id": workspace_id,
            "document_ids": document_ids or [],
            "created_at": session.created_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.post("/ask")
async def ask_question(
    session_id: int = Query(...),
    query: str = Query(..., min_length=1, max_length=5000),
    document_ids: Optional[List[int]] = Query(None),
    stream: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Ask a question about documents with RAG
    
    Args:
        session_id: Chat session ID
        query: User's question
        document_ids: Optional specific documents to search
        stream: Whether to stream the response
    """
    try:
        # Validate session and access
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine documents to search
        if document_ids:
            # Verify all documents belong to user
            docs = db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.owner_id == current_user.id
            ).all()
            docs_to_search = [doc.id for doc in docs]
        elif session.document_id:
            docs_to_search = [session.document_id]
        else:
            raise HTTPException(status_code=400, detail="No documents specified")
        
        if not docs_to_search:
            raise HTTPException(status_code=404, detail="Documents not found")
        
        # Generate query embedding
        try:
            query_embedding = embedding_gen.generate_single(query)
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Get document chunks from database
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id.in_(docs_to_search)
        ).all()
        
        if not chunks:
            raise HTTPException(status_code=404, detail="No document content found")
        
        # Search for relevant chunks
        retrieved_chunks = semantic_search.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            k=rag_config.search_k
        )
        
        if not retrieved_chunks:
            retrieved_chunks = [
                {
                    "chunk_id": chunks[0].id,
                    "content": chunks[0].content,
                    "page": chunks[0].page_number,
                    "document_id": chunks[0].document_id,
                    "score": 0.5
                }
            ]
        
        # Build context for LLM
        context, sources = ContextBuilder.build_context(
            retrieved_chunks,
            max_tokens=rag_config.max_context_tokens
        )
        
        # Get conversation history
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
        
        # Store user message
        user_message = Message(
            session_id=session_id,
            role="user",
            content=query,
            sources=None
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # Generate response
        if stream:
            async def response_generator():
                try:
                    # Send metadata first
                    metadata = {
                        "type": "metadata",
                        "session_id": session_id,
                        "sources_count": len(sources)
                    }
                    yield f"data: {json.dumps(metadata)}\n\n"
                    
                    # Stream response
                    full_response = ""
                    async for token in llm_handler.stream_answer(
                        query=query,
                        context=context,
                        conversation_history=conversation_history
                    ):
                        full_response += token
                        chunk = {
                            "type": "content",
                            "content": token,
                            "session_id": session_id
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        await asyncio.sleep(0)  # Yield control to event loop
                    
                    # Send completion with sources
                    completion = {
                        "type": "complete",
                        "session_id": session_id,
                        "sources": sources,
                        "full_response": full_response
                    }
                    yield f"data: {json.dumps(completion)}\n\n"
                    
                    # Save assistant message in background
                    background_tasks.add_task(
                        save_assistant_message,
                        session_id,
                        full_response,
                        sources
                    )
                
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    error = {
                        "type": "error",
                        "message": "Error generating response"
                    }
                    yield f"data: {json.dumps(error)}\n\n"
            
            return StreamingResponse(response_generator(), media_type="text/event-stream")
        
        else:
            # Non-streaming response
            answer, metadata = await llm_handler.generate_answer(
                query=query,
                context=context,
                conversation_history=conversation_history
            )
            
            # Store assistant message
            assistant_message = Message(
                session_id=session_id,
                role="assistant",
                content=answer,
                sources=json.dumps(sources)
            )
            db.add(assistant_message)
            db.commit()
            
            return {
                "session_id": session_id,
                "answer": answer,
                "sources": sources,
                "metadata": metadata,
                "query": query
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question answering error: {e}", exc_info=True)
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Full traceback:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")

@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat messages from a session"""
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "sources": json.loads(msg.sources) if msg.sources else None,
                "created_at": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]
    
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")

@router.get("/sessions")
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List chat sessions for current user"""
    try:
        from sqlalchemy import func
        
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).order_by(ChatSession.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for s in sessions:
            # Count messages without accessing the relationship
            message_count = db.query(func.count(Message.id)).filter(
                Message.session_id == s.id
            ).scalar()
            
            result.append({
                "id": s.id,
                "title": s.title,
                "document_id": s.document_id,
                "message_count": message_count,
                "created_at": s.created_at.isoformat()
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session"""
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete messages
        db.query(Message).filter(Message.session_id == session_id).delete()
        # Delete session
        db.delete(session)
        db.commit()
        
        return {"status": "deleted", "session_id": session_id}
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: int,
    format: str = Query("md", regex="^(md|json|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export chat session as Markdown, JSON, or PDF"""
    from fastapi.responses import FileResponse, StreamingResponse
    import io
    
    try:
        # Validate session and access
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get all messages for this session
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc()).all()
        
        if not messages:
            raise HTTPException(status_code=404, detail="No messages in session")
        
        if format == "json":
            # Export as JSON
            export_data = {
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "sources": json.loads(msg.sources) if msg.sources else None,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
            
            content = json.dumps(export_data, indent=2)
            filename = f"chat_session_{session_id}.json"
            
            # Return as streaming response with proper headers
            return StreamingResponse(
                iter([content.encode()]),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{filename}\"",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
        
        elif format == "pdf":
            # Export as PDF (simple text-based)
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
                from reportlab.lib.units import inch
                
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                story = []
                styles = getSampleStyleSheet()
                
                # Add title
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    textColor="#0066cc",
                    spaceAfter=12
                )
                story.append(Paragraph(f"Chat Session Export", title_style))
                story.append(Paragraph(f"Session ID: {session_id}", styles['Normal']))
                story.append(Paragraph(f"Created: {session.created_at.isoformat()}", styles['Normal']))
                story.append(Spacer(1, 0.3*inch))
                
                # Add messages
                for msg in messages:
                    role_style = ParagraphStyle(
                        'RoleStyle',
                        parent=styles['Normal'],
                        fontName='Helvetica-Bold',
                        textColor="#0066cc" if msg.role == "user" else "#00aa00"
                    )
                    story.append(Paragraph(f"<b>{msg.role.upper()}:</b>", role_style))
                    story.append(Paragraph(msg.content, styles['Normal']))
                    
                    if msg.sources:
                        sources = json.loads(msg.sources)
                        story.append(Paragraph(f"<b>Sources:</b>", styles['Normal']))
                        for src in sources:
                            story.append(Paragraph(
                                f"• Document {src.get('document_id')}, Page {src.get('page')}",
                                styles['Normal']
                            ))
                    
                    story.append(Spacer(1, 0.2*inch))
                
                doc.build(story)
                pdf_buffer.seek(0)
                
                return StreamingResponse(
                    iter([pdf_buffer.getvalue()]),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=\"chat_session_{session_id}.pdf\"",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization"
                    }
                )
            
            except ImportError:
                # Fallback to markdown if reportlab not available
                logger.warning("reportlab not installed, falling back to markdown")
                format = "md"
        
        if format == "md":
            # Export as Markdown
            lines = [
                f"# Chat Session {session_id}",
                f"**Created:** {session.created_at.isoformat()}",
                "",
            ]
            
            for msg in messages:
                lines.append(f"## {msg.role.upper()}")
                lines.append("")
                lines.append(msg.content)
                lines.append("")
                
                if msg.sources:
                    sources = json.loads(msg.sources)
                    lines.append("**Sources:**")
                    for src in sources:
                        lines.append(f"- Document {src.get('document_id')}, Page {src.get('page')}")
                    lines.append("")
            
            content = "\n".join(lines)
            filename = f"chat_session_{session_id}.md"
            
            # Return as streaming response with proper headers
            return StreamingResponse(
                iter([content.encode()]),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{filename}\"",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export session: {str(e)}")

# ============ WebSocket Endpoint ============

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time chat with streaming"""
    try:
        # Note: WebSocket authentication needs to be handled differently
        # You may want to pass token in query params
        await manager.connect(session_id, websocket)
        
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                query = message_data.get("message", "").strip()
                document_ids = message_data.get("document_ids", [])
                
                if not query:
                    continue
                
                # Generate embedding
                query_embedding = embedding_gen.generate_single(query)
                
                # Search chunks
                retrieved_chunks = semantic_search.hybrid_search(
                    query=query,
                    query_embedding=query_embedding,
                    k=rag_config.search_k
                )
                
                # Build context
                context, sources = ContextBuilder.build_context(retrieved_chunks)
                
                # Send searching status
                await manager.send_message(session_id, json.dumps({
                    "type": "searching",
                    "message": "Searching documents..."
                }))
                
                # Generate response with streaming
                full_response = ""
                async for token in llm_handler.stream_answer(query, context):
                    full_response += token
                    await manager.send_message(session_id, json.dumps({
                        "type": "content",
                        "content": token
                    }))
                
                # Send complete with sources
                await manager.send_message(session_id, json.dumps({
                    "type": "complete",
                    "sources": sources,
                    "message_length": len(full_response)
                }))
            
            except json.JSONDecodeError:
                await manager.send_message(session_id, json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.send_message(session_id, json.dumps({
                    "type": "error",
                    "message": "Error processing message"
                }))
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        await manager.disconnect(session_id)

# ============ Helper Functions ============

async def save_assistant_message(session_id: int, content: str, sources: list):
    """Background task to save assistant message to database"""
    try:
        db = next(get_db())
        message = Message(
            session_id=session_id,
            role="assistant",
            content=content,
            sources=json.dumps(sources)
        )
        db.add(message)
        db.commit()
        logger.debug(f"Saved assistant message for session {session_id}")
    except Exception as e:
        logger.error(f"Error saving assistant message: {e}")
    finally:
        db.close()
