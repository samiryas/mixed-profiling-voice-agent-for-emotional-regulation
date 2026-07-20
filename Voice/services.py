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
import re
from os import environ

from settings import LANG

logger = logging.getLogger(__name__)

STT_BACKEND = environ.get('VOICE_STT_BACKEND', 'stub')
LLM_BACKEND = environ.get('VOICE_LLM_BACKEND', 'stub')
TTS_BACKEND = environ.get('VOICE_TTS_BACKEND', 'stub')

_PROFILE_MARKERS = (
    'Teilnehmerprofil (personalisieren Sie darauf):',
    'Participant profile (personalize to this person):',
)


# ===== STT =====================================================================

async def transcribe(audio_bytes: bytes) -> str:
    if STT_BACKEND == 'whisper-local':
        return await _transcribe_faster_whisper(audio_bytes)
    # stub: the real audio is still captured and saved upstream — only the
    # transcription is faked, so the turn loop runs without any model.
    if LANG == 'de':
        return '[Stub-Transkript] (VOICE_STT_BACKEND=whisper-local setzen für faster-whisper)'
    return '[stub transcript] (set VOICE_STT_BACKEND=whisper-local to use faster-whisper)'


_WHISPER_MODEL = None


def _get_whisper_model():
    """Lazy singleton for faster-whisper (shared by STT and warm-up)."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel(
            environ.get('WHISPER_MODEL', 'base'), device='cpu', compute_type='int8',
        )
    return _WHISPER_MODEL


async def _transcribe_faster_whisper(audio_bytes: bytes) -> str:
    """Target STT (design D14): faster-whisper, runs locally so audio never
    leaves the lab. Requires `faster-whisper` to be installed."""
    def _run():
        import io
        segments, _ = _get_whisper_model().transcribe(
            io.BytesIO(audio_bytes), language=LANG,
        )
        return ' '.join(s.text for s in segments).strip()

    return await asyncio.to_thread(_run)


# ===== LLM =====================================================================

async def generate_reply(messages: list, *, system_prompt: str) -> str:
    if LLM_BACKEND in ('kit', 'openai'):
        return await _generate_reply_kit(messages, system_prompt)
    # stub: echo whether a profile reached the system prompt, to prove the
    # profile-by-PID wiring and condition handling end-to-end.
    personalized = (
        'personalized' if any(m in system_prompt for m in _PROFILE_MARKERS) else 'generic'
    )
    if LANG == 'de':
        return (
            f'[Stub-Bot-Antwort | {personalized}] Danke fürs Teilen. '
            f'Was ging Ihnen in dem Moment durch den Kopf?'
        )
    return (
        f'[stub bot reply | {personalized}] Thanks for sharing. '
        f'What was going through your mind in that moment?'
    )


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


# ----- phase-readiness judge (Option B) ----------------------------------------

# Parse a {"met": true|false} verdict; tolerant of reformatting and of harmony-model junk
# around it (we search anywhere in the content rather than requiring clean JSON).
_MET_RE = re.compile(r'"?met"?\s*[:=]\s*"?(true|false)"?', re.IGNORECASE)


def _parse_met(content: str) -> bool | None:
    """Extract the judge's boolean verdict from raw model content. None if unparseable."""
    if not content:
        return None
    m = _MET_RE.search(content)
    if m:
        return m.group(1).lower() == 'true'
    # last resort: a lone true/false with no ambiguity
    low = content.lower()
    has_true, has_false = 'true' in low, 'false' in low
    if has_true and not has_false:
        return True
    if has_false and not has_true:
        return False
    return None


async def judge_phase_goal(system_prompt: str, messages: list) -> bool | None:
    """Out-of-band readiness judge: a second, structured LLM call that decides whether the
    current phase's goal is met, kept entirely separate from the coaching reply so the spoken
    text never carries a control signal.

    Returns True/False, or None when the judge is unavailable (stub backend) or the call/parse
    fails -- the caller then falls back to the inline flag, and the phase ceiling always applies.
    """
    if LLM_BACKEND not in ('kit', 'openai'):
        return None
    try:
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
            temperature=0,
        )
        return _parse_met(resp.choices[0].message.content or '')
    except Exception:
        logger.exception('phase-goal judge failed (falling back to inline flag)')
        return None


# ===== TTS =====================================================================

async def synthesize(
    text: str,
    *,
    voice_id: str,
    voice_settings: dict | None = None,
) -> bytes:
    if TTS_BACKEND == 'elevenlabs':
        return await asyncio.to_thread(
            _synthesize_elevenlabs, text, voice_id, voice_settings,
        )
    # stub: no audio bytes -> the client shows the transcript only.
    return b''


def _elevenlabs_tts_request(text: str, voice_id: str, voice_settings: dict | None):
    """POST to ElevenLabs TTS; returns the requests Response (caller checks .ok)."""
    import requests

    key = (environ.get('ELEVENLABS_KEY') or '').strip()
    payload = {'text': text, 'model_id': 'eleven_multilingual_v2'}
    if voice_settings:
        payload['voice_settings'] = voice_settings
    return requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
        headers={'xi-api-key': key, 'Content-Type': 'application/json'},
        json=payload,
        params={'output_format': 'mp3_44100_128'},
        timeout=30,
    )


def _synthesize_elevenlabs(
    text: str,
    voice_id: str,
    voice_settings: dict | None = None,
) -> bytes:
    """High-quality TTS (design D13). Receives only generated text — no
    participant audio or profile data leaves KIT infrastructure.

    When ``voice_settings`` is provided and the API rejects it (unsupported
    parameter, model quirk, etc.), retries once with default voice settings
    (fail-open — same pattern as sentiment/acoustics).
    """
    from .tts_settings import default_voice_settings

    resp = _elevenlabs_tts_request(text, voice_id, voice_settings)
    if not resp.ok and voice_settings:
        logger.warning(
            'ElevenLabs TTS failed with state voice_settings %s (fail-open -> defaults): %s',
            voice_settings, resp.text,
        )
        fallback = default_voice_settings()
        resp = _elevenlabs_tts_request(text, voice_id, fallback)
        if not resp.ok:
            logger.warning(
                'ElevenLabs TTS failed with default voice_settings (fail-open -> no settings): %s',
                resp.text,
            )
            resp = _elevenlabs_tts_request(text, voice_id, None)

    if not resp.ok:
        logger.error('ElevenLabs TTS %s for voice %s: %s',
                     resp.status_code, voice_id, resp.text)
    resp.raise_for_status()
    return resp.content
