# ACE - Indianapolis Pickleball Club Voice Agent

Voice agent for answering phone calls to Indianapolis Pickleball Club. Embodies Chris Sears' authentic voice and uses RAG for accurate knowledge retrieval.

**⚠️ CURRENT STATUS:** See `STATUS.md` for latest issues and fixes needed.

## ✅ Working Setup

- **Agent Framework**: LiveKit Agents (Python)
- **STT**: OpenAI Whisper
- **LLM**: OpenAI GPT-4 Turbo
- **TTS**: OpenAI TTS
- **VAD**: Silero VAD
- **Testing**: LiveKit Playground (auto-dispatch)

## 🚀 Quick Start

### 1. Environment Setup

```bash
cd agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env.local` in project root:

```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
OPENAI_API_KEY=your_openai_key
AGENT_NAME=sage-assistant
```

### 3. Run Agent

```bash
cd agent
source venv/bin/activate
python main.py dev
```

Agent will register and wait for connections.

### 4. Test with LiveKit Playground

1. Visit: https://agents-playground.livekit.io
2. Enter your LiveKit credentials (URL, API Key, API Secret)
3. Set Agent Name: `sage-assistant`
4. Click "Connect"
5. Agent auto-dispatches when you join
6. Start speaking - agent responds with voice

## 📁 Project Structure

```
agent/
  main.py          # Entry point - AgentSession setup
  config.py        # Configuration from .env
  tools/           # Function tools (weather, calendar, database)
    weather.py
    calendar.py
    database.py
    voicemail.py
```

## 🔧 Key Implementation Details

### Agent Pattern

```python
# Agent defines behavior (instructions + tools)
voice_agent = Agent(
    instructions=system_instructions,
    tools=tools_list,
)

# AgentSession handles STT/LLM/TTS/VAD
session = AgentSession(
    stt=openai.STT(...),
    llm=openai.LLM(...),
    tts=openai.TTS(...),
    vad=silero.VAD.load(...),
)

# Start session with agent and room
await session.start(voice_agent, room=ctx.room)
```

### Worker Registration

Agent registers with LiveKit Cloud using `agent_name` from config:
- Set in `.env.local` as `AGENT_NAME=sage-assistant`
- Must match the name used in Playground or dispatch

### Tool Schema Note

Tools use `@llm.function_tool` decorator. For complex types, use JSON strings:
- `filters: str = "{}"` instead of `filters: Optional[Dict] = None`
- Parse JSON inside the function

## 🐛 Troubleshooting

**Agent not responding:**
- Check logs: `tail -f /tmp/agent.log`
- Verify worker registered: Look for "registered worker" in logs
- Ensure agent name matches in Playground

**Schema errors:**
- Tool parameters must use simple types or JSON strings
- Avoid `Optional[Dict]` - use `str` with default `"{}"`

**Connection issues:**
- Verify `.env.local` credentials
- Check LiveKit Cloud dashboard for worker status

## 📝 Notes

- Uses LiveKit Playground for testing (recommended - auto-dispatches)
- Custom test GUI available in `test_gui/` (requires manual dispatch)
- Agent runs in dev mode: `python main.py dev`
- Production mode requires different setup (not covered here)
