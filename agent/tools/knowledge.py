"""
IPC Knowledge Base Tool
RAG implementation for answering questions about Indianapolis Pickleball Club
Uses vector embeddings for semantic search
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio

import numpy as np
from openai import AsyncOpenAI

from livekit.agents import llm

logger = logging.getLogger(__name__)

# Initialize OpenAI client (will use OPENAI_API_KEY from environment)
_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


class KnowledgeBase:
    """IPC Knowledge Base with vector embeddings for semantic search"""

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self._embeddings_loaded = False

    def _load_knowledge_file(self) -> str:
        """Load knowledge.md file"""
        # Get path to persona/knowledge.md relative to this file
        current_dir = Path(__file__).parent.parent.parent
        knowledge_path = current_dir / "persona" / "knowledge.md"

        if not knowledge_path.exists():
            raise FileNotFoundError(f"Knowledge base not found at {knowledge_path}")

        with open(knowledge_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_markdown_chunks(self, content: str) -> List[Dict[str, str]]:
        """Parse markdown into semantic chunks by headers"""
        chunks = []
        lines = content.split("\n")

        current_section = "General"
        current_chunk = []
        current_level = 0

        for line in lines:
            # Detect headers (markdown headers start with #)
            header_match = re.match(r"^(#+)\s+(.+)$", line)
            if header_match:
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(
                            {
                                "section": current_section,
                                "text": chunk_text,
                                "level": current_level,
                            }
                        )

                # Start new section
                header_text = header_match.group(2).strip()
                current_section = header_text
                current_level = len(header_match.group(1))
                current_chunk = [line]  # Include header in chunk
            else:
                # Add line to current chunk
                if line.strip() or current_chunk:
                    current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(
                    {
                        "section": current_section,
                        "text": chunk_text,
                        "level": current_level,
                    }
                )

        # Further split large chunks (if > 10 lines, split by bullet points or paragraphs)
        refined_chunks = []
        for chunk in chunks:
            text = chunk["text"]
            lines = text.split("\n")

            if len(lines) > 10:
                # Split by double newlines (paragraphs) or bullet points
                paragraphs = re.split(r"\n\s*\n", text)
                for para in paragraphs:
                    para = para.strip()
                    if para and len(para) > 50:  # Only include substantial paragraphs
                        refined_chunks.append(
                            {
                                "section": chunk["section"],
                                "text": para,
                                "level": chunk["level"],
                            }
                        )
            else:
                refined_chunks.append(chunk)

        return refined_chunks

    async def _generate_embeddings(
        self, chunks: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for all chunks using OpenAI"""
        client = get_openai_client()
        chunks_with_embeddings = []

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")

        # Process in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk["text"] for chunk in batch]

            try:
                response = await client.embeddings.create(
                    model="text-embedding-3-small", input=texts
                )

                for j, embedding_obj in enumerate(response.data):
                    chunks_with_embeddings.append(
                        {
                            "section": batch[j]["section"],
                            "text": batch[j]["text"],
                            "level": batch[j]["level"],
                            "embedding": embedding_obj.embedding,
                        }
                    )

                logger.debug(f"Generated embeddings for batch {i // batch_size + 1}")

            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {e}")
                raise

        logger.info(f"Successfully generated {len(chunks_with_embeddings)} embeddings")
        return chunks_with_embeddings

    async def load(self):
        """Load knowledge base and generate embeddings (called at module import)"""
        if self._embeddings_loaded:
            return

        try:
            # Load and parse markdown
            content = self._load_knowledge_file()
            chunks = self._parse_markdown_chunks(content)
            logger.info(f"Parsed {len(chunks)} chunks from knowledge base")

            # Generate embeddings
            self.chunks = await self._generate_embeddings(chunks)
            self._embeddings_loaded = True
            logger.info("Knowledge base loaded and ready")

        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            raise

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (legacy method, use _cosine_similarity_fast)"""
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)

        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def search(self, query: str, top_k: int = 3) -> str:
        """Search knowledge base using semantic similarity - optimized for low latency"""
        import time

        start_time = time.time()

        if not self._embeddings_loaded:
            await self.load()

        if not self.chunks:
            return "Knowledge base is empty."

        try:
            # Generate embedding for query (fastest model: text-embedding-3-small)
            embed_start = time.time()
            client = get_openai_client()
            response = await client.embeddings.create(
                model="text-embedding-3-small",  # Fast, cost-effective model
                input=[query],
            )
            query_embedding = response.data[0].embedding
            embed_time = time.time() - embed_start
            logger.debug(f"RAG: Embedding generation took {embed_time * 1000:.1f}ms")

            # Calculate similarities (vectorized for speed)
            search_start = time.time()
            similarities = []
            query_vec = np.array(query_embedding)

            # Use numpy for faster vector operations
            for chunk in self.chunks:
                chunk_vec = np.array(chunk["embedding"])
                similarity = self._cosine_similarity_fast(query_vec, chunk_vec)
                similarities.append((similarity, chunk))

            # Sort by similarity and get top K
            similarities.sort(key=lambda x: x[0], reverse=True)
            top_results = similarities[:top_k]
            search_time = time.time() - search_start
            logger.debug(f"RAG: Similarity search took {search_time * 1000:.1f}ms")

            # Format results
            if not top_results or top_results[0][0] < 0.3:  # Low similarity threshold
                total_time = time.time() - start_time
                logger.debug(
                    f"RAG: No results found (total: {total_time * 1000:.1f}ms)"
                )
                return "I couldn't find relevant information about that topic."

            results = []
            for similarity, chunk in top_results:
                results.append(f"[{chunk['section']}]\n{chunk['text']}")

            total_time = time.time() - start_time
            logger.info(
                f"RAG: Found {len(top_results)} results in {total_time * 1000:.1f}ms (embed: {embed_time * 1000:.1f}ms, search: {search_time * 1000:.1f}ms)"
            )

            return "\n\n---\n\n".join(results)

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(
                f"RAG: Error searching knowledge base (took {total_time * 1000:.1f}ms): {e}"
            )
            return f"Error searching knowledge base: {str(e)}"

    def _cosine_similarity_fast(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Fast cosine similarity using numpy (optimized version)"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Global knowledge base instance
_knowledge_base: Optional[KnowledgeBase] = None
_load_task: Optional[asyncio.Task] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create global knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base


async def _preload_knowledge_base():
    """Preload knowledge base at module import (prewarm pattern)"""
    try:
        kb = get_knowledge_base()
        await kb.load()
        logger.info(f"Knowledge base preloaded: {len(kb.chunks)} chunks ready")
    except Exception as e:
        logger.warning(f"Failed to preload knowledge base (will load on demand): {e}")


# Start preloading in background (non-blocking)
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    # Module imported outside an async runtime; load on first use.
    pass
else:
    _load_task = loop.create_task(_preload_knowledge_base())


# Function tool for LLM to call
@llm.function_tool(
    description="Query the IPC knowledge base for information about Indianapolis Pickleball Club, including hours, membership, pricing, programs, policies, and facilities"
)
async def query_ipc_knowledge(query: str) -> str:
    """
    Search the IPC knowledge base for information.

    Args:
        query: The question or topic to search for (e.g., "what are your hours?", "membership pricing")

    Returns:
        Relevant information from the knowledge base
    """
    kb = get_knowledge_base()
    return await kb.search(query, top_k=3)
