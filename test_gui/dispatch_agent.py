#!/usr/bin/env python3
"""
Dispatch agent to a LiveKit room
Usage: python dispatch_agent.py <room_name>
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path, override=True)

try:
    from livekit import api
    import asyncio
except ImportError:
    print("❌ LiveKit API not installed. Run: pip install livekit-api")
    sys.exit(1)


def dispatch_agent(room_name: str, agent_name: str = None):
    """Dispatch agent to a room using LiveKit HTTP API"""

    livekit_url = os.getenv("LIVEKIT_URL") or os.getenv("LK_URL")
    api_key = os.getenv("LIVEKIT_API_KEY") or os.getenv("LK_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET") or os.getenv("LK_API_SECRET")

    if not all([livekit_url, api_key, api_secret]):
        print("❌ Missing required environment variables")
        sys.exit(1)

    if not agent_name:
        agent_name = os.getenv("AGENT_NAME", "sage-assistant")

    try:
        print(f"🚀 Dispatching agent '{agent_name}' to room '{room_name}'...")

        # Use LiveKit SDK to create dispatch
        async def create_dispatch():
            lkapi = api.LiveKitAPI(
                url=livekit_url, api_key=api_key, api_secret=api_secret
            )

            request = api.CreateAgentDispatchRequest(
                agent_name=agent_name, room=room_name
            )

            dispatch = await lkapi.agent_dispatch.create_dispatch(request)
            return dispatch

        dispatch = asyncio.run(create_dispatch())

        print("✅ Agent dispatched successfully!")
        print(f"   Dispatch ID: {dispatch.id}")
        print(f"   Room: {room_name}")
        print(f"   Agent: {agent_name}")
        return True

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Install: pip install PyJWT httpx")
        return False
    except Exception as e:
        print(f"❌ Failed to dispatch agent: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dispatch_agent.py <room_name> [agent_name]")
        print("\nExample:")
        print("  python dispatch_agent.py test-room")
        print("  python dispatch_agent.py test-room sage-assistant")
        sys.exit(1)

    room_name = sys.argv[1]
    agent_name = sys.argv[2] if len(sys.argv) > 2 else None

    success = dispatch_agent(room_name, agent_name)
    sys.exit(0 if success else 1)
