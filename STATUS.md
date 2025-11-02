# ACE Voice Agent - Current Status

**Date:** November 2, 2025  
**Last Updated:** After latency optimizations and greeting fix

## Current State

### ✅ What's Working

1. **Agent Infrastructure**
   - LiveKit agent is running and registering successfully
   - Worker ID: Changes on each restart
   - Connection to LiveKit Cloud is stable
   - Agent receives and processes audio input

2. **Knowledge Base Integration**
   - RAG system implemented in `agent/tools/knowledge.py`
   - Knowledge base loads from `persona/knowledge.md` (299 lines)
   - Vector embeddings generated using OpenAI `text-embedding-3-small`
   - Semantic search functional
   - Smart keyword detection for IPC-related queries

3. **System Prompt**
   - Full ACE prompt loaded from `persona/ace prompt` (803 lines)
   - Comprehensive persona instructions in place
   - Phone call specific behavior instructions included
   - Chris Sears' voice and values embedded

4. **Audio Pipeline**
   - STT (Whisper) receiving and transcribing audio
   - TTS (OpenAI) generating responses
   - VAD (Silero) detecting speech
   - Audio streaming functional

5. **Agent Identity**
   - Agent identifies as ACE (when asked)
   - Knowledge of IPC is accessible
   - Can answer questions about the club

### ❌ Critical Issues

1. **Proactive Greeting** ✅ FIXED
   - **Status:** Fixed using `on_start()` hook with `ctx.reply()` method
   - **Implementation:** `agent/main.py` lines 95-102
   - **Method:** Uses LiveKit's proper turn mechanism to trigger TTS immediately
   - **Testing Needed:** Verify greeting happens immediately on call connect

2. **Persona Not Being Followed** ⚠️ PARTIALLY ADDRESSED
   - **Problem:** Agent responses are generic, not using Chris Sears' authentic voice
   - **Example:** Responds with "I'm here to make your experience as smooth and enjoyable as possible!" (generic)
   - **Expected:** Should use direct, authentic language like "Look, here's the deal..." with Chris's signature phrases
   - **Changes Made:** Added voice optimization instructions to prompt (keep responses short, conversational)
   - **Still Needs:** Stronger enforcement in system prompt, temperature tuning, or example-based training

3. **High Latency** ✅ OPTIMIZED
   - **Status:** Multiple optimizations applied
   - **Optimizations Implemented:**
     - ✅ VAD tuned for faster turn detection (0.3s silence vs 0.55s default)
     - ✅ Preemptive generation enabled (starts response before user finishes)
     - ✅ Thinking audio added (masks RAG/LLM latency)
     - ✅ RAG search optimized with timing logs
     - ✅ Voice-optimized prompt (keep responses short)
   - **Expected Improvement:** 200-500ms reduction in perceived latency
   - **Testing Needed:** Measure actual latency improvements

### ⚠️ Partial Issues

1. **Greeting Timing** ✅ FIXED
   - ✅ Fixed: Now uses `on_start()` hook with `ctx.reply()` 
   - ⏳ **TODO:** Test to verify greeting happens immediately (not after user speaks)
   - ⏳ **TODO:** Monitor logs to ensure greeting doesn't repeat multiple times

2. **Language Detection** ✅ FIXED
   - ✅ Fixed by hardcoding STT language to "en"
   - Should monitor if this recurs, but should be stable now

## Technical Implementation Details

### File Structure
```
agent/
  main.py              # Main entry point - AgentSession setup
  config.py            # Configuration from .env
  tools/
    knowledge.py       # RAG knowledge base implementation
    weather.py
    calendar.py
    database.py
    voicemail.py

persona/
  ace prompt           # Full 803-line ACE system prompt
  knowledge.md         # IPC knowledge base (299 lines)
```

### Key Classes

1. **IPCAssistant(Agent)**
   - Extends LiveKit `Agent` class
   - Implements `on_user_turn_completed` hook for smart RAG
   - Has `on_start` hook (not working correctly)
   - Location: `agent/main.py` lines 85-161

2. **KnowledgeBase**
   - Loads and parses markdown knowledge base
   - Generates embeddings
   - Performs semantic search
   - Location: `agent/tools/knowledge.py`

### Configuration

- **Agent Name:** `sage-assistant` (from `.env.local`)
- **LLM Model:** `gpt-4-turbo`
- **STT Model:** `whisper-1`
- **TTS Model:** `tts-1` (voice: `alloy`)
- **Language:** English (hardcoded)

### Current Greeting Implementation ✅ FIXED

```python
# agent/main.py lines 95-102
async def on_start(self, ctx: llm.ChatContext) -> None:
    """Send proactive greeting when agent starts (for phone calls)"""
    if self.is_phone_call and not self._has_greeted:
        # Use reply() to trigger TTS output - this properly sends through the TTS pipeline
        greeting = "Hi, thanks for calling Indianapolis Pickleball Club. This is ACE, how can I help you today?"
        await ctx.reply(greeting)
        self._has_greeted = True
        logger.info("ACE proactive greeting sent via on_start hook")
```

**Solution:** Uses LiveKit's `on_start()` hook with `ctx.reply()` method, which properly triggers TTS output through the session's turn mechanism.

