#!/usr/bin/env python3
"""
Generate LiveKit access token for testing
Usage: python generate_token.py [room_name] [identity] [name]
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    print(f"❌ Could not find .env.local at {env_path}")
    sys.exit(1)

try:
    from livekit import api
except ImportError:
    print("❌ LiveKit API not installed. Run: pip install livekit-api")
    sys.exit(1)


def generate_token(room_name="test-room", identity="test-user", name="Test User"):
    """Generate a LiveKit access token"""

    livekit_url = os.getenv("LIVEKIT_URL") or os.getenv("LK_URL")
    api_key = os.getenv("LIVEKIT_API_KEY") or os.getenv("LK_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET") or os.getenv("LK_API_SECRET")

    if not all([livekit_url, api_key, api_secret]):
        print("❌ Missing required environment variables:")
        print("   - LIVEKIT_URL or LK_URL")
        print("   - LIVEKIT_API_KEY or LK_API_KEY")
        print("   - LIVEKIT_API_SECRET or LK_API_SECRET")
        sys.exit(1)

    # Create token
    token = (
        api.AccessToken(api_key=api_key, api_secret=api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )

    return token, livekit_url


if __name__ == "__main__":
    # Get arguments
    room_name = sys.argv[1] if len(sys.argv) > 1 else "test-room"
    identity = sys.argv[2] if len(sys.argv) > 2 else "test-user"
    name = sys.argv[3] if len(sys.argv) > 3 else "Test User"

    try:
        token, url = generate_token(room_name, identity, name)

        print("\n" + "=" * 70)
        print("🎟️  LiveKit Access Token Generated")
        print("=" * 70)
        print("\n📡 LiveKit URL:")
        print(f"   {url}")
        print("\n🏠 Room Name:")
        print(f"   {room_name}")
        print("\n🎫 Access Token:")
        print(f"   {token}")
        print("\n👤 Identity:")
        print(f"   {identity} ({name})")
        print("\n" + "=" * 70)
        print("\n📋 Copy the token above and paste it into the test GUI")
        print("   Or use it with the LiveKit Playground\n")

        # Try to copy to clipboard (optional)
        try:
            import subprocess

            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=token, text=True, check=True)
                print("✅ Token copied to clipboard!")
            elif sys.platform == "linux":
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=token,
                    text=True,
                    check=True,
                )
                print("✅ Token copied to clipboard!")
            elif sys.platform == "win32":
                subprocess.run(["clip"], input=token, text=True, check=True)
                print("✅ Token copied to clipboard!")
        except (OSError, subprocess.SubprocessError):
            pass  # Clipboard copy is optional

    except Exception as e:
        print(f"❌ Error generating token: {e}")
        sys.exit(1)
