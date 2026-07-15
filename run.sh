#!/bin/bash
# Quick start script for the agent

cd "$(dirname "$0")" || exit 1
exec uv run --frozen python -m agent.main dev
