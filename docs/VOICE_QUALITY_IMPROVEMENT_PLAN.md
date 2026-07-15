# Voice Quality and Identity Improvement Plan

<!-- markdownlint-disable MD013 -->

**Created:** November 2, 2025

**Validated against the repository and current provider docs:** July 15, 2026
**Status:** Runtime lock complete; voice and identity implementation remains

## Goal

Make ACE sound natural while keeping its identity unambiguous: ACE is the
Indianapolis Pickleball Club assistant. It may use Chris Sears' approved tone
and stories, but it must never claim to be Chris or his literal voice.

## Facts confirmed before implementation

- `agent/main.py` sends the LLM stream to the `openai.TTS` instance owned by
  `AgentSession`. A standalone helper that is never connected to that stream
  cannot change synthesized speech.
- `agent/config.py` defaults are overridden by `.env.example`, deployed
  environment variables, and any local `.env` copied from the example.
- Identity text comes from three active sources: `persona/ace prompt`, the
  fallback in `agent/main.py`, and RAG chunks loaded from
  `persona/knowledge.md`.
- The repository now installs from `pyproject.toml` and `uv.lock` on Python
  3.13. The plan and its future implementation can target LiveKit Agents
  1.6.5 instead of relying on changing lower-bound dependency ranges.
- OpenAI's speech endpoint supports `tts-1`, `tts-1-hd`, and newer instruction-
  capable speech models. Speed is configurable from 0.25 to 4.0. Model and
  voice quality must be selected by a recorded comparison, not an unsupported
  latency claim.
- LiveKit exposes `Agent.tts_node` for transforming the text stream before it
  reaches TTS. The implementation must use that hook, or an equivalent hook
  verified against the locked SDK.

## Task 1: Lock the runtime before changing behavior — completed July 15, 2026

**Files:** `pyproject.toml`, `uv.lock`, CI configuration

1. Replace broad LiveKit, OpenAI, and test dependency ranges with a lock that
   installs on the supported Python version.
2. Record the exact `Agent.tts_node` signature for that LiveKit version.
3. Add gates for a clean install, import/compile, unit tests, and a no-network
   agent-construction smoke test.
4. Keep one explicit, opt-in live voice test for billed provider calls.

**Exit evidence:** a fresh environment installed from `uv.lock`; 18 tests,
Ruff, format checking, compilation, and `pip-audit` passed. The webhook also
builds under its locked Node dependencies with a zero-vulnerability audit.

## Task 2: Select a voice from recorded evidence

**Files:** `agent/config.py`, `.env.example`, deployment environment settings

Test at least these candidates with the same short IPC script:

- Current baseline: `tts-1` / `alloy` / `1.0`
- Quality baseline: `tts-1-hd` / `echo` / `1.05`
- Current instruction-capable OpenAI speech model supported by the locked
  LiveKit plugin

Score each recording for first-audio latency, intelligibility over a phone
codec, pronunciation of IPC terms, warmth, interruption recovery, and cost.
Choose the winner only after listening to the rendered call audio.

When a winner is selected, update every configuration surface together:

```python
self.tts_model = os.getenv("TTS_MODEL", SELECTED_MODEL)
self.tts_voice = os.getenv("TTS_VOICE", SELECTED_VOICE)
self.tts_speed = float(os.getenv("TTS_SPEED", SELECTED_SPEED))
```

- Update `TTS_MODEL`, `TTS_VOICE`, and `TTS_SPEED` in `.env.example`.
- Update deployed secrets/environment values; code defaults do not override an
  existing environment variable.
- Search deployment scripts and documentation for stale values.
- Validate model, voice, and speed at startup and fail with a useful error.

## Task 3: Correct identity in every active source

### `persona/ace prompt`

Replace embodiment language with:

```text
You are ACE, the Indianapolis Pickleball Club assistant. You use Chris Sears'
approved communication style and may share clearly attributed IPC stories,
but you are not Chris Sears and must never claim to be his literal voice.

When asked who or what you are, answer: "I'm ACE, the Indianapolis Pickleball
Club assistant."
```

Add these rules near the primary identity section:

```text
- Say: "I'm ACE" or "I'm ACE, the Indianapolis Pickleball Club assistant."
- Attribute Chris's experiences to Chris; do not narrate them as your own.
- Never say you are Chris, his embodiment, his digital extension, or his voice.
```

