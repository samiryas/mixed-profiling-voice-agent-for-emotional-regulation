"""T3 emotional-state -> ElevenLabs voice_settings mapping (FR13/FR14).

Maps the persisted 3-state classifier output to deterministic ElevenLabs
``voice_settings`` (stability, similarity_boost, speed). Values are env-var
overridable for pilot tuning — see .env.example.

IMPORTANT (NFR3): T1/T2 must never call ``voice_settings_for_emotional_state``.
Condition gating lives exclusively in ``Voice/__init__.py`` (``condition == 'T3'``).
"""
import os

STATES = ("calm", "moderate_distress", "high_distress")

# Pilot defaults when env vars are unset — distress = higher stability, lower speed.
_STABILITY_DEFAULTS = {
    "calm": 0.5,
    "moderate_distress": 0.65,
    "high_distress": 0.75,
}
_SPEED_DEFAULTS = {
    "calm": 1.0,
    "moderate_distress": 0.92,
    "high_distress": 0.85,
}
_SIMILARITY_DEFAULT = 0.75


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def default_voice_settings() -> dict:
    """Fixed ElevenLabs voice_settings for T1/T2 and T3 fail-open fallback."""
    return {
        "stability": _float_env("VOICE_TTS_STABILITY_DEFAULT", 0.5),
        "similarity_boost": _float_env("VOICE_TTS_SIMILARITY_DEFAULT", _SIMILARITY_DEFAULT),
        "speed": _float_env("VOICE_TTS_SPEED_DEFAULT", 1.0),
    }


def voice_settings_for_emotional_state(state: str) -> dict:
    """Deterministic state -> voice_settings. Unknown state uses the calm mapping."""
    if state not in STATES:
        state = "calm"
    suffix = state.upper()
    return {
        "stability": _float_env(
            f"VOICE_TTS_STABILITY_{suffix}",
            _STABILITY_DEFAULTS[state],
        ),
        "similarity_boost": _float_env(
            f"VOICE_TTS_SIMILARITY_{suffix}",
            _SIMILARITY_DEFAULT,
        ),
        "speed": _float_env(
            f"VOICE_TTS_SPEED_{suffix}",
            _SPEED_DEFAULTS[state],
        ),
    }
