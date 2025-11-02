#!/usr/bin/env python3
"""
Agent Orchestrator - Automatically manages agent lifecycle and dispatch
Monitors agent status, restarts if needed, and dispatches to rooms
"""

import sys
import os
import time
import subprocess
import signal
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path, override=True)

try:
    from livekit import api
except ImportError:
    print("❌ LiveKit API not installed")
    sys.exit(1)

class AgentOrchestrator:
    def __init__(self):
        self.agent_process = None
        self.agent_log_path = "/tmp/agent.log"
        self.monitoring = False
        self.room_name = "test-room"
        self.agent_name = os.getenv("AGENT_NAME", "sage-assistant")
        self.last_dispatch_time = {}
        
    def is_agent_running(self):
        """Check if agent process is running"""
        result = subprocess.run(
            ["pgrep", "-f", "python.*main.py.*dev"],
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) > 0
    
    def start_agent(self):
        """Start the agent process"""
        if self.is_agent_running():
            print("✅ Agent already running")
            return True
            
        print("🚀 Starting agent...")
        agent_dir = Path(__file__).parent.parent / "agent"
        
        try:
            # Start agent in background
            self.agent_process = subprocess.Popen(
                ["python", "main.py", "dev"],
                cwd=str(agent_dir),
                stdout=open(self.agent_log_path, "a"),
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONPATH": str(agent_dir)},
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for registration
            print("⏳ Waiting for agent to register...")
            for _ in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if "registered worker" in self.read_tail_log(20):
                    print("✅ Agent registered successfully")
                    return True
            
            print("⚠️ Agent started but may not have registered yet")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start agent: {e}")
            return False
    
    def stop_agent(self):
        """Stop the agent process"""
        if self.agent_process:
            try:
                os.killpg(os.getpgid(self.agent_process.pid), signal.SIGTERM)
            except:
                pass
            self.agent_process = None
        
        # Kill any remaining agent processes
        subprocess.run(["pkill", "-f", "python main.py dev"], 
                      capture_output=True)
        print("🛑 Agent stopped")
    
    def read_tail_log(self, lines=50):
        """Read last N lines from agent log"""
        try:
            with open(self.agent_log_path, "r") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except:
            return ""
    
    def agent_in_room(self, room_name):
        """Check if agent has joined a specific room"""
        log_content = self.read_tail_log(100)
        return f"Agent starting for room: {room_name}" in log_content or \
               f"room: {room_name}" in log_content.lower()
    
    async def dispatch_to_room(self, room_name):
        """Dispatch agent to a room"""
        # Don't dispatch too frequently to same room
        now = time.time()
        if room_name in self.last_dispatch_time:
            if now - self.last_dispatch_time[room_name] < 5:
                return False  # Too soon
        
        self.last_dispatch_time[room_name] = now
        
        livekit_url = os.getenv("LIVEKIT_URL") or os.getenv("LK_URL")
        api_key = os.getenv("LIVEKIT_API_KEY") or os.getenv("LK_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET") or os.getenv("LK_API_SECRET")
        
        if not all([livekit_url, api_key, api_secret]):
            print("❌ Missing LiveKit credentials")
            return False
        
        try:
            print(f"🚀 Dispatching agent to room: {room_name}")
            
            lkapi = api.LiveKitAPI(
                url=livekit_url,
                api_key=api_key,
                api_secret=api_secret
            )
            
            request = api.CreateAgentDispatchRequest(
                agent_name=self.agent_name,
                room=room_name
            )
            
            dispatch = await lkapi.agent_dispatch.create_dispatch(request)
            print(f"✅ Dispatch successful (ID: {dispatch.id})")
            return True
            
        except Exception as e:
            print(f"❌ Dispatch failed: {e}")
            return False
    
    def monitor_agent_health(self):
        """Check agent health and restart if needed"""
        if not self.is_agent_running():
            print("⚠️ Agent not running, restarting...")
            return self.start_agent()
        
        # Check if agent is stuck/errored
        log_content = self.read_tail_log(50)
        if "Error" in log_content or "Traceback" in log_content:
            print("⚠️ Agent error detected in logs")
            # Don't auto-restart on first error, might be transient
        
        return True
    
    async def monitor_and_dispatch(self, room_name, check_interval=5):
        """Main monitoring loop"""
        self.monitoring = True
        print(f"\n🎛️ Orchestrator started - Monitoring room: {room_name}", flush=True)
        print("=" * 60, flush=True)
        
        while self.monitoring:
            try:
                # Check agent health
                if not self.monitor_agent_health():
                    await asyncio.sleep(5)
                    continue
                
                # Check if agent is in room
                if not self.agent_in_room(room_name):
                    print(f"📡 Agent not in room '{room_name}', dispatching...")
                    await self.dispatch_to_room(room_name)
                    await asyncio.sleep(3)  # Wait for agent to join
                else:
                    # Agent is in room - check for activity
                    log_content = self.read_tail_log(20)
                    if "error" in log_content.lower():
                        print("⚠️ Error detected in agent logs")
                
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Orchestrator stopping...")
                self.monitoring = False
                break
            except Exception as e:
                print(f"❌ Orchestrator error: {e}")
                await asyncio.sleep(check_interval)
    
    def get_status(self):
        """Get current status"""
        status = {
            "agent_running": self.is_agent_running(),
            "agent_registered": "registered worker" in self.read_tail_log(30),
            "agent_in_room": self.agent_in_room(self.room_name),
            "last_log": self.read_tail_log(5).strip().split("\n")[-1] if self.read_tail_log(5) else "No logs"
        }
        return status

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Orchestrator")
    parser.add_argument("--room", default="test-room", help="Room name to monitor")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--dispatch-only", action="store_true", help="Dispatch once and exit")
    args = parser.parse_args()
    
    orchestrator = AgentOrchestrator()
    orchestrator.room_name = args.room
    
    if args.status:
        status = orchestrator.get_status()
        print("\n📊 Agent Status:")
        print("=" * 60)
        for key, value in status.items():
            print(f"  {key}: {value}")
        return
    
    if args.dispatch_only:
        await orchestrator.dispatch_to_room(args.room)
        await asyncio.sleep(2)
        return
    
    # Ensure agent is running
    if not orchestrator.start_agent():
        print("❌ Failed to start agent")
        sys.exit(1)
    
    # Start monitoring
    try:
        await orchestrator.monitor_and_dispatch(args.room)
    except KeyboardInterrupt:
        print("\n🛑 Stopping orchestrator...")
        orchestrator.stop_agent()

if __name__ == "__main__":
    asyncio.run(main())

