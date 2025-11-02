# Test GUI (Alternative Testing Method)

**Note: Use LiveKit Playground instead** (recommended - see main README).

This custom GUI is provided as an alternative if you need custom testing scenarios.

## Usage

1. Start agent: `python main.py dev` (from agent directory)
2. Generate token: `python generate_token.py`
3. Open `index.html` in browser
4. Paste token and room name
5. **Manually dispatch agent** after connecting:
   ```bash
   python dispatch_agent.py <room-name>
   ```

The orchestrator can automate dispatch (optional).
