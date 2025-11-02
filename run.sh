#!/bin/bash
# Quick start script for the agent

cd "$(dirname "$0")/agent"
source venv/bin/activate
python main.py dev
