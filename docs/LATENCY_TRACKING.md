# Latency Tracking System

## Overview

This document describes the comprehensive latency tracking system implemented for the ACE voice agent. The system uses **LiveKit's official metrics API** to capture and analyze conversation latency at multiple levels.

## How Latency is Measured

### Official LiveKit Formula

According to the [LiveKit documentation](https://docs.livekit.io/agents/build/metrics/#measuring-conversation-latency), total conversation latency is calculated as:

```
total_latency = eou.end_of_utterance_delay + llm.ttft + tts.ttfb
```

Where:
- **`eou.end_of_utterance_delay`**: Time from end of user speech (VAD detection) to turn completion, including transcription delay
- **`llm.ttft`**: Time-to-First-Token - how long until the LLM generates its first token
- **`tts.ttfb`**: Time-to-First-Byte - how long until TTS generates its first audio byte

### Metrics Components

The system tracks the following metrics automatically via LiveKit's `metrics_collected` event:

#### 1. End-of-Utterance (EOU) Metrics
- `end_of_utterance_delay`: Total delay from speech end to turn completion
- `transcription_delay`: Time between end of speech and final transcript availability
- `on_user_turn_completed_delay`: Time to execute the `on_user_turn_completed` callback
- `speech_id`: Unique identifier linking metrics from the same turn

#### 2. LLM Metrics
- `ttft`: Time to first token (seconds)
- `duration`: Total LLM generation time (seconds)
- `completion_tokens`: Number of tokens generated
- `prompt_tokens`: Number of tokens in the prompt
- `tokens_per_second`: Generation rate
- `speech_id`: Links to the user turn

#### 3. TTS Metrics
- `ttfb`: Time to first byte (seconds)
- `duration`: Total TTS synthesis time (seconds)
- `audio_duration`: Length of generated audio (seconds)
- `characters_count`: Number of characters in input text
- `speech_id`: Links to the LLM response

#### 4. STT Metrics (if available)
- `duration`: STT processing time (seconds)
- `audio_duration`: Length of audio processed (seconds)
- `streamed`: Whether streaming STT was used

#### 5. RAG Metrics (custom)
- `rag_duration`: Time spent searching the knowledge base (milliseconds)
- Correlated with `speech_id` when RAG is triggered

## Implementation

### Metrics Collection Hook

The system hooks into LiveKit's `metrics_collected` event on the `AgentSession`:

```python
session.on("metrics_collected", voice_agent._on_metrics_collected)
```

### Metrics Processing

1. **Event Reception**: The `_on_metrics_collected` handler receives metrics events
2. **Speech ID Correlation**: Metrics are grouped by `speech_id` to link EOU, LLM, and TTS from the same turn
3. **RAG Correlation**: RAG duration (measured in `on_user_turn_completed`) is matched to the corresponding `speech_id`
4. **Complete Turn Calculation**: When all components (EOU, LLM, TTS) are available, total latency is calculated
5. **Storage**: Complete turn data is stored in `latency_metrics['turns']` for analysis

### Logging Format

The system logs comprehensive metrics for each completed turn:

```
📊 COMPLETE TURN METRICS (speech_id=abc123):
   🎯 TOTAL LATENCY: 1250.5ms
   📝 EOU delay: 350.2ms
   🧠 LLM TTFT: 450.3ms | Total: 1200.5ms | 125 tokens
   🔊 TTS TTFB: 450.0ms | Total: 800.2ms
   🔍 RAG: 125.5ms
```

## Creating a Baseline

### 1. Collect Metrics During Conversations

Simply run the agent and have conversations. Metrics are automatically collected and logged to `/tmp/agent_new.log`.

### 2. Analyze the Baseline

Use the analysis script to generate a baseline report:

```bash
python scripts/analyze_latency_baseline.py [log_file]
```

The script will:
- Parse all latency metrics from logs
- Calculate statistics (mean, median, min, max, percentiles)
- Show component breakdowns
- Display recent turns
- Save baseline data to `/tmp/agent_latency_baseline.json`

### 3. Baseline Metrics

The baseline includes:
- **Total Latency Statistics**: Mean, median, percentiles (P50, P75, P90, P95, P99)
- **Component Breakdown**: Individual statistics for EOU, LLM, TTS, STT, RAG
- **Turn History**: Complete metrics for each conversation turn
- **Raw Data**: All metrics stored as JSON for further analysis

## Monitoring Real-Time Metrics

### During Development

Watch logs in real-time:

```bash
tail -f /tmp/agent_new.log | grep -E "(COMPLETE TURN|TOTAL LATENCY|METRICS)"
```

### Using Monitoring Scripts

The monitoring scripts (`scripts/monitor.sh`, `scripts/monitor_all.sh`) will display metrics as they're collected.

## Interpreting Results

### Target Latencies

For a responsive phone conversation:
- **Total Latency**: < 1500ms (1.5 seconds)
- **EOU Delay**: < 500ms
- **LLM TTFT**: < 600ms
- **TTS TTFB**: < 500ms

### Component Optimization

- **High EOU Delay**: Reduce VAD `min_silence_duration` (but risk interruptions)
- **High LLM TTFT**: Use faster model, enable preemptive generation, optimize prompts
- **High TTS TTFB**: Use streaming TTS, faster voice models
- **High RAG Duration**: Optimize embedding search, reduce `top_k`, cache common queries

## Baseline Comparison

After making optimizations, re-run the analysis script to compare against the baseline:

1. **Before Optimization**: Run baseline analysis → save results
2. **Make Changes**: Optimize components (VAD, LLM, TTS, RAG)
3. **After Optimization**: Run analysis again → compare metrics
4. **Improvement Calculation**: Track percentage improvements for each component

## Files

- **`agent/main.py`**: Implements `_on_metrics_collected` handler and latency tracking
- **`scripts/analyze_latency_baseline.py`**: Analyzes logs and generates baseline reports
- **`docs/LATENCY_TRACKING.md`**: This document

## References

- [LiveKit Metrics Documentation](https://docs.livekit.io/agents/build/metrics/#measuring-conversation-latency)
- [LiveKit Agent Hooks](https://docs.livekit.io/agents/build/workflows/#hooks)

