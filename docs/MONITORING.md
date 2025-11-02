# ACE Voice Agent - Monitoring & Latency Measurement Guide

## Overview

The ACE Voice Agent now has comprehensive monitoring and latency measurement capabilities built-in. This guide explains how to monitor logs, transcripts, and measure lag times.

## Monitoring System Components

### 1. **Real-Time Log Monitoring**

The agent logs the following with emoji prefixes for easy identification:

- 📝 **USER TRANSCRIPT**: User speech transcribed
- 🤖 **ASSISTANT RESPONSE**: Agent's response text
- 🔍 **RAG**: Knowledge base lookup timing
- 📊 **LATENCY SUMMARY**: Periodic performance summaries
- ✅ **System Events**: Greeting, worker registration, etc.
- ❌ **Errors**: Any errors or warnings

### 2. **Latency Metrics Tracked**

The agent automatically tracks:

- **RAG Lookup Times**: Time spent searching knowledge base
- **Greeting Time**: Time to send initial greeting
- **Transcripts**: Full conversation transcripts with timestamps
- **Turn Times**: Total time per conversation turn (when available)

### 3. **Monitoring Tools**

#### Real-Time Monitor (`scripts/monitor.sh`)

Colorized real-time log tailing with automatic highlighting:

```bash
./scripts/monitor.sh
```

**Features:**
- Color-coded output (transcripts, RAG, errors)
- Filters and highlights important events
- Real-time updates as logs are written

#### Latency Analyzer (`scripts/analyze_latency.py`)

Analyzes historical logs and provides statistics:

```bash
python scripts/analyze_latency.py [log_file]
```

**Output includes:**
- RAG lookup statistics (avg, median, min, max, std dev)
- Greeting performance metrics
- Transcript count and recent examples
- Error/warning summary

## What Gets Logged

### Transcripts

Every user utterance and agent response is logged:

```
📝 USER TRANSCRIPT: what are your hours?
🤖 ASSISTANT RESPONSE: We're open Monday through Friday...
```

### RAG Performance

When IPC keywords are detected, RAG lookups are timed:

```
🔍 RAG: IPC keywords detected, performing search...
🔍 RAG: Found 3 results in 245.3ms (embed: 180.2ms, search: 65.1ms)
🔍 RAG: Injected knowledge (total hook time: 245.3ms)
```

### Latency Summaries

Every 5 RAG lookups, a summary is logged:

```
📊 LATENCY SUMMARY: RAG: avg=234.5ms, max=312.1ms | Transcripts: 12 turns
```

### Greeting Performance

Initial greeting timing:

```
✅ ACE proactive greeting sent via on_start hook (took 45.2ms)
```

## Manual Monitoring Commands

### Watch Logs in Real-Time

```bash
# Basic tail
tail -f /tmp/agent.log

# Filter for specific events
tail -f /tmp/agent.log | grep -E "(TRANSCRIPT|RAG|LATENCY|ERROR)"

# Watch with timestamps
tail -f /tmp/agent.log | while read line; do echo "$(date '+%H:%M:%S') $line"; done
```

### Analyze Historical Data

```bash
# Full analysis
python scripts/analyze_latency.py

# Analyze specific log file
python scripts/analyze_latency.py /path/to/log.log

# Quick stats
grep "RAG:" /tmp/agent.log | grep -oE '[0-9]+\.[0-9]+ms' | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'
```

### Extract Transcripts

```bash
# User transcripts only
grep "USER TRANSCRIPT" /tmp/agent.log

# Assistant responses only
grep "ASSISTANT RESPONSE" /tmp/agent.log

# Full conversation
grep -E "(USER TRANSCRIPT|ASSISTANT RESPONSE)" /tmp/agent.log
```

## Latency Benchmarks

### Target Metrics

- **RAG Lookup**: < 300ms (currently averaging ~200-250ms)
- **Greeting**: < 100ms (currently ~45-50ms)
- **Total Turn Time**: < 2s (user speaks → agent responds)

### What to Watch For

**High RAG Latency (> 500ms):**
- Check embedding API response time
- Verify knowledge base size (should be manageable)
- Consider pre-warming embeddings

**High Turn Time (> 3s):**
- Check LLM response time (TTFT - Time To First Token)
- Verify network latency
- Check if preemptive generation is working

**Greeting Delays:**
- Verify `on_start()` hook is firing
- Check TTS initialization time
- Ensure no blocking operations before greeting

## Debugging Tips

### If No Transcripts Appear

1. Check if agent is receiving audio:
   ```bash
   grep "Agent starting for room" /tmp/agent.log
   ```

2. Verify STT is working:
   ```bash
   grep -i "stt\|transcript" /tmp/agent.log
   ```

### If RAG Not Triggering

1. Check if keywords are detected:
   ```bash
   grep "IPC keywords detected" /tmp/agent.log
   ```

2. Verify knowledge base loaded:
   ```bash
   grep "Knowledge base loaded" /tmp/agent.log
   ```

### If High Latency

1. Identify bottleneck:
   ```bash
   # Check RAG times
   grep "RAG:" /tmp/agent.log | tail -10
   
   # Check for errors
   grep -i "error\|warning" /tmp/agent.log | tail -10
   ```

2. Verify optimizations are active:
   ```bash
   grep "latency-optimized\|preemptive\|VAD" /tmp/agent.log
   ```

## Integration with LiveKit Metrics

The agent logs complement LiveKit's built-in metrics. You can access LiveKit metrics through:

- LiveKit Cloud Dashboard
- Prometheus/Grafana (if configured)
- LiveKit SDK metrics API

Our custom logs provide:
- **Application-level** timing (RAG, business logic)
- **Transcript-level** correlation (what was said when)
- **Easier debugging** with emoji prefixes and clear formatting

## Continuous Monitoring

For production, consider:

1. **Log Aggregation**: Send logs to Datadog, Splunk, or similar
2. **Alerting**: Set up alerts for:
   - RAG latency > 500ms
   - Error rate > 5%
   - No transcripts for > 30s
3. **Dashboards**: Create dashboards showing:
   - Average latency over time
   - RAG hit rate
   - Error frequency
   - Transcript count

## Example Monitoring Session

```bash
# Terminal 1: Start agent
./run.sh > /tmp/agent.log 2>&1 &

# Terminal 2: Monitor in real-time
./scripts/monitor.sh

# Terminal 3: Analyze periodically
watch -n 30 'python scripts/analyze_latency.py'
```

This gives you:
- Real-time colorized logs (Terminal 2)
- Periodic statistics (Terminal 3)
- Full log file for later analysis (Terminal 1)

