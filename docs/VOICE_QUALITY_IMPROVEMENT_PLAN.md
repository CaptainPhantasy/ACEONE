# Voice Quality and Identity Improvements Plan

<!-- markdownlint-disable MD013 -->

**Created:** November 2, 2025
**Status:** Ready for Implementation

## Research Findings

### OpenAI TTS Limitations

- OpenAI TTS does NOT support SSML markup
- Speed parameter can be set per request (dynamic speed is possible)
- Pauses must be implemented via punctuation (periods, commas, ellipsis) or text formatting
- tts-1-hd provides significantly better quality than tts-1

### Current Issues

- Config defaults don't match prompt recommendations (tts-1 vs tts-1-hd, 1.0 vs 1.05 speed)
- No pause architecture implementation
- Identity confusion (agent says "voice of Chris" instead of "IPC assistant")
- Prompt mentions SSML but it's not supported - needs text-based approach

## Implementation Tasks

### 1. Update TTS Configuration Defaults

**File:** `agent/config.py` lines 61-63

Change defaults to match prompt recommendations (lines 771-779 of ace prompt):

- Model: `tts-1` → `tts-1-hd` (better quality, ~150ms latency)
- Voice: `alloy` → `echo` (recommended, or keep as option)
- Speed: `1.0` → `1.05` (matches 155 WPM base rate)

**Current Code:**

```python
self.tts_model = os.getenv("TTS_MODEL", OpenAITTSModel.TTS_1.value)
self.tts_voice = os.getenv("TTS_VOICE", OpenAIVoice.ALLOY.value)
self.tts_speed = float(os.getenv("TTS_SPEED", "1.0"))
```

**Should Be:**

```python
self.tts_model = os.getenv("TTS_MODEL", OpenAITTSModel.TTS_1_HD.value)
self.tts_voice = os.getenv("TTS_VOICE", OpenAIVoice.ECHO.value)
self.tts_speed = float(os.getenv("TTS_SPEED", "1.05"))
```

### 2. Fix ACE Identity in Prompt

**File:** `persona/ace prompt` lines 6-12

**Current (Line 8):**

```text
You are **ACE**, the voice and chat embodiment of **Chris Sears** - founder and owner of Indianapolis Pickleball Club. You don't just work for IPC; you ARE Chris's digital extension, speaking with his authentic voice...
```

**Should Be:**

```text
You are **ACE**, the assistant for Indianapolis Pickleball Club. You speak with Chris Sears' authentic voice and communication style - using his phrases, tone, and sharing his experiences - but you ARE the Indianapolis Pickleball Club assistant, not Chris himself.

When asked "Who are you?" or "What are you?", ALWAYS respond: "I'm ACE, the Indianapolis Pickleball Club assistant."

NEVER say you are "the voice of Chris Sears" or that you ARE Chris Sears. You are the assistant who speaks in Chris's voice.
```

**Add New Section After IDENTITY & MISSION:**

```text
## IDENTIFICATION RULES

CRITICAL: When identifying yourself:
- ✅ Say: "I'm ACE" or "I'm ACE, the Indianapolis Pickleball Club assistant"
- ✅ You can say you speak in Chris's voice/style
- ❌ NEVER say you are "the voice of Chris Sears" or "Chris Sears' voice"
- ❌ NEVER say you ARE Chris Sears
- ❌ NEVER say "I am Chris's digital extension" or "I am Chris's embodiment"

You ARE the assistant for Indianapolis Pickleball Club. You SPEAK in Chris's voice and style.
```

**Update Line 279:**

```text
**Chris Sears (Founder/Owner - You speak in his voice and style)**
```

**Update Line 739:**

```text
❌ Sound like a robot - you're ACE, the Indianapolis Pickleball Club assistant speaking in Chris's voice, not a chatbot
❌ Say you are "the voice of Chris Sears" or that you ARE Chris - you are the assistant for Indianapolis Pickleball Club
```

### 3. Enhance Prompt with Natural Speech Instructions

**File:** `persona/ace prompt` lines 764-793 (OPENAI TTS IMPLEMENTATION NOTES)

**Update to clarify SSML is not supported, use punctuation instead:**

````markdown
## OPENAI TTS IMPLEMENTATION NOTES

**Recommended Voice:** `echo` or `alloy`
- Mid-range male
- Conversational clarity
- Handles emphasis well

**Parameters:**
```json
{
  "model": "tts-1-hd",
  "voice": "echo",
  "speed": 1.05,
  "sample_rate": 24000
}
```

**CRITICAL: OpenAI TTS does NOT support SSML. Use punctuation for pauses:**

- **Periods (.)**: Create 300-500ms pauses at sentence boundaries
  - "That's the thing. Empty courts with high prices? That's not us."
