import faiss
import numpy as np
from typing import List, Tuple, Dict, Optional
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGEngine:
    """Retrieval-Augmented Generation engine using FAISS"""
    
    def __init__(self):
        self.index = None
        self.metadata_store = {}
        self.dimension = 1024
    
    def initialize_index(self):
        """Create FAISS index"""
        self.index = faiss.IndexFlatL2(self.dimension)
    
    def add_embeddings(self, chunk_id: int, embedding: List[float], metadata: dict):
        """Add embedding to index"""
        if self.index is None:
            self.initialize_index()
        
        vector = np.array([embedding]).astype('float32')
        self.index.add(vector)
        self.metadata_store[len(self.metadata_store)] = {
            "chunk_id": chunk_id,
            "content": metadata.get("content", ""),
            "page": metadata.get("page", 1),
            "document_id": metadata.get("document_id"),
            "created_at": datetime.utcnow().isoformat()
        }
    
    def search(self, query_embedding: List[float], k: int = 5) -> List[dict]:
        """Search for similar chunks"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        vector = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(vector, min(k, self.index.ntotal))
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx in self.metadata_store:
                meta = self.metadata_store[idx]
                results.append({
                    "chunk_id": meta["chunk_id"],
                    "content": meta["content"],
                    "page": meta["page"],
                    "document_id": meta["document_id"],
                    "score": float(1 / (1 + distance))
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)


class SemanticSearch:
    """Semantic search with hybrid retrieval"""
    
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        k: int = 5
    ) -> List[dict]:
        """Hybrid search combining vector and keyword"""
        vector_results = self.rag_engine.search(query_embedding, k)
        return sorted(vector_results, key=lambda x: x["score"], reverse=True)[:k]


class ContextBuilder:
    """Build context from retrieved chunks"""
    
    @staticmethod
    def build_context(retrieved_chunks: List[dict], max_tokens: int = 2000) -> Tuple[str, List[dict]]:
        """Build context from chunks"""
        context_parts = []
        sources = []
        token_count = 0
        
        for chunk in retrieved_chunks:
            chunk_text = f"[Document {chunk['document_id']}, Page {chunk['page']}]\n{chunk['content']}\n"
            tokens = len(chunk_text.split())
            
            if token_count + tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            token_count += tokens
            sources.append({
                "document_id": chunk["document_id"],
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"],
                "score": chunk.get("score", 0)
            })
        
        context = "\n".join(context_parts)
        return context, sources


class RAGConfig:
    """Configuration for RAG engine"""
    
    def __init__(self):
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 512))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 50))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", 2000))
        self.search_k = int(os.getenv("SEARCH_K", 5))
        self.vector_weight = float(os.getenv("VECTOR_WEIGHT", 0.7))
        self.keyword_weight = float(os.getenv("KEYWORD_WEIGHT", 0.3))