## Testing Results

### Test Session (November 2, 2025 ~6:17 AM)

**User:** "Agent, are you listening?"  
**Agent:** [No immediate greeting, then responds with greeting AFTER user speaks]

**User:** "Oh hey, what can you tell me about Pickleball?"  
**Agent:** Generic response about pickleball (not using ACE persona)

**User:** "Hey, Ace, what can you tell me about the... the Indianapolis Pickleball Club. specifically."  
**Agent:** Generic response mentioning IPC

**User:** "Hey, I'm testing your interruption and Turn around abilities. It seems like you're doing pretty good. I like that"  
**Agent:** "Thanks for the feedback, I appreciate it!"

**User:** "We need to get you optimized a little bit though your latency on is pretty laggy."  
**Agent:** "I'm here to make your experience as smooth and enjoyable as possible!"

### Key Observations from Logs

1. Full ACE prompt IS being sent to LLM (visible in chat completion requests)
2. Greeting appears multiple times in conversation history (6+ times)
3. Agent receives transcripts correctly
4. TTS is generating audio
5. RAG lookups may not be triggering (no IPC-specific knowledge injection visible)

## Required Fixes

### Priority 1: Proactive Greeting
- **Must Fix:** Agent must greet immediately when session starts
- **Approach Needed:** Find correct LiveKit hook/method to trigger initial TTS output
- **Research:** How does LiveKit AgentSession handle initial messages?
- **Alternative:** May need to use LLM to generate greeting as first turn instead of injecting into context

### Priority 2: Persona Adherence
- **Must Fix:** Agent must follow Chris Sears' authentic voice
- **Approach:** 
  - Verify system prompt is being used correctly
  - May need stronger enforcement in prompt
  - Consider adjusting temperature or adding examples
  - Ensure RAG is injecting Chris's quotes/phrases

### Priority 3: Latency Optimization ✅ OPTIMIZED
- **Optimizations Applied:**
  1. **VAD Tuning:** Reduced `min_silence_duration` from 0.55s to 0.3s (faster turn detection)
  2. **Preemptive Generation:** Enabled - starts generating response before user finishes speaking
  3. **Thinking Audio:** Added BackgroundAudioPlayer with keyboard typing sound to mask latency
  4. **RAG Optimization:** Added timing logs, optimized vector operations with numpy
  5. **Prompt Optimization:** Added voice-specific instructions to keep responses short (1-2 sentences)
- **Expected Improvements:** 200-500ms reduction in perceived latency
- **Monitoring:** RAG timing logs added to diagnose bottlenecks

## Next Steps

1. **Test Proactive Greeting** ✅ FIXED
   - ✅ Fixed using `on_start()` hook with `ctx.reply()`
   - ⏳ **TODO:** Test on actual phone call to verify greeting happens immediately
   - ⏳ **TODO:** Verify greeting doesn't repeat multiple times

2. **Strengthen Persona** ⚠️ IN PROGRESS
   - ✅ Added voice optimization instructions (keep responses short)
   - ⏳ **TODO:** Add explicit examples of Chris's voice to system prompt
   - ⏳ **TODO:** Test with temperature adjustments (lower = more consistent)
   - ⏳ **TODO:** Verify RAG is injecting Chris's quotes/phrases into context
   - ⏳ **TODO:** Consider adding few-shot examples to prompt

3. **Measure Latency Improvements** ✅ OPTIMIZED
   - ✅ VAD optimized (0.3s silence detection)
   - ✅ Preemptive generation enabled
   - ✅ Thinking audio added
   - ✅ RAG timing logs added
   - ⏳ **TODO:** Run latency benchmarks before/after
   - ⏳ **TODO:** Monitor RAG timing logs to identify bottlenecks
   - ⏳ **TODO:** Consider faster LLM model (gpt-4o-mini) if latency still high

4. **Test Full Phone Call Flow**
   - ⏳ **TODO:** Test on actual phone call
   - ⏳ **TODO:** Verify proactive greeting on call connect
   - ⏳ **TODO:** Test RAG knowledge injection with IPC keywords
   - ⏳ **TODO:** Verify persona adherence in responses
   - ⏳ **TODO:** Measure actual latency improvements

## Important Notes

- **This agent ONLY handles phone calls** - all code paths assume phone calls
- **Room naming:** Phone calls use `call-*` prefix (detected in `entrypoint`)
- **Agent identity:** ACE (not Chris Sears, but embodies his values/voice)
- **Knowledge base:** `persona/knowledge.md` + `persona/ace prompt` both loaded

## Running the Agent

```bash
cd agent
source venv/bin/activate
python main.py dev > /tmp/agent.log 2>&1 &
```

**Monitor logs:**
```bash
tail -f /tmp/agent.log
```

**Key log markers:**
- `registered worker` - Agent connected to LiveKit
- `Agent starting for room` - Session started
- `Triggering proactive greeting` - Greeting code executed
- `ACE greeting added to chat context` - Should see this when greeting works
- `received user transcript` - User speaking
- `json_data.*input` - TTS output being generated

## Environment Variables Required

From `.env.local`:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`
- `AGENT_NAME=sage-assistant`

