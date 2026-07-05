import os
import logging
from typing import List, AsyncGenerator, Optional, Tuple
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class LLMHandler:
    """Handle interactions with LLM using Groq (free, fast, no API key needed for basic usage)"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        self.client = None
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.7))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", 2000))
        
        logger.info(f"LLM init: api_key={'SET' if self.api_key else 'NOT SET'}, model={self.model}")
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set or empty, using fallback responses")
            return
        
        if len(self.api_key) < 10:
            logger.warning(f"GROQ_API_KEY appears invalid (too short: {len(self.api_key)} chars), using fallback")
            self.api_key = ""
            return
        
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=self.api_key)
            logger.info(f"LLM initialized successfully with Groq model: {self.model}")
        except ImportError as e:
            logger.error(f"Groq library import error: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Groq client initialization error: {e}", exc_info=True)
            self.client = None
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[dict]] = None
    ) -> Tuple[str, dict]:
        """Generate answer from query and context using Groq
        
        Args:
            query: User's question
            context: Retrieved context from documents
            conversation_history: Previous messages for context
        
        Returns:
            Tuple of (answer_text, metadata)
        """
        
        messages = [
            {
                "role": "system",
                "content": """You are DocMind AI, an intelligent document analysis assistant.
                
Your role is to help users understand documents through detailed, accurate, and well-cited responses.

Guidelines:
- Always base your answer on the provided context from documents
- Cite specific pages and document sections
- Be concise but thorough
- If information is not in the context, clearly state "This information is not available in the provided documents"
- Structure your response with clear sections when appropriate
- Use bullet points for lists
- Highlight key findings and insights"""
            }
        ]
        
        # Add conversation history (last 10 messages for context)
        if conversation_history:
            messages.extend(conversation_history[-10:])
        
        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"""Context from documents:
            
{context}

---

User question: {query}

Please provide a detailed answer based on the context above. Always cite which document and page the information comes from."""
        })
        
        if not self.client:
            # Fallback response
            return self._fallback_answer(query, context)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )
            
            answer = response.choices[0].message.content
            metadata = {
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Generated answer using Groq {self.model}")
            return answer, metadata
        
        except Exception as e:
            logger.error(f"Groq LLM error: {e}", exc_info=True)
            return self._fallback_answer(query, context)
    
    async def stream_answer(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[dict]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream answer generation token by token using Groq
        
        Yields:
            str: Individual tokens from the LLM response
        """
        
        logger.info(f"stream_answer called. client={self.client is not None}, model={self.model}")
        
        messages = [
            {
                "role": "system",
                "content": """You are DocMind AI, an intelligent document analysis assistant.
                
Your role is to help users understand documents through detailed, accurate, and well-cited responses.

Guidelines:
- Always base your answer on the provided context from documents
- Cite specific pages and document sections
- Be concise but thorough
- If information is not in the context, clearly state "This information is not available in the provided documents"
- Structure your response with clear sections when appropriate"""
            }
        ]
        
        if conversation_history:
            messages.extend(conversation_history[-10:])
        
        messages.append({
            "role": "user",
            "content": f"""Context from documents:
            
{context}

---

User question: {query}

Provide a detailed answer based on the context above."""
        })
        
        if not self.client:
            logger.warning("No client, using fallback")
            # Yield fallback response token by token
            answer, _ = self._fallback_answer(query, context)
            for word in answer.split():
                yield word + " "
            return
        
        try:
            logger.info(f"Calling Groq API with model {self.model}")
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            logger.info("Got stream response, yielding chunks")
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("Streaming response completed")
        
        except Exception as e:
            logger.error(f"Stream error in stream_answer: {type(e).__name__}: {e}", exc_info=True)
            answer, _ = self._fallback_answer(query, context)
            yield answer
    
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text using Groq
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
        
        Returns:
            str: Summary of the text
        """
        messages = [
            {
                "role": "system",
                "content": "You are a document summarization expert. Provide concise, accurate summaries."
            },
            {
                "role": "user",
                "content": f"Summarize the following text in {max_length} characters:\n\n{text}"
            }
        ]
        
        if not self.client:
            return text[:max_length]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return text[:max_length]
    
    async def extract_entities(self, text: str) -> dict:
        """Extract key entities from text using Groq
        
        Returns:
            dict: {entities_type: [entity_list]}
        """
        messages = [
            {
                "role": "system",
                "content": """Extract key entities from the text and categorize them.
                Return as JSON with categories like: people, organizations, locations, dates, numbers, concepts."""
            },
            {
                "role": "user",
                "content": f"Extract entities from this text:\n\n{text}"
            }
        ]
        
        if not self.client:
            return {}
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            # Try to parse as JSON
            import json
            result_text = response.choices[0].message.content
            try:
                return json.loads(result_text)
            except:
                return {"raw": result_text}
        
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {}
    
    def _fallback_answer(self, query: str, context: str) -> Tuple[str, dict]:
        """Provide fallback response when Groq is not available"""
        answer = f"""I've reviewed your documents for: "{query}"

Based on the provided context:
{context[:500]}...

To get a full answer, please ensure:
1. GROQ_API_KEY is set in your environment variables
2. Get your free Groq API key from https://console.groq.com
3. The API key has proper permissions

For now, the context above contains information relevant to your query."""
        
        return answer, {
            "model": "fallback",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "Using fallback response - Groq not configured"
        }
