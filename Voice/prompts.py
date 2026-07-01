"""System-prompt assembly and phase control for the Voice session.

Builds the layered system prompt (persona + AI disclosure -> condition-based profile block ->
current phase block -> pacing/advance instruction) from the version-controlled templates under
Voice/prompts/<lang>/, and parses the LLM's {"ready_to_advance": true} readiness flag.

Personalization beyond profile injection (Big Five delivery notes, ERQ DEEPEN/INTRODUCE framing)
is intentionally left as seams here -- see delivery_notes_from_profile() and erq_framing(). Their
thresholds are a separate task ("Finalize personalization thresholds", design ref D17).
"""
import re
from os import environ

from utils.promting import renderPrompt

# Phase name + default minimum duration in seconds (design ref D18).
PHASES = [
    ("checkin", 90),
    ("technique", 120),
    ("practice", 180),
    ("reflection", 60),
]

LANG = environ.get("VOICE_LANG", "en")

_ADVANCE_RE = re.compile(r'\{\s*"ready_to_advance"\s*:\s*true\s*\}', re.IGNORECASE)


def _prompt_dir() -> str:
    return f"Voice/prompts/{LANG}"


def phase_name(phase_index: int) -> str:
    return PHASES[phase_index][0]


def is_last_phase(phase_index: int) -> bool:
    return phase_index >= len(PHASES) - 1


def min_duration(phase_index: int) -> float:
    """Minimum seconds to stay in a phase before an advance flag is honoured (D18).

    Overridable per phase via VOICE_PHASE_MIN_<NAME>; VOICE_FAST_PHASES=1 collapses all
    durations for quick manual testing (NFR9 -- externalized config).
    """
    if environ.get("VOICE_FAST_PHASES") == "1":
        return 2.0
    name, default = PHASES[phase_index]
    return float(environ.get(f"VOICE_PHASE_MIN_{name.upper()}", default))


# ----- personalization seams (return neutral defaults for now) -----------------

def delivery_notes_from_profile(profile: str) -> str:
    """SEAM: translate Big Five scores into behavioural delivery notes (design ref D17).
    TODO(Finalize personalization thresholds): map BFI-10 -> concrete instructions."""
    return ""


def erq_framing(condition: str, profile: str) -> str:
    """SEAM: choose reappraisal framing from the ERQ -- REAPPRAISAL_DEEPEN vs INTRODUCE
    (design ref D4-rev). TODO(Finalize personalization thresholds): map ERQ scores -> framing.
    Returns neutral framing until thresholds are set."""
    return ""


# ----- prompt assembly ---------------------------------------------------------

def build_system_prompt(
    profile: str,
    condition: str,
    phase_index: int,
    emotional_state: str | None = None,
) -> str:
    """Assemble the layered system prompt for the current turn.

    `emotional_state` is T3-only: when provided (i.e. on a state transition), the
    matching state instruction block is appended after the existing layers.
    """
    d = _prompt_dir()
    persona = renderPrompt(f"{d}/persona.txt", {})

    # T1 withholds the personal profile from the agent; T2/T3 inject it.
    if condition != "T1" and profile:
        profile_block = "Participant profile (personalize to this person):\n" + profile
    else:
        profile_block = renderPrompt(f"{d}/generic_profile.txt", {})

    phase_ctx = {
        "framing": erq_framing(condition, profile),
        "delivery_notes": delivery_notes_from_profile(profile),
    }
    phase_block = renderPrompt(f"{d}/phase_{phase_name(phase_index)}.txt", phase_ctx)
    advance = renderPrompt(f"{d}/advance.txt", {})

    # T3 only: append the state instruction on transition (trigger-only adaptation).
    state_block = ""
    if emotional_state is not None:
        state_block = _load_state_block(emotional_state)

    return "\n\n".join(
        b.strip() for b in (persona, profile_block, phase_block, advance, state_block) if b.strip()
    )


def _load_state_block(state: str) -> str:
    """Load Voice/prompts/<LANG>/state_<state>.txt. Return "" if missing (fail-open)."""
    try:
        return renderPrompt(f"{_prompt_dir()}/state_{state}.txt", {})
    except Exception:
        return ""


# ----- readiness flag ----------------------------------------------------------

def extract_advance_flag(text: str):
    """Strip a {"ready_to_advance": true} token from the reply.

    Returns (clean_text, wants_advance). The flag must never reach TTS or the transcript
    (D18/FR22). Tolerates surrounding whitespace and code fences.
    """
    raw = text or ""
    wants_advance = bool(_ADVANCE_RE.search(raw))
    clean = _ADVANCE_RE.sub("", raw)
    # drop any now-empty code fence the model may have wrapped the flag in
    clean = re.sub(r"```[a-zA-Z]*\s*```", "", clean).replace("```", "")
    return clean.strip(), wants_advance
