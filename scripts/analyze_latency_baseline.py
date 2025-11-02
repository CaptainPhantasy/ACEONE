#!/usr/bin/env python3
"""
Analyze latency baseline from agent logs.

This script parses the agent logs and extracts latency metrics to create
a baseline for conversation latency improvement.

Usage:
    python scripts/analyze_latency_baseline.py [log_file]
"""

import re
import sys
import json
import statistics
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def parse_latency_metrics(log_file: Path) -> Dict:
    """Parse latency metrics from agent logs"""
    metrics_data = {
        'turns': [],
        'eou_delays': [],
        'llm_ttft': [],
        'llm_total': [],
        'tts_ttfb': [],
        'tts_total': [],
        'total_latencies': [],
        'rag_durations': [],
        'stt_durations': []
    }
    
    # Patterns to match metrics in logs
    patterns = {
        'total_latency': re.compile(r'TOTAL LATENCY:\s+(\d+\.?\d*)ms'),
        'eou_delay': re.compile(r'EOU delay:\s+(\d+\.?\d*)ms'),
        'llm_ttft': re.compile(r'LLM TTFT:\s+(\d+\.?\d*)ms'),
        'llm_total': re.compile(r'LLM.*Total:\s+(\d+\.?\d*)ms'),
        'tts_ttfb': re.compile(r'TTS TTFB:\s+(\d+\.?\d*)ms'),
        'tts_total': re.compile(r'TTS.*Total:\s+(\d+\.?\d*)ms'),
        'rag': re.compile(r'RAG:\s+(\d+\.?\d*)ms'),
        'stt': re.compile(r'STT.*duration.*?(\d+\.?\d*)ms'),
    }
    
    if not log_file.exists():
        print(f"{Colors.RED}Error: Log file not found: {log_file}{Colors.END}")
        return metrics_data
    
    print(f"{Colors.CYAN}Parsing log file: {log_file}{Colors.END}")
    
    current_turn = {}
    with open(log_file, 'r') as f:
        for line in f:
            # Look for complete turn metrics
            if 'COMPLETE TURN METRICS' in line:
                # Extract speech_id if present
                speech_id_match = re.search(r'speech_id=([^\s\)]+)', line)
                if speech_id_match:
                    current_turn = {'speech_id': speech_id_match.group(1)}
            
            # Extract metrics from the following lines
            for metric_type, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    value = float(match.group(1))
                    
                    if metric_type == 'total_latency':
                        metrics_data['total_latencies'].append(value)
                        current_turn['total_latency'] = value
                    elif metric_type == 'eou_delay':
                        metrics_data['eou_delays'].append(value)
                        current_turn['eou_delay'] = value
                    elif metric_type == 'llm_ttft':
                        metrics_data['llm_ttft'].append(value)
                        current_turn['llm_ttft'] = value
                    elif metric_type == 'llm_total':
                        metrics_data['llm_total'].append(value)
                        current_turn['llm_total'] = value
                    elif metric_type == 'tts_ttfb':
                        metrics_data['tts_ttfb'].append(value)
                        current_turn['tts_ttfb'] = value
                    elif metric_type == 'tts_total':
                        metrics_data['tts_total'].append(value)
                        current_turn['tts_total'] = value
                    elif metric_type == 'rag':
                        metrics_data['rag_durations'].append(value)
                        current_turn['rag_duration'] = value
                    elif metric_type == 'stt':
                        metrics_data['stt_durations'].append(value)
                        current_turn['stt_duration'] = value
            
            # If we have a complete turn, save it
            if current_turn and 'total_latency' in current_turn:
                metrics_data['turns'].append(current_turn.copy())
                current_turn = {}
    
    return metrics_data

def calculate_statistics(values: List[float]) -> Dict:
    """Calculate statistical measures for a list of values"""
    if not values:
        return {
            'count': 0,
            'mean': None,
            'median': None,
            'min': None,
            'max': None,
            'stddev': None,
            'p50': None,
            'p75': None,
            'p90': None,
            'p95': None,
            'p99': None
        }
    
    sorted_values = sorted(values)
    return {
        'count': len(values),
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'min': min(values),
        'max': max(values),
        'stddev': statistics.stdev(values) if len(values) > 1 else 0,
        'p50': sorted_values[int(len(sorted_values) * 0.50)],
        'p75': sorted_values[int(len(sorted_values) * 0.75)],
        'p90': sorted_values[int(len(sorted_values) * 0.90)],
        'p95': sorted_values[int(len(sorted_values) * 0.95)],
        'p99': sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[-1]
    }

def print_statistics_table(stats: Dict, label: str, unit: str = 'ms'):
    """Print a formatted statistics table"""
    if stats['count'] == 0:
        print(f"{Colors.YELLOW}  No {label} metrics found{Colors.END}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{label} Statistics ({stats['count']} samples){Colors.END}")
    print(f"  {Colors.CYAN}Mean:{Colors.END}   {stats['mean']:.1f}{unit}")
    print(f"  {Colors.CYAN}Median:{Colors.END} {stats['median']:.1f}{unit}")
    print(f"  {Colors.CYAN}Min:{Colors.END}    {stats['min']:.1f}{unit}")
    print(f"  {Colors.CYAN}Max:{Colors.END}    {stats['max']:.1f}{unit}")
    print(f"  {Colors.CYAN}StdDev:{Colors.END} {stats['stddev']:.1f}{unit}")
    print(f"  {Colors.CYAN}Percentiles:{Colors.END}")
    print(f"    P50: {stats['p50']:.1f}{unit}  P75: {stats['p75']:.1f}{unit}")
    print(f"    P90: {stats['p90']:.1f}{unit}  P95: {stats['p95']:.1f}{unit}  P99: {stats['p99']:.1f}{unit}")

