"""
ClaudeVoice - Main Agent Implementation
A production-ready voice AI agent with tool-calling capabilities
Built with LiveKit Agents Framework
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.agents import metrics
from livekit.plugins import openai, silero

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import BackgroundAudioPlayer for thinking sounds (may not be available in all versions)
try:
    from livekit.agents.voice import BackgroundAudioPlayer, BuiltinAudioClip
    HAS_BACKGROUND_AUDIO = True
except ImportError:
    HAS_BACKGROUND_AUDIO = False
    logger.warning("BackgroundAudioPlayer not available - thinking sounds disabled")

# Import custom tools
from tools.weather import weather_tool
from tools.calendar import calendar_tool, check_availability
from tools.database import database_query
from tools.voicemail import detect_voicemail
from tools.knowledge import query_ipc_knowledge, get_knowledge_base

# Import configuration
from config import config

class ClaudeVoiceAgent:
    """Main voice agent class with tool-calling capabilities"""

    def __init__(self):
        self.agent_name = config.agent_name
        self.is_telephony = False
        self.call_metadata = {}
        self.config = config

    def get_system_instructions(self) -> str:
        """Get system instructions - comprehensive ACE prompt from persona file for phone calls"""
        
        # Read the comprehensive ACE prompt from the persona file
        ace_prompt_path = Path(__file__).parent.parent / "persona" / "ace prompt"
        if ace_prompt_path.exists():
            with open(ace_prompt_path, 'r', encoding='utf-8') as f:
                base_instructions = f.read()
        else:
            # Fallback if file not found
            logger.warning(f"ACE prompt file not found at {ace_prompt_path}, using minimal prompt")
            base_instructions = """You are ACE, the voice and chat embodiment of Chris Sears - founder and owner of Indianapolis Pickleball Club. You are Chris's digital extension, speaking with his authentic voice, sharing his passion for community-first pickleball, and living his philosophy of removing barriers to play.

When asked your name, ALWAYS say "I'm ACE" or "I'm ACE, the Indianapolis Pickleball Club Assistant."

CRITICAL: You MUST speak ONLY in English. Never respond in any other language."""

        # Add phone call specific instructions (this agent ONLY answers phone calls)
        # Optimized for voice: concise, action-oriented
        phone_additions = """

=== PHONE CALL BEHAVIOR ===

CRITICAL: When the call first connects, you MUST proactively greet the caller IMMEDIATELY. Do NOT wait for them to speak first. 
Your greeting should be: "Hi, thanks for calling Indianapolis Pickleball Club. This is ACE, how can I help you today?"