Update the Chris staff heading, the quality checklist, and the final mission
statement so none of them contradict those rules.

### `persona/knowledge.md`

Change `Chris Sears (Founder/Owner - YOU embody him)` to a factual staff
heading. Remove or rewrite any instruction-like identity claims from RAG data.
Knowledge chunks should provide facts; they must not compete with the system
prompt for identity control.

### `agent/main.py`

Apply the same wording to the fallback prompt and change the
`IPCAssistant` class description so maintenance text does not preserve the old
identity contract.

## Task 4: Use natural text without spoken control tokens

Update `persona/ace prompt` and `phone_additions` with these rules:

```text
- Keep most phone turns to one or two short sentences.
- Prefer ordinary sentence punctuation and contractions.
- Use an occasional ellipsis only when a natural thinking pause is intended.
- Never output SSML, XML, bracketed pause tokens, or repeated-period controls.
- Do not insert commas where normal grammar would not use them.
- Ask one clear follow-up question instead of delivering a monologue.
```

Examples must contain only text safe to speak aloud:

```text
"That's the thing. Empty courts with high prices? That's not us."
"Nine courts, climate controlled, with 24/7 access."
"The first day after we went paid... only two people showed up."
```

Do not promise fixed millisecond pauses from punctuation. Pause length varies
by model, voice, context, and tokenizer and must be measured from output audio.

## Task 5: Wire optional preprocessing into the LiveKit pipeline

Prompt changes come first. Add preprocessing only for deterministic cleanup,
such as stripping control tokens or normalizing whitespace. It must not insert
awkward punctuation into valid prose.

For a locked LiveKit version that supports the current node API, implement the
hook in `IPCAssistant` and pass the transformed stream into LiveKit's default
TTS node:

```python
from collections.abc import AsyncIterable

from livekit.agents import Agent, ModelSettings


async def tts_node(
    self,
    text: AsyncIterable[str],
    model_settings: ModelSettings,
):
    async def cleaned_text():
        async for chunk in text:
            yield self._clean_text_for_speech(chunk)

    async for frame in Agent.default.tts_node(
        self,
        cleaned_text(),
        model_settings,
    ):
        yield frame
```

The exact imports and return annotation must match the locked SDK. If the SDK
uses a different supported transform hook, use that hook and add a test proving
the processed text is the text received by TTS.

Minimum preprocessing tests:

- removes `[pause]`, `<break>`, and other unsupported control text;
- preserves ordinary punctuation and contractions;
- handles chunks split across the async stream;
- never changes URLs, email addresses, numbers, or tool results;
- does not call the provider or require credentials.

## Task 6: Validate identity and rendered speech

### Automated checks

- Search all active prompt, fallback, and knowledge sources for forbidden
  identity phrases.
- Test direct questions: "Who are you?", "Are you Chris?", and "Whose
  experience is that?"
- Test a Chris-related question that triggers RAG and confirm retrieved text
  cannot override ACE's identity.
- Assert `.env.example`, code defaults, and deployment configuration agree.
- Prove the configured TTS parameters reach `AgentSession`.
- Prove any text transform is invoked before TTS.

### Rendered call checks

- Record the same script for every model/voice candidate.
- Listen through a phone-quality codec, not only local speakers.
- Measure first-audio latency from LiveKit metrics.
- Check proper nouns, numbers, URLs, interruptions, and a tool-call response.
- Confirm no control token is spoken aloud.
- Save the chosen recording, measurements, configuration, and reviewer decision
  as the implementation evidence packet.

## Completion gate

This plan is complete only when:

- the runtime installs from a lock;
- identity is consistent in prompt, fallback, class text, and RAG knowledge;
- configuration agrees across code, sample environment, and deployment;
- the text-to-TTS path is mechanically tested;
- offline gates and the opt-in live call pass;
- the selected voice is backed by saved rendered audio and measurements.

## References

- [LiveKit pipeline nodes and hooks](https://docs.livekit.io/agents/logic/nodes/)
- [LiveKit OpenAI TTS plugin](https://docs.livekit.io/agents/models/tts/openai/)
- [OpenAI create speech API](https://platform.openai.com/docs/api-reference/audio/createSpeech)
- Repository sources: `agent/config.py`, `agent/main.py`, `.env.example`,
  `persona/ace prompt`, `persona/knowledge.md`, and
  `agent/tools/knowledge.py`
