"""
Test script for IPC Knowledge Base
Validates core functionality before integration

Run this from the agent directory: python tools/test_knowledge.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure we're importing from the right location
# Run this from agent/ directory to avoid calendar.py conflict
agent_dir = Path(__file__).parent.parent
if Path.cwd() != agent_dir:
    print(f"Warning: Run from agent directory. Current: {Path.cwd()}, Expected: {agent_dir}")

sys.path.insert(0, str(agent_dir))

from dotenv import load_dotenv

# Import knowledge module using absolute import from agent.tools
# This avoids the calendar.py naming conflict
from tools import knowledge
get_knowledge_base = knowledge.get_knowledge_base

# Load environment variables
env_path = agent_dir.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)


async def test_knowledge_base():
    """Test knowledge base loading and search functionality"""
    print("=" * 60)
    print("IPC Knowledge Base Test")
    print("=" * 60)
    
    kb = get_knowledge_base()
    
    # Test 1: Load knowledge base
    print("\n[Test 1] Loading knowledge base...")
    try:
        await kb.load()
        print(f"✅ Knowledge base loaded successfully")
        print(f"   - Chunks loaded: {len(kb.chunks)}")
        assert len(kb.chunks) > 20, f"Expected >20 chunks, got {len(kb.chunks)}"
    except Exception as e:
        print(f"❌ Failed to load knowledge base: {e}")
        return False
    
    # Test 2: Search for hours
    print("\n[Test 2] Searching for 'what are your hours'...")
    try:
        result = await kb.search("what are your hours", top_k=3)
        print(f"✅ Search completed")
        print(f"   Result preview: {result[:200]}...")
        assert "hours" in result.lower() or "monday" in result.lower() or "friday" in result.lower(), \
            "Result should contain hours information"
        print(f"✅ Result contains hours information")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    # Test 3: Search for membership pricing
    print("\n[Test 3] Searching for 'membership pricing'...")
    try:
        result = await kb.search("membership pricing", top_k=3)
        print(f"✅ Search completed")
        print(f"   Result preview: {result[:200]}...")
        assert "$29" in result or "membership" in result.lower() or "pricing" in result.lower(), \
            "Result should contain pricing information"
        print(f"✅ Result contains pricing information")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    # Test 4: Verify chunks have embeddings
    print("\n[Test 4] Verifying embeddings...")
    try:
        assert kb._embeddings_loaded, "Embeddings should be loaded"
        assert all("embedding" in chunk for chunk in kb.chunks), "All chunks should have embeddings"
        print(f"✅ All {len(kb.chunks)} chunks have embeddings")
    except Exception as e:
        print(f"❌ Embedding verification failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_knowledge_base())
    sys.exit(0 if success else 1)