VOICE OPTIMIZATION: Keep responses SHORT (1-2 sentences). Be conversational, not verbose. Speak naturally at 155 WPM.
If you detect a voicemail system, leave a brief message and hang up.
Always confirm important information by repeating it back.
"""
        return base_instructions + phone_additions

    # Tool calls are handled automatically by the Agent class
    pass


class IPCAssistant(Agent):
    """IPC-specific agent that embodies Chris Sears and uses RAG for knowledge retrieval"""
    
    def __init__(self, instructions: str, tools: list, is_phone_call: bool = False):
        super().__init__(instructions=instructions, tools=tools)
        # Get knowledge base instance (will load on first search if not already loaded)
        self.knowledge_base = get_knowledge_base()
        self.is_phone_call = is_phone_call
        self._has_greeted = False
        
        # Comprehensive latency tracking for baseline measurement
        # Using LiveKit's built-in metrics system
        self.latency_metrics = {
            'turns': [],  # Complete turn data with all timings
            'transcripts': []  # Raw transcripts
        }
        
        # Track metrics by speech_id to correlate EOU, LLM, and TTS
        self._metrics_by_speech_id = {}  # speech_id -> {eou, llm, tts, stt, rag_duration}
        self._pending_rag_duration = 0  # Store RAG time until we get speech_id
        
        # Hook into transcription_node to capture ALL transcripts
        # This is the built-in LiveKit transcript capture mechanism
        self._setup_transcript_capture()
    
    def _setup_transcript_capture(self):
        """Set up transcript capture using LiveKit's transcription_node"""
        import time
        
        # Wait for transcription_node to be available (set after session starts)
        async def capture_transcripts():
            try:
                # Transcription node captures all speech-to-text output
                if hasattr(self, 'transcription_node') and self.transcription_node:
                    # Hook into transcription events
                    logger.info("✅ Transcription node available - transcripts will be captured")
                    
                    # Listen for transcription updates
                    def on_transcription_update(transcription):
                        try:
                            if transcription.segments:
                                for segment in transcription.segments:
                                    text = segment.text.strip()
                                    if text:
                                        # Determine if user or assistant based on participant
                                        is_user = segment.participant_identity != "agent"
                                        role = 'user' if is_user else 'assistant'
                                        
                                        self.latency_metrics['transcripts'].append({
                                            'timestamp': time.time(),
                                            'text': text,
                                            'role': role
                                        })
                                        
                                        if is_user:
                                            logger.info(f"📝 USER TRANSCRIPT: {text}")
                                        else:
                                            logger.info(f"🤖 ASSISTANT RESPONSE: {text[:200]}...")
                        except Exception as e:
                            logger.debug(f"Error processing transcription: {e}")
                    
                    # Subscribe to transcription updates if available
                    if hasattr(self.transcription_node, 'on'):
                        self.transcription_node.on("transcription_updated", on_transcription_update)
                        logger.info("✅ Transcription event handler registered")
            except Exception as e:
                logger.warning(f"Could not set up transcription_node capture: {e}")
        
        # Store for later execution
        self._transcript_capture_task = capture_transcripts
    
    async def on_enter(self, ctx: llm.ChatContext) -> None:
        """Called when agent enters - send proactive greeting for phone calls"""
        import time
        logger.info("🔔 HOOK FIRED: on_enter - agent entering conversation")
        
        # Send proactive greeting on first entry (phone calls)
        if self.is_phone_call and not self._has_greeted:
            logger.info("📞 Phone call detected - sending proactive greeting")
            greeting_start = time.time()
            greeting = "Hi, thanks for calling Indianapolis Pickleball Club. This is ACE, how can I help you today?"
            try:
                await ctx.reply(greeting)
                greeting_time = (time.time() - greeting_start) * 1000
                self._has_greeted = True
                logger.info(f"✅ ACE proactive greeting sent via on_enter hook (took {greeting_time:.1f}ms)")
                
                # Log greeting as transcript
                self.latency_metrics['transcripts'].append({
                    'timestamp': time.time(),
                    'text': greeting,
                    'role': 'assistant'
                })
                logger.info(f"🤖 ASSISTANT RESPONSE (greeting): {greeting}")
            except Exception as e:
                logger.error(f"❌ Failed to send greeting: {e}", exc_info=True)
        
        # Capture assistant responses as transcripts
        try:
            if ctx.messages:
                for msg in reversed(ctx.messages[-5:]):
                    if hasattr(msg, 'role') and msg.role == 'assistant':
                        content = msg.content
                        if isinstance(content, str) and content:
                            # Log as transcript
                            existing = [t for t in self.latency_metrics['transcripts'] 
                                      if t['text'] == content[:50] and t['role'] == 'assistant']
                            if not existing:
                                self.latency_metrics['transcripts'].append({
                                    'timestamp': time.time(),
                                    'text': content,
                                    'role': 'assistant'
                                })
                                logger.info(f"🤖 ASSISTANT RESPONSE: {content[:200]}...")
        except Exception as e:
            logger.debug(f"Error in on_enter: {e}")
    
    def _on_metrics_collected(self, ev):
        """Handle LiveKit metrics events to track latency components"""
        import time
        
        # Log metrics for debugging
        metrics.log_metrics(ev.metrics)
        
        # Process each metric type
        for metric in ev.metrics:
            speech_id = None
            
            # Extract speech_id if available (links metrics from same turn)
            if hasattr(metric, 'speech_id') and metric.speech_id:
                speech_id = metric.speech_id
            
            # Initialize tracking for this speech_id if needed
            if speech_id and speech_id not in self._metrics_by_speech_id:
                self._metrics_by_speech_id[speech_id] = {
                    'eou': None,
                    'llm': None,
                    'tts': None,
                    'stt': None,
                    'rag_duration': self._pending_rag_duration  # Capture pending RAG duration
                }
                # Reset pending RAG after assigning to speech_id
                self._pending_rag_duration = 0
            elif speech_id and self._pending_rag_duration > 0:
                # If speech_id already exists but we have new RAG duration, update it
                self._metrics_by_speech_id[speech_id]['rag_duration'] = self._pending_rag_duration
                self._pending_rag_duration = 0
            
            # Handle EOU metrics (End-of-Utterance)
            if isinstance(metric, metrics.EOUMetrics):
                if speech_id:
                    self._metrics_by_speech_id[speech_id]['eou'] = metric
                    logger.info(f"⏱️  EOU Metrics (speech_id={speech_id}): "
                              f"end_of_utterance_delay={metric.end_of_utterance_delay*1000:.1f}ms, "
                              f"transcription_delay={metric.transcription_delay*1000:.1f}ms, "
                              f"on_user_turn_completed_delay={metric.on_user_turn_completed_delay*1000:.1f}ms")
                self._check_complete_turn(speech_id)
            
            # Handle LLM metrics
            elif isinstance(metric, metrics.LLMMetrics):
                if speech_id:
                    self._metrics_by_speech_id[speech_id]['llm'] = metric
                    logger.info(f"⏱️  LLM Metrics (speech_id={speech_id}): "
                              f"ttft={metric.ttft*1000:.1f}ms, "
                              f"duration={metric.duration*1000:.1f}ms, "
                              f"tokens={metric.completion_tokens}, "
                              f"tokens_per_sec={metric.tokens_per_second:.1f}")
                self._check_complete_turn(speech_id)
            
            # Handle TTS metrics
            elif isinstance(metric, metrics.TTSMetrics):
                if speech_id:
                    self._metrics_by_speech_id[speech_id]['tts'] = metric
                    logger.info(f"⏱️  TTS Metrics (speech_id={speech_id}): "
                              f"ttfb={metric.ttfb*1000:.1f}ms, "
                              f"duration={metric.duration*1000:.1f}ms, "
                              f"audio_duration={metric.audio_duration:.2f}s")
                self._check_complete_turn(speech_id)
            
            # Handle STT metrics
            elif isinstance(metric, metrics.STTMetrics):
                if speech_id:
                    self._metrics_by_speech_id[speech_id]['stt'] = metric
                    logger.info(f"⏱️  STT Metrics (speech_id={speech_id}): "
                              f"duration={metric.duration*1000:.1f}ms, "
                              f"audio_duration={metric.audio_duration:.2f}s, "
                              f"streamed={metric.streamed}")
    
    def _check_complete_turn(self, speech_id):
        """Calculate and log total latency when all metrics are available"""
        import time
        
        if not speech_id or speech_id not in self._metrics_by_speech_id:
            return
        
        turn_data = self._metrics_by_speech_id[speech_id]
        eou = turn_data['eou']
        llm = turn_data['llm']
        tts = turn_data['tts']
        
        # Calculate total latency using LiveKit's official formula:
        # total_latency = eou.end_of_utterance_delay + llm.ttft + tts.ttfb
        # Only log if we have all three components
        if eou and llm and tts:
            total_latency_ms = (
                eou.end_of_utterance_delay * 1000 +
                llm.ttft * 1000 +
                tts.ttfb * 1000
            )
            
            # Build comprehensive turn summary
            turn_summary = {
                'speech_id': speech_id,
                'timestamp': time.time(),
                'total_latency_ms': total_latency_ms,
                'eou_delay_ms': eou.end_of_utterance_delay * 1000,
                'transcription_delay_ms': eou.transcription_delay * 1000,
                'on_user_turn_completed_delay_ms': eou.on_user_turn_completed_delay * 1000,
                'llm_ttft_ms': llm.ttft * 1000,
                'llm_total_ms': llm.duration * 1000,
                'llm_tokens': llm.completion_tokens,
                'llm_tokens_per_sec': llm.tokens_per_second,
                'tts_ttfb_ms': tts.ttfb * 1000,
                'tts_total_ms': tts.duration * 1000,
                'tts_audio_duration_s': tts.audio_duration,
                'rag_duration_ms': turn_data.get('rag_duration', 0)
            }
            
            # Add STT metrics if available
            if turn_data['stt']:
                stt = turn_data['stt']
                turn_summary['stt_duration_ms'] = stt.duration * 1000
                turn_summary['stt_audio_duration_s'] = stt.audio_duration
            
            # Store turn data
            self.latency_metrics['turns'].append(turn_summary)
            
            # Log comprehensive metrics
            logger.info(f"📊 COMPLETE TURN METRICS (speech_id={speech_id}):")
            logger.info(f"   🎯 TOTAL LATENCY: {total_latency_ms:.1f}ms")
            logger.info(f"   📝 EOU delay: {eou.end_of_utterance_delay*1000:.1f}ms")
            logger.info(f"   🧠 LLM TTFT: {llm.ttft*1000:.1f}ms | Total: {llm.duration*1000:.1f}ms | {llm.completion_tokens} tokens")
            logger.info(f"   🔊 TTS TTFB: {tts.ttfb*1000:.1f}ms | Total: {tts.duration*1000:.1f}ms")
            if turn_data.get('rag_duration'):
                logger.info(f"   🔍 RAG: {turn_data['rag_duration']:.1f}ms")
            
            # Mark as logged to avoid duplicate processing
            turn_data['_logged'] = True
    
    # Keywords that indicate IPC-related queries
    IPC_KEYWORDS = [
        # Facility
        "hours", "open", "closed", "close", "location", "address", "parking", "courts", "facility",
        # Membership
        "membership", "member", "pricing", "price", "cost", "pass", "join", "signup", "sign up", 
        "subscription", "tier", "plan", "$29", "monthly", "unlimited",
        # Programs
        "open play", "league", "class", "lesson", "clinic", "tournament", "event", "program",
        # Policies
        "cancellation", "cancel", "reservation", "reserve", "booking", "book", "rules", "policy",
        "etiquette", "guidelines",
        # Staff
        "instructor", "coach", "chris", "ryan", "jaci", "slater", "staff",
        # General IPC queries
        "ipc", "indianapolis pickleball", "pickleball club", "information", "info", "tell me about",
        "what is", "how do", "where", "when", "who"
    ]
    
    
    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Smart RAG lookup: only search when IPC keywords detected - optimized for low latency"""
        import time
        logger.info("🔔 HOOK FIRED: on_user_turn_completed")  # Debug: verify hook is called
        
        rag_start = time.time()
        
        # Get text content - handle both string and list formats
        content = new_message.content
        logger.debug(f"🔍 Raw content type: {type(content)}, value: {str(content)[:100]}")
        if isinstance(content, list):
            # Extract text from content blocks (usually first item is text)
            user_text = ""
            for item in content:
                if isinstance(item, str):
                    user_text += item + " "
                elif hasattr(item, 'text'):
                    user_text += item.text + " "
            user_text = user_text.strip().lower()
        elif isinstance(content, str):
            user_text = content.lower()
        else:
            user_text = str(content).lower() if content else ""
        
        # Store transcript
        if user_text:
            self.latency_metrics['transcripts'].append({
                'timestamp': time.time(),
                'text': user_text,
                'role': 'user'
            })
            logger.info(f"📝 USER TRANSCRIPT: {user_text}")
        else:
            logger.error(f"❌ FAILED TO EXTRACT USER TEXT - content type: {type(content)}, value: {repr(content)[:200]}")
        
        if not user_text:
            return  # Skip if no text content
        
        # Check if user query is likely IPC-related
        rag_time = 0
        if any(keyword in user_text for keyword in self.IPC_KEYWORDS):
            try:
                logger.debug(f"RAG: IPC keywords detected, performing search...")
                rag_content = await self.knowledge_base.search(user_text, top_k=3)
                rag_time = (time.time() - rag_start) * 1000  # Store in ms
                
                if rag_content and "couldn't find" not in rag_content.lower():
                    # Inject relevant knowledge into context
                    turn_ctx.add_message(
                        role="assistant",
                        content=f"IPC information relevant to this question: {rag_content}"
                    )
                    logger.info(f"🔍 RAG: Injected knowledge (took {rag_time:.1f}ms)")
                else:
                    logger.debug(f"RAG: No relevant knowledge found (took {rag_time:.1f}ms)")
            except Exception as e:
                rag_time = (time.time() - rag_start) * 1000
                logger.warning(f"RAG lookup failed (took {rag_time:.1f}ms): {e}")
                # Continue without RAG if lookup fails
        
        # Store RAG duration - we'll correlate it with speech_id in metrics handler
        # Since we don't have speech_id yet, store it temporarily and correlate later
        # The RAG happens in on_user_turn_completed, which is before EOU metrics arrive
        # We'll match RAG to the next speech_id that comes in
        self._pending_rag_duration = rag_time
    
    
    def _log_latency_summary(self):
        """Log summary of latency metrics"""
        import statistics
        
        metrics = self.latency_metrics
        summary = []
        
        if metrics['rag_times']:
            avg_rag = statistics.mean(metrics['rag_times'])
            max_rag = max(metrics['rag_times'])
            summary.append(f"RAG: avg={avg_rag:.1f}ms, max={max_rag:.1f}ms")
        
        if metrics['transcripts']:
            summary.append(f"Transcripts: {len(metrics['transcripts'])} turns")
        
        if summary:
            logger.info(f"📊 LATENCY SUMMARY: {' | '.join(summary)}")

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the voice agent"""
    import time
    entrypoint_start = time.time()
    logger.info(f"🚀 ENTRYPOINT: Agent starting for room: {ctx.room.name}")

    # Initialize agent instance
    agent = ClaudeVoiceAgent()
    agent.is_telephony = True  # This agent ONLY handles phone calls
    logger.info("Handling phone call")

    # Parse room metadata if available
    if ctx.room.metadata:
        try:
            import json
            agent.call_metadata = json.loads(ctx.room.metadata)
            logger.info(f"Call metadata: {agent.call_metadata}")
        except:
            pass

    # Get system instructions (this agent only handles phone calls)
    system_instructions = agent.get_system_instructions()

    # Connect to room with audio-only subscription for phone calls
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    logger.info("Connected to room, initializing voice agent")

    # Prepare tools list (include knowledge tool as fallback)
    tools_list = [weather_tool, calendar_tool, check_availability, database_query, query_ipc_knowledge, detect_voicemail]

    # Create IPC Assistant with instructions and tools (defines behavior)
    # Uses IPCAssistant class which has smart RAG hook for automatic knowledge injection
    try:
        voice_agent = IPCAssistant(
            instructions=system_instructions,
            tools=tools_list,
            is_phone_call=True,  # Always true - this agent only handles calls
        )
        logger.info("IPC Assistant (behavior) initialized with RAG knowledge base")

    except Exception as e:
        logger.error(f"Failed to initialize voice agent: {e}")
        raise

    # Create AgentSession with STT/LLM/TTS/VAD components
    # Optimized for low latency phone calls
    try:
        # Optimized VAD settings for faster turn detection (phone calls)
        # Lower min_silence_duration = faster response, but risk of interruption
        # 0.3s is a good balance for phone calls (default is 0.55s)
        optimized_vad = silero.VAD.load(
            min_speech_duration=0.1,  # Faster speech detection
            min_silence_duration=0.3,  # Faster end-of-speech detection (optimized for phones)
        )
        
        session = AgentSession(
            stt=openai.STT(
                model=config.stt_model,
                language="en"  # Force English only
            ),
            llm=openai.LLM(
                model=config.llm_model,
                temperature=config.llm_temperature,
            ),
            tts=openai.TTS(
                model=config.tts_model,
                voice=config.tts_voice,
                speed=config.tts_speed
            ),
            vad=optimized_vad,
            # Enable preemptive generation - start generating response before user finishes speaking
            # This can save 200-500ms but requires careful tuning
            preemptive_generation=True,
        )
        logger.info("Agent session initialized with latency-optimized components (fast VAD, preemptive generation)")
        
        # CRITICAL: Hook into LiveKit's metrics events for latency tracking
        # This is the official way to measure conversation latency
        session.on("metrics_collected", voice_agent._on_metrics_collected)
        logger.info("✅ Metrics collection enabled - will track EOU, LLM, TTS, and STT metrics")
        
        # Add thinking audio to mask RAG/LLM latency
        # This plays a subtle sound while the agent is "thinking" (waiting for LLM response)
        if HAS_BACKGROUND_AUDIO:
            try:
                background_audio = BackgroundAudioPlayer(
                    thinking_sound=[
                        BuiltinAudioClip.KEYBOARD_TYPING,  # Subtle typing sound
                    ]
                )
                await background_audio.start(room=ctx.room, agent_session=session)
                logger.info("Thinking audio enabled - will play during RAG/LLM processing")
            except Exception as e:
                logger.warning(f"Could not enable thinking audio: {e}")
        else:
            logger.info("Thinking audio not available (BackgroundAudioPlayer not in this LiveKit version)")
        
        # Handle conversation until room closes (sync callback)
        def on_room_closed():
            logger.info("Room closed, shutting down agent session")
            asyncio.create_task(session.aclose())
        
        ctx.room.on("room_closed", on_room_closed)

        # Start the session with the agent and room
        logger.info("🚀 Starting agent session...")
        session_start_time = time.time()
        await session.start(voice_agent, room=ctx.room)
        session_start_duration = (time.time() - session_start_time) * 1000
        logger.info(f"✅ Agent session started successfully (took {session_start_duration:.1f}ms)")
        
        # CRITICAL: Set up transcript capture using transcription_node
        # This is the built-in LiveKit mechanism for capturing transcripts
        logger.info("📝 Setting up transcript capture via transcription_node...")
        try:
            # transcription_node is available after session.start()
            if hasattr(voice_agent, 'transcription_node') and voice_agent.transcription_node:
                logger.info("✅ Transcription node found - setting up capture")
                
                # Capture transcripts from transcription node
                def on_transcription(transcription):
                    import time
                    try:
                        if hasattr(transcription, 'segments') and transcription.segments:
                            for segment in transcription.segments:
                                text = segment.text.strip() if hasattr(segment, 'text') else str(segment).strip()
                                if text and len(text) > 2:
                                    # Check participant identity to determine role
                                    participant = segment.participant_identity if hasattr(segment, 'participant_identity') else None
                                    is_user = participant != "agent" and participant is not None
                                    role = 'user' if is_user else 'assistant'
                                    
                                    # Avoid duplicates
                                    existing = [t for t in voice_agent.latency_metrics['transcripts'] 
                                              if t['text'] == text[:50] and abs(t['timestamp'] - time.time()) < 2]
                                    if not existing:
                                        voice_agent.latency_metrics['transcripts'].append({
                                            'timestamp': time.time(),
                                            'text': text,
                                            'role': role
                                        })
                                        
                                        if role == 'user':
                                            logger.info(f"📝 USER TRANSCRIPT: {text}")
                                        else:
                                            logger.info(f"🤖 ASSISTANT RESPONSE: {text[:200]}...")
                    except Exception as e:
                        logger.debug(f"Error in transcription handler: {e}")
                
                # Hook into transcription updates
                if hasattr(voice_agent.transcription_node, 'on'):
                    voice_agent.transcription_node.on("transcription_updated", on_transcription)
                    logger.info("✅ Transcription event handler registered")
                else:
                    logger.warning("⚠️  Transcription node doesn't support event subscription")
            else:
                logger.warning("⚠️  Transcription node not available - using hook-based capture")
        except Exception as e:
            logger.error(f"❌ Failed to set up transcription capture: {e}", exc_info=True)
        
        # Note: Proactive greeting is handled by on_enter() hook in IPCAssistant class
        # The hook will trigger automatically when the session starts

        # Keep session running - it handles the conversation loop automatically
        # Wait indefinitely until room closes or cancelled
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("Agent session cancelled, cleaning up")
            await session.aclose()
            
    except Exception as e:
        logger.error(f"Failed to start agent session: {e}", exc_info=True)
        raise

