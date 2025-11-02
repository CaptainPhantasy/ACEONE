# Google Chirp API Refactoring Plan

## Overview

This document outlines the plan to refactor the voice agent from OpenAI TTS/STT to Google Chirp API for both Text-to-Speech (TTS) and Speech-to-Text (STT) functionality.

**Reference**: [LiveKit Models Documentation](https://docs.livekit.io/agents/models/) | [LiveKit Inference Blog](https://blog.livekit.io/introducing-livekit-inference/)

## Key Insights from LiveKit Architecture

### Easy Model Switching
LiveKit's `AgentSession` accepts models in two ways:
1. **Plugin Instances**: Direct instantiation (e.g., `google.STT(model="chirp")`)
2. **String Descriptors**: Via LiveKit Inference (e.g., `stt="google/chirp"`)

Both approaches use the same consistent API, making provider switching trivial - just change the parameter passed to `AgentSession`.

### Current Implementation
```python
# Current: OpenAI plugins
session = AgentSession(
    stt=openai.STT(model=config.stt_model, language="en"),
    tts=openai.TTS(model=config.tts_model, voice=config.tts_voice, speed=config.tts_speed)
)
```

### Target Implementation
```python
# Target: Google Chirp plugins
session = AgentSession(
    stt=google.STT(model="chirp", language="en"),
    tts=google.TTS(model="chirp-3", voice=config.tts_voice)
)
```

## Refactoring Steps

### Phase 1: Dependencies & Setup

#### 1.1 Install Google Plugin
```bash
# Add to requirements.txt
livekit-plugins-google>=1.2.0

# Or install via pip
pip install "livekit-agents[google]~=1.2"
```

**References**: 
- [LiveKit Models Docs](https://docs.livekit.io/agents/models/) - Plugin installation section
- LiveKit Google plugin supports Chirp model for STT

#### 1.2 Google Cloud Authentication
Set up Google Cloud credentials:

**Option A: Service Account Key File**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**Option B: Environment Variables**
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"  # Optional, defaults to us-central1
```

**Required**:
- Google Cloud project with Text-to-Speech and Speech-to-Text APIs enabled
- Service account with appropriate permissions
- API quota: Chirp TTS has 100 requests/minute limit (as of April 2025)

### Phase 2: Configuration Updates

#### 2.1 Update `config.py`

**Add Google Configuration Section:**
```python
# Google Cloud Configuration
self.google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
self.google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
self.google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
```

**Add Google Voice Enums:**
```python
class GoogleVoice(Enum):
    """Available Google Chirp TTS voices"""
    # Standard voices (add based on Google Cloud TTS available voices)
    NEUTRAL = "neutral"      # Neutral voice
    # Add more as needed based on Google's voice list

class GoogleSTTModel(Enum):
    """Available Google STT models"""
    CHIRP = "chirp"          # Chirp model for STT
    CHIRP_MULTILINGUAL = "chirp-multilingual"

class GoogleTTSModel(Enum):
    """Available Google TTS models"""
    CHIRP_3 = "chirp-3"      # Chirp 3 for TTS
    NEURAL_2 = "neural2"     # Alternative if Chirp 3 not available
```

**Update TTS/STT Settings:**
```python
# STT Settings - Add Google option
self.stt_provider = os.getenv("STT_PROVIDER", "openai")  # "openai" or "google"
self.google_stt_model = os.getenv("GOOGLE_STT_MODEL", GoogleSTTModel.CHIRP.value)
self.google_stt_language = os.getenv("GOOGLE_STT_LANGUAGE", "en-US")

# TTS Settings - Add Google option
self.tts_provider = os.getenv("TTS_PROVIDER", "openai")  # "openai" or "google"
self.google_tts_model = os.getenv("GOOGLE_TTS_MODEL", GoogleTTSModel.CHIRP_3.value)
self.google_tts_voice = os.getenv("GOOGLE_TTS_VOICE", "en-US-Neural2-D")  # Example voice
self.google_tts_speaking_rate = float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0"))
```

**Update Validation:**
```python
def validate(self) -> bool:
    """Validate required configuration"""
    if self.tts_provider == "google" or self.stt_provider == "google":
        if not self.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT required when using Google provider")
        # Check credentials file if provided
        if self.google_application_credentials:
            if not os.path.exists(self.google_application_credentials):
                raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {self.google_application_credentials}")
    
    # ... existing validation
```

### Phase 3: Update `main.py`

#### 3.1 Import Google Plugin
```python
from livekit.plugins import openai, silero, google  # Add google
```

#### 3.2 Create Model Factory Functions
```python
def create_stt_provider(config):
    """Create STT provider based on configuration"""
    if config.stt_provider == "google":
        return google.STT(
            model=config.google_stt_model,
            language=config.google_stt_language,
            # Additional Google-specific options
            spoken_punctuation=True,  # Enable punctuation in transcripts
        )
    else:  # Default to OpenAI
        return openai.STT(
            model=config.stt_model,
            language="en"
        )

def create_tts_provider(config):
    """Create TTS provider based on configuration"""
    if config.tts_provider == "google":
        return google.TTS(
            model=config.google_tts_model,
            voice=config.google_tts_voice,
            speaking_rate=config.google_tts_speaking_rate,
            # Additional Google-specific options
        )
    else:  # Default to OpenAI
        return openai.TTS(
            model=config.tts_model,
            voice=config.tts_voice,
            speed=config.tts_speed
        )
```

#### 3.3 Update AgentSession Creation
```python
# In entrypoint() function, replace lines 507-520:

session = AgentSession(
    stt=create_stt_provider(config),
    llm=openai.LLM(
        model=config.llm_model,
        temperature=config.llm_temperature,
    ),
    tts=create_tts_provider(config),
    vad=optimized_vad,
    preemptive_generation=True,
)

# Log which providers are being used
logger.info(f"Agent session initialized with STT: {config.stt_provider}, TTS: {config.tts_provider}")
```

### Phase 4: Environment Configuration

#### 4.1 Update `.env.local` Template
```bash
# STT Provider: "openai" or "google"
STT_PROVIDER=google

# Google STT Configuration
GOOGLE_STT_MODEL=chirp
GOOGLE_STT_LANGUAGE=en-US

# TTS Provider: "openai" or "google"
TTS_PROVIDER=google

# Google TTS Configuration
GOOGLE_TTS_MODEL=chirp-3
GOOGLE_TTS_VOICE=en-US-Neural2-D  # Adjust based on available voices
GOOGLE_TTS_SPEAKING_RATE=1.0

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Phase 5: Testing & Validation

#### 5.1 Test Script
Create `test_chirp_integration.py`:
```python
"""Test Google Chirp integration"""
import asyncio
from livekit.plugins import google
from agent.config import config

async def test_chirp():
    """Test Chirp STT and TTS"""
    # Test STT
    stt = google.STT(model="chirp", language="en-US")
    print("✅ Chirp STT initialized")
    
    # Test TTS
    tts = google.TTS(model="chirp-3", voice="en-US-Neural2-D")
    print("✅ Chirp TTS initialized")
    
    print("\n🎉 Google Chirp integration ready!")

if __name__ == "__main__":
    config.load_from_env()
    asyncio.run(test_chirp())
```

#### 5.2 Verification Checklist
- [ ] Google Cloud project configured
- [ ] APIs enabled (Speech-to-Text, Text-to-Speech)
- [ ] Service account credentials set
- [ ] Plugin installed and importable
- [ ] STT provider switches correctly
- [ ] TTS provider switches correctly
- [ ] Voice quality acceptable
- [ ] Latency acceptable for phone calls
- [ ] Rate limits understood (100 req/min for Chirp TTS)

### Phase 6: Documentation Updates

#### 6.1 Update README.md
Add section on Google Chirp configuration and usage.

#### 6.2 Create Migration Guide
Document the process of switching from OpenAI to Google Chirp.

#### 6.3 Update Voice Selection Guide
Create equivalent guide for Google voices.

## Important Considerations

### Latency
- Google Chirp TTS may have different latency characteristics than OpenAI TTS
- Test thoroughly for phone call scenarios (target: <500ms total latency)
- Monitor metrics during transition

### Rate Limits
- Chirp TTS: 100 requests/minute per project (as of April 2025)
- Plan for capacity if expecting high volume
- Consider fallback to OpenAI if limits reached

### Voice Quality
- Google voices may sound different from OpenAI voices
- Test voice selection for ACE persona match
- May need to adjust speaking_rate for optimal sound

### Cost
- Google Cloud pricing differs from OpenAI
- Monitor usage and costs during transition
- Compare per-character/per-minute costs

### Feature Parity
- Verify all features work (interruptions, turn detection, etc.)
- Google TTS may have different SSML support
- Check audio format compatibility

## Rollout Strategy

### Option A: Gradual Migration
1. Deploy with both providers available
2. Use feature flag to switch per-call
3. A/B test quality and latency
4. Gradually migrate traffic

### Option B: Full Cutover
1. Test thoroughly in staging
2. Deploy to production with Google Chirp
3. Monitor closely for issues
4. Keep OpenAI as fallback option

## Rollback Plan

If issues arise:
1. Set `TTS_PROVIDER=openai` and `STT_PROVIDER=openai` in environment
2. Restart agent
3. Agent will automatically use OpenAI providers
4. No code changes needed - all handled via configuration

## References

- [LiveKit Models Documentation](https://docs.livekit.io/agents/models/)
- [LiveKit Inference Blog Post](https://blog.livekit.io/introducing-livekit-inference/)
- [Google Cloud Text-to-Speech API](https://cloud.google.com/text-to-speech/docs)
- [Google Cloud Speech-to-Text API](https://cloud.google.com/speech-to-text/docs)
- [Chirp Model Documentation](https://cloud.google.com/text-to-speech/docs/chirp3-instant-custom-voice)

