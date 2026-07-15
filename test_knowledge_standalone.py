"""
Standalone test for IPC Knowledge Base
Avoids import conflicts by running from project root
"""

import asyncio
import sys
from pathlib import Path

# Add agent directory to path
project_root = Path(__file__).parent
agent_dir = project_root / "agent"
sys.path.insert(0, str(agent_dir))

# Import before any other tools imports to avoid calendar conflict
import os

os.environ["PYTHONPATH"] = str(agent_dir)

from dotenv import load_dotenv

# Load environment
env_path = project_root / ".env.local"
if env_path.exists():
    load_dotenv(env_path)

# Import knowledge module directly (avoiding tools/calendar.py conflict)
# by using importlib with explicit path
import importlib.util

knowledge_path = agent_dir / "tools" / "knowledge.py"
spec = importlib.util.spec_from_file_location("knowledge_module", knowledge_path)
knowledge = importlib.util.module_from_spec(spec)

# Temporarily remove calendar.py from path to avoid conflict
import sys

if str(agent_dir / "tools") in sys.path:
    sys.path.remove(str(agent_dir / "tools"))

spec.loader.exec_module(knowledge)
get_knowledge_base = knowledge.get_knowledge_base


async def run_knowledge_base_test():
    """Test knowledge base loading and search functionality"""
    print("=" * 60)
    print("IPC Knowledge Base Test")
    print("=" * 60)

    kb = get_knowledge_base()

    # Test 1: Load knowledge base
    print("\n[Test 1] Loading knowledge base...")
    try:
        await kb.load()
        print("✅ Knowledge base loaded successfully")
        print(f"   - Chunks loaded: {len(kb.chunks)}")
        assert len(kb.chunks) > 20, f"Expected >20 chunks, got {len(kb.chunks)}"
    except Exception as e:
        print(f"❌ Failed to load knowledge base: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 2: Search for hours
    print("\n[Test 2] Searching for 'what are your hours'...")
    try:
        result = await kb.search("what are your hours", top_k=3)
        print("✅ Search completed")
        print(f"   Result preview: {result[:200]}...")
        assert (
            "hours" in result.lower()
            or "monday" in result.lower()
            or "friday" in result.lower()
        ), "Result should contain hours information"
        print("✅ Result contains hours information")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Search for membership pricing
    print("\n[Test 3] Searching for 'membership pricing'...")
    try:
        result = await kb.search("membership pricing", top_k=3)
        print("✅ Search completed")
        print(f"   Result preview: {result[:200]}...")
        assert (
            "$29" in result
            or "membership" in result.lower()
            or "pricing" in result.lower()
        ), "Result should contain pricing information"
        print("✅ Result contains pricing information")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 4: Verify chunks have embeddings
    print("\n[Test 4] Verifying embeddings...")
    try:
        assert kb._embeddings_loaded, "Embeddings should be loaded"
        assert all("embedding" in chunk for chunk in kb.chunks), (
            "All chunks should have embeddings"
        )
        print(f"✅ All {len(kb.chunks)} chunks have embeddings")
    except Exception as e:
        print(f"❌ Embedding verification failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_knowledge_base_test())
    sys.exit(0 if success else 1)