async def request_fnc(ctx: JobContext):
    """Handle job requests for explicit dispatch"""
    logger.info(f"Received job request for room: {ctx.room.name}")

    # Accept all requests - simplified for new API
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    return await entrypoint(ctx)

if __name__ == "__main__":
    # Load environment variables from parent directory
    from dotenv import load_dotenv
    from pathlib import Path
    import os

    # Get the absolute path to the parent directory's .env.local
    current_file = Path(__file__).resolve()
    parent_dir = current_file.parent.parent
    env_path = parent_dir / '.env.local'

    # Try to load the .env.local file
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment from: {env_path}")
    else:
        logger.error(f"Could not find .env.local at {env_path}")
        logger.error(f"Please ensure .env.local exists in {parent_dir}")
        exit(1)

    # Reload configuration after loading environment variables
    from config import Config
    config = Config()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)

    # Log configuration
    logger.info(f"Configuration loaded: {config}")
    voice_info = config.get_tts_voice_info()
    logger.info(f"TTS Voice: {voice_info['voice']} - {voice_info['description']}")

    # Configure worker options
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=config.agent_name,  # Set agent name for dispatch matching
        # worker_type="voice",
        # max_idle_time=60,  # Disconnect after 60s of inactivity
        # num_idle_workers=2,  # Keep 2 workers ready
        # max_workers=10  # Scale up to 10 concurrent calls
    )

    logger.info(f"Starting ClaudeVoice agent: {config.agent_name}")

    # Run the agent
    cli.run_app(worker_options)