def print_baseline_summary(metrics_data: Dict):
    """Print comprehensive baseline summary"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}LATENCY BASELINE ANALYSIS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}\n")
    
    # Total latency (most important metric)
    total_stats = calculate_statistics(metrics_data['total_latencies'])
    print_statistics_table(total_stats, "🎯 Total Conversation Latency", "ms")
    
    # Breakdown by component
    print(f"\n{Colors.BOLD}{Colors.BLUE}Component Breakdown:{Colors.END}")
    
    eou_stats = calculate_statistics(metrics_data['eou_delays'])
    print_statistics_table(eou_stats, "📝 EOU (End-of-Utterance) Delay", "ms")
    
    llm_ttft_stats = calculate_statistics(metrics_data['llm_ttft'])
    print_statistics_table(llm_ttft_stats, "🧠 LLM Time-to-First-Token", "ms")
    
    llm_total_stats = calculate_statistics(metrics_data['llm_total'])
    print_statistics_table(llm_total_stats, "🧠 LLM Total Generation Time", "ms")
    
    tts_ttfb_stats = calculate_statistics(metrics_data['tts_ttfb'])
    print_statistics_table(tts_ttfb_stats, "🔊 TTS Time-to-First-Byte", "ms")
    
    tts_total_stats = calculate_statistics(metrics_data['tts_total'])
    print_statistics_table(tts_total_stats, "🔊 TTS Total Synthesis Time", "ms")
    
    # RAG timing (if available)
    if metrics_data['rag_durations']:
        rag_stats = calculate_statistics(metrics_data['rag_durations'])
        print_statistics_table(rag_stats, "🔍 RAG Lookup Duration", "ms")
    
    # STT timing (if available)
    if metrics_data['stt_durations']:
        stt_stats = calculate_statistics(metrics_data['stt_durations'])
        print_statistics_table(stt_stats, "🎤 STT Processing Duration", "ms")
    
    # Show individual turns if available
    if metrics_data['turns']:
        print(f"\n{Colors.BOLD}{Colors.BLUE}Recent Turns:{Colors.END}")
        for i, turn in enumerate(metrics_data['turns'][-10:], 1):
            print(f"\n  {Colors.CYAN}Turn {i}:{Colors.END}")
            print(f"    Total: {turn.get('total_latency', 'N/A'):.1f}ms")
            if 'eou_delay' in turn:
                print(f"    EOU: {turn['eou_delay']:.1f}ms")
            if 'llm_ttft' in turn:
                print(f"    LLM-TTFT: {turn['llm_ttft']:.1f}ms | LLM-Total: {turn.get('llm_total', 'N/A'):.1f}ms")
            if 'tts_ttfb' in turn:
                print(f"    TTS-TTFB: {turn['tts_ttfb']:.1f}ms | TTS-Total: {turn.get('tts_total', 'N/A'):.1f}ms")
            if 'rag_duration' in turn:
                print(f"    RAG: {turn['rag_duration']:.1f}ms")
    
    # Save baseline to JSON file
    baseline_file = Path('/tmp/agent_latency_baseline.json')
    baseline_data = {
        'summary': {
            'total_latency': total_stats,
            'eou_delay': eou_stats,
            'llm_ttft': llm_ttft_stats,
            'llm_total': llm_total_stats,
            'tts_ttfb': tts_ttfb_stats,
            'tts_total': tts_total_stats,
        },
        'turns': metrics_data['turns'],
        'raw_metrics': {
            'total_latencies': metrics_data['total_latencies'],
            'eou_delays': metrics_data['eou_delays'],
            'llm_ttft': metrics_data['llm_ttft'],
            'llm_total': metrics_data['llm_total'],
            'tts_ttfb': metrics_data['tts_ttfb'],
            'tts_total': metrics_data['tts_total'],
            'rag_durations': metrics_data['rag_durations'],
            'stt_durations': metrics_data['stt_durations']
        }
    }
    
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"\n{Colors.GREEN}✅ Baseline saved to: {baseline_file}{Colors.END}")

def main():
    log_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/agent_new.log')
    
    print(f"{Colors.CYAN}Analyzing latency baseline from logs...{Colors.END}")
    metrics_data = parse_latency_metrics(log_file)
    
    if not metrics_data['total_latencies']:
        print(f"{Colors.YELLOW}⚠️  No latency metrics found in logs.{Colors.END}")
        print(f"{Colors.YELLOW}   Make sure the agent is running and generating metrics.{Colors.END}")
        sys.exit(1)
    
    print_baseline_summary(metrics_data)

if __name__ == '__main__':
    main()

