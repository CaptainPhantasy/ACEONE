#!/usr/bin/env python3
"""
Latency Analysis Tool for ACE Voice Agent
Extracts and analyzes latency metrics from agent logs
"""

import re
import sys
from collections import defaultdict
from statistics import mean, median, stdev

def parse_log_file(log_file="/tmp/agent.log"):
    """Parse log file and extract latency metrics"""
    metrics = {
        'rag_times': [],
        'greeting_times': [],
        'transcripts': [],
        'errors': []
    }
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # RAG timing
                rag_match = re.search(r'RAG:.*?(\d+\.?\d*)ms', line)
                if rag_match:
                    metrics['rag_times'].append(float(rag_match.group(1)))
                
                # Greeting timing
                greeting_match = re.search(r'greeting.*?(\d+\.?\d*)ms', line, re.IGNORECASE)
                if greeting_match:
                    metrics['greeting_times'].append(float(greeting_match.group(1)))
                
                # Transcripts
                if 'USER TRANSCRIPT:' in line or 'ASSISTANT RESPONSE:' in line:
                    metrics['transcripts'].append(line.strip())
                
                # Errors
                if 'ERROR' in line or 'WARNING' in line:
                    metrics['errors'].append(line.strip())
    
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return None
    
    return metrics

def print_statistics(metrics):
    """Print formatted statistics"""
    print("\n" + "="*60)
    print("📊 ACE Voice Agent - Latency Analysis")
    print("="*60)
    
    # RAG Statistics
    if metrics['rag_times']:
        print(f"\n🔍 RAG Lookup Performance:")
        print(f"   Count: {len(metrics['rag_times'])}")
        print(f"   Average: {mean(metrics['rag_times']):.1f}ms")
        print(f"   Median: {median(metrics['rag_times']):.1f}ms")
        print(f"   Min: {min(metrics['rag_times']):.1f}ms")
        print(f"   Max: {max(metrics['rag_times']):.1f}ms")
        if len(metrics['rag_times']) > 1:
            print(f"   Std Dev: {stdev(metrics['rag_times']):.1f}ms")
    else:
        print("\n🔍 RAG Lookup Performance: No data")
    
    # Greeting Statistics
    if metrics['greeting_times']:
        print(f"\n👋 Greeting Performance:")
        print(f"   Count: {len(metrics['greeting_times'])}")
        print(f"   Average: {mean(metrics['greeting_times']):.1f}ms")
        print(f"   Median: {median(metrics['greeting_times']):.1f}ms")
    else:
        print("\n👋 Greeting Performance: No data")
    
    # Transcripts
    print(f"\n📝 Transcripts:")
    print(f"   Total: {len(metrics['transcripts'])}")
    if metrics['transcripts']:
        print(f"   Recent (last 5):")
        for transcript in metrics['transcripts'][-5:]:
            print(f"     {transcript[:80]}...")
    
    # Errors/Warnings
    if metrics['errors']:
        print(f"\n⚠️  Errors/Warnings: {len(metrics['errors'])}")
        for error in metrics['errors'][-5:]:
            print(f"     {error[:80]}...")
    else:
        print(f"\n✅ No errors found")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agent.log"
    metrics = parse_log_file(log_file)
    
    if metrics:
        print_statistics(metrics)
    else:
        sys.exit(1)

