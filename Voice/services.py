"""Swappable STT / LLM / TTS adapters for the Voice session.

The scaffold ships local STUBS so the full record -> STT -> LLM -> TTS ->
playback loop runs end-to-end with no API keys or models installed. Each
backend is selected independently via an env var and defaults to the stub:

    VOICE_STT_BACKEND = stub | whisper-local   (target per design D14: faster-whisper, GDPR-local)
    VOICE_LLM_BACKEND = stub | kit             (KIT Toolbox gpt-oss:120b, OpenAI-compatible endpoint)
    VOICE_TTS_BACKEND = stub | elevenlabs

Real backends import their heavy dependencies lazily, so importing this module
never requires faster-whisper / openai / requests unless a real backend is
actually selected. Wiring each real backend is its own downstream task
(STT, KIT LLM, TTS); this file is the seam they plug into.
"""
import asyncio
import logging
from os import environ

logger = logging.getLogger(__name__)

STT_BACKEND = environ.get('VOICE_STT_BACKEND', 'stub')
LLM_BACKEND = environ.get('VOICE_LLM_BACKEND', 'stub')
TTS_BACKEND = environ.get('VOICE_TTS_BACKEND', 'stub')


# ===== STT =====================================================================

async def transcribe(audio_bytes: bytes) -> str:
    if STT_BACKEND == 'whisper-local':
        return await _transcribe_faster_whisper(audio_bytes)
    # stub: the real audio is still captured and saved upstream — only the
    # transcription is faked, so the turn loop runs without any model.
    return '[stub transcript] (set VOICE_STT_BACKEND=whisper-local to use faster-whisper)'


_WHISPER_MODEL = None


async def _transcribe_faster_whisper(audio_bytes: bytes) -> str:
    """Target STT (design D14): faster-whisper, runs locally so audio never
    leaves the lab. Requires `faster-whisper` to be installed."""
    def _run():
        global _WHISPER_MODEL
        import io
        from faster_whisper import WhisperModel
        if _WHISPER_MODEL is None:
            _WHISPER_MODEL = WhisperModel(
                environ.get('WHISPER_MODEL', 'base'), device='cpu', compute_type='int8',
            )
        segments, _ = _WHISPER_MODEL.transcribe(io.BytesIO(audio_bytes))
        return ' '.join(s.text for s in segments).strip()

    return await asyncio.to_thread(_run)


# ===== LLM =====================================================================

async def generate_reply(messages: list, *, system_prompt: str) -> str:
    if LLM_BACKEND in ('kit', 'openai'):
        return await _generate_reply_kit(messages, system_prompt)
    # stub: echo whether a profile reached the system prompt, to prove the
    # profile-by-PID wiring and condition handling end-to-end.
    personalized = 'personalized' if 'User profile' in system_prompt else 'generic'
    return (f'[stub bot reply | {personalized}] Thanks for sharing. '
            f'What was going through your mind in that moment?')


async def _generate_reply_kit(messages: list, system_prompt: str) -> str:
    """KIT Toolbox gpt-oss:120b via the OpenAI-compatible API (local, GDPR)."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=environ.get('OPENAI_KEY', 'unused'),
        base_url=environ.get('OPENAI_URL'),
    )
    chat = [{'role': 'system', 'content': system_prompt}]
    for m in messages:
        role = 'assistant' if m.get('sender') == 'assistant' else 'user'
        chat.append({'role': role, 'content': m.get('text', '')})
    resp = await client.chat.completions.create(
        model=environ.get('OPENAI_MODEL', 'gpt-oss:120b'),
        messages=chat,
    )
    return (resp.choices[0].message.content or '').strip()


# ===== TTS =====================================================================

async def synthesize(text: str, *, voice_id: str) -> bytes:
    if TTS_BACKEND == 'elevenlabs':
        return await asyncio.to_thread(_synthesize_elevenlabs, text, voice_id)
    # stub: no audio bytes -> the client shows the transcript only.
    return b''


def _synthesize_elevenlabs(text: str, voice_id: str) -> bytes:
    """High-quality TTS (design D13). Receives only generated text — no
    participant audio or profile data leaves KIT infrastructure."""
    import requests
    key = (environ.get('ELEVENLABS_KEY') or '').strip()
    resp = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
        headers={'xi-api-key': key, 'Content-Type': 'application/json'},
        json={'text': text, 'model_id': 'eleven_multilingual_v2'},
        params={'output_format': 'mp3_44100_128'},
        timeout=30,
    )
    if not resp.ok:
        # ElevenLabs sends the real reason (quota_exceeded,
        # detected_unusual_activity, needs_billing, ...) in the body — surface it.
        logger.error('ElevenLabs TTS %s for voice %s: %s',
                     resp.status_code, voice_id, resp.text)
    resp.raise_for_status()
    return resp.content