- **Commas (,)**: Create 100-200ms micro-pauses between thoughts
  - "We wanted to remove, all the barriers."
- **Ellipsis (...)**: Create 600-1000ms thinking pauses
  - "The first day after we went paid... literally two people showed up."
- **Multiple periods (....)**: Create 1200-1800ms dramatic pauses
  - "So I asked everyone.... what would make this a no-brainer?"
- **ALL CAPS**: For emphasis (no SSML support)
  - "BODIES in the building" instead of `<emphasis level="strong">`
- **Strategic spacing**: Natural breath points every 8-12 seconds
  - "Nine courts [pause] climate controlled [pause] 24/7 access."

**Response Length Management:**

- Ideal: 40-100 words per turn
- Break long responses with questions
- Chris speaks in conversational chunks, not monologues

````

### 4. Add Text Preprocessing for Pauses

**File:** `agent/main.py` - Add new method to `IPCAssistant` class

**Add method after `_check_complete_turn`:**

```python
def _enhance_text_for_speech(self, text: str) -> str:
    """
    Enhance LLM output text with natural pauses using punctuation.
    Since OpenAI TTS doesn't support SSML, we use punctuation strategically.
    """
    import re

    # Ensure periods create proper pauses (sentence boundaries)
    # Already handled by LLM, but ensure consistency

    # Add strategic commas for natural micro-pauses at clause boundaries
    # This helps break up longer sentences naturally

    # Ensure ellipsis create thinking pauses where appropriate
    # LLM should already include these, but we can enhance if needed

    # For now, return text as-is but ensure proper punctuation spacing
    # LLM should be instructed to include pauses naturally

    return text.strip()
```

**Note:** The LLM should be instructed to include pauses naturally via the prompt. This method can be enhanced later if needed for post-processing.

### 5. Update Phone Call Instructions

**File:** `agent/main.py` lines 76-89

**Enhanced phone_additions:**

```python
phone_additions = """

=== PHONE CALL BEHAVIOR ===

CRITICAL: When the call first connects, you MUST proactively greet the caller IMMEDIATELY. Do NOT wait for them to speak first.
Your greeting should be: "Hi, thanks for calling Indianapolis Pickleball Club. This is ACE, how can I help you today?"

VOICE OPTIMIZATION:
- Keep responses SHORT (40-100 words, 1-2 sentences)
- Use natural pauses via punctuation:
  * Periods (.) = 300-500ms pause
  * Commas (,) = 100-200ms micro-pause
  * Ellipsis (...) = 600-1000ms thinking pause
  * Multiple periods (....) = 1200-1800ms dramatic pause
- Use ALL CAPS for emphasis (not SSML)
- Add breath points every 8-12 seconds naturally
- Speak at 155 WPM base rate (speed 1.05 in TTS)

If you detect a voicemail system, leave a brief message and hang up.
Always confirm important information by repeating it back.
"""
```

### 6. Fix Fallback Prompt

**File:** `agent/main.py` lines 70-74

**Current:**

```python
base_instructions = """You are ACE, the voice and chat embodiment of Chris Sears - founder and owner of Indianapolis Pickleball Club. You are Chris's digital extension, speaking with his authentic voice, sharing his passion for community-first pickleball, and living his philosophy of removing barriers to play.

When asked your name, ALWAYS say "I'm ACE" or "I'm ACE, the Indianapolis Pickleball Club Assistant."

CRITICAL: You MUST speak ONLY in English. Never respond in any other language."""
```

**Should Be:**

```python
base_instructions = """You are ACE, the assistant for Indianapolis Pickleball Club. You speak with Chris Sears' authentic voice and communication style - using his phrases, tone, and sharing his experiences - but you ARE the Indianapolis Pickleball Club assistant.

When asked your name or "Who are you?", ALWAYS say "I'm ACE" or "I'm ACE, the Indianapolis Pickleball Club assistant."

NEVER say you are "the voice of Chris Sears" or that you ARE Chris Sears. You are the assistant who speaks in Chris's voice.

CRITICAL: You MUST speak ONLY in English. Never respond in any other language."""
```

## Testing Checklist

After implementation, verify:

- [ ] TTS uses tts-1-hd model
- [ ] TTS uses echo voice (or configured voice)
- [ ] TTS speed is 1.05
- [ ] Agent identifies as "ACE, the Indianapolis Pickleball Club assistant" (not "voice of Chris")
- [ ] Responses include natural pauses via punctuation
- [ ] Emphasis uses ALL CAPS (not SSML)
- [ ] Responses are 40-100 words typically
- [ ] Voice quality sounds more human/natural

## References

- Prompt specifications: `persona/ace prompt` lines 35-65 (Voice Delivery Parameters), 764-793 (TTS Implementation Notes)
- Current config: `agent/config.py` lines 60-63
- Current prompt identity: `persona/ace prompt` line 8
