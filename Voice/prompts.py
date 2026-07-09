"""System-prompt assembly and phase control for the Voice session.

Builds the layered system prompt (persona + AI disclosure -> condition-based profile block ->
current phase block -> pacing/advance instruction) from the version-controlled templates under
Voice/prompts/<lang>/, and parses the LLM's {"ready_to_advance": true} readiness flag.

Personalization beyond profile injection (Big Five delivery notes, ERQ DEEPEN/INTRODUCE framing)
is intentionally left as seams here -- see delivery_notes_from_profile() and erq_framing(). Their
thresholds are a separate task ("Finalize personalization thresholds", design ref D17).
"""
import re
from dataclasses import dataclass
from os import environ

from settings import LANG

# NOTE: renderPrompt (utils.promting) is imported lazily inside the functions that render
# templates. It pulls in oTree models transitively, so keeping it out of module scope lets the
# pure phase-control logic (advance_decision, phase_config, extract_advance_flag) be imported and
# unit-tested without the full oTree runtime.


@dataclass(frozen=True)
class PhaseCfg:
    """Advancement bounds for one phase (design ref D18).

    Advancement is gated on *turns* (conversational depth), not wall-clock, so a phase
    tracks the actual exchange rather than idle time:
      - min_turns   : the readiness flag is ignored before this many exchanges (a floor
                      against the model bailing after one turn).
      - max_turns   : force-advance at/after this many exchanges even without the flag.
      - max_seconds : hard wall-clock ceiling so a stalled or runaway phase can never hang
                      the session (a single very long turn is still capped here).
    """
    name: str
    min_turns: int
    max_turns: int
    max_seconds: float


PHASES = [
    PhaseCfg("checkin",    min_turns=2, max_turns=6, max_seconds=240),
    PhaseCfg("technique",  min_turns=2, max_turns=6, max_seconds=240),
    PhaseCfg("practice",   min_turns=3, max_turns=8, max_seconds=360),
    PhaseCfg("reflection", min_turns=1, max_turns=4, max_seconds=180),
]

# The strict token we instruct the model to append.
_ADVANCE_JSON_RE = re.compile(r'\{\s*"ready_to_advance"\s*:\s*true\s*\}', re.IGNORECASE)
# Tolerant readiness match — survives models that reformat the token (unquoted key, `=`, etc.).
_ADVANCE_RE = re.compile(r'"?ready_to_advance"?\s*[:=]\s*true', re.IGNORECASE)
# Harmony / channel control tokens that some local models (e.g. gpt-oss) leak into message
# content: <|channel|>, <|message|>, <|start|>, <|end|>, <|constrain|>, <|return|>, ...
_HARMONY_TOKEN_RE = re.compile(r'<\|[^>]*?\|>')
# A switch to a non-user-facing channel (commentary/analysis, often addressed to a developer or
# tool). Everything from that switch to the end of the reply is scaffolding, not speech.
_CHANNEL_SWITCH_RE = re.compile(
    r'<\|channel\|>\s*(?:commentary|analysis)\b.*\Z', re.IGNORECASE | re.DOTALL
)
# The developer-directed commentary channel gpt-oss opens solely to emit our JSON flag — we never
# ask the model for any other side-channel message, so its presence is itself a readiness signal
# (covers the case where the JSON payload gets truncated after the channel header).
_DEV_JSON_CHANNEL_RE = re.compile(
    r'channel\|>\s*commentary[^<]*?to\s*=\s*developer', re.IGNORECASE
)


def _prompt_dir() -> str:
    return f"Voice/prompts/{LANG}"


def phase_name(phase_index: int) -> str:
    return PHASES[phase_index].name


def is_last_phase(phase_index: int) -> bool:
    return phase_index >= len(PHASES) - 1


def phase_config(phase_index: int) -> PhaseCfg:
    """Resolve the phase's bounds, applying env overrides.

    VOICE_FAST_PHASES=1 collapses every phase for quick manual testing; individual bounds are
    overridable via VOICE_PHASE_{MIN_TURNS,MAX_TURNS,MAX_SECONDS}_<NAME> (NFR9 -- externalized
    config).
    """
    if environ.get("VOICE_FAST_PHASES") == "1":
        return PhaseCfg(phase_name(phase_index), min_turns=1, max_turns=2, max_seconds=8)
    cfg = PHASES[phase_index]
    up = cfg.name.upper()
    return PhaseCfg(
        cfg.name,
        min_turns=int(environ.get(f"VOICE_PHASE_MIN_TURNS_{up}", cfg.min_turns)),
        max_turns=int(environ.get(f"VOICE_PHASE_MAX_TURNS_{up}", cfg.max_turns)),
        max_seconds=float(environ.get(f"VOICE_PHASE_MAX_SECONDS_{up}", cfg.max_seconds)),
    )


def advance_decision(phase_index: int, turns: int, elapsed_seconds: float, wants_advance: bool):
    """Decide whether to leave the current phase this turn (design ref D18).

    Returns (should_advance, reason) where reason is "forced" (a ceiling was hit),
    "flag" (the model asked and the turn floor is met), or "" (stay).
    A ceiling always wins so a phase -- and the session -- can never hang.
    """
    cfg = phase_config(phase_index)
    if turns >= cfg.max_turns or elapsed_seconds >= cfg.max_seconds:
        return True, "forced"
    if wants_advance and turns >= cfg.min_turns:
        return True, "flag"
    return False, ""


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
    transition_from: str | None = None,
) -> str:
    """Assemble the layered system prompt for the current turn.

    Layers: persona -> session arc (where we are in the 4-phase plan) -> profile ->
    current phase -> transition note -> advance instruction -> state block.

    `transition_from` names the phase we just left; when set (i.e. the first turn of a new
    phase), a note is injected so the model acknowledges the shift rather than being handed a
    new instruction with no context (design ref D18).

    `emotional_state` is T3-only: when provided (i.e. on a state transition), the
    matching state instruction block is appended after the existing layers.
    """
    from utils.promting import renderPrompt

    d = _prompt_dir()
    persona = renderPrompt(f"{d}/persona.txt", {})

    # give the model a map of the whole arc so it can pace itself, not drive blind.
    arc = renderPrompt(f"{d}/session_arc.txt", {
        "position": phase_index + 1,
        "total": len(PHASES),
        "phase_list": ", ".join(p.name for p in PHASES),
        "current": phase_name(phase_index),
    })

    # T1 withholds the personal profile from the agent; T2/T3 inject it.
    if condition != "T1" and profile:
        profile_header = (
            "Teilnehmerprofil (personalisieren Sie darauf):\n" if LANG == "de"
            else "Participant profile (personalize to this person):\n"
        )
        profile_block = profile_header + profile
    else:
        profile_block = renderPrompt(f"{d}/generic_profile.txt", {})

    phase_ctx = {
        "framing": erq_framing(condition, profile),
        "delivery_notes": delivery_notes_from_profile(profile),
    }
    phase_block = renderPrompt(f"{d}/phase_{phase_name(phase_index)}.txt", phase_ctx)

    # first turn of a new phase: tell the model it just moved so it hands off naturally.
    transition_block = ""
    if transition_from:
        transition_block = renderPrompt(f"{d}/transition.txt", {
            "previous": transition_from,
            "current": phase_name(phase_index),
        })

    advance = renderPrompt(f"{d}/advance.txt", {})

    # T3 only: append the state instruction on transition (trigger-only adaptation).
    state_block = ""
    if emotional_state is not None:
        state_block = _load_state_block(emotional_state)

    return "\n\n".join(
        b.strip() for b in
        (persona, arc, profile_block, phase_block, transition_block, advance, state_block)
        if b.strip()
    )


def build_judge_prompt(phase_index: int) -> str:
    """System prompt for the out-of-band phase-readiness judge (Option B).

    Reuses the current phase block -- the single source of truth for that phase's "ready to move
    on" condition -- and asks for a strict JSON verdict. Deliberately separate from the coaching
    prompt so the spoken reply never carries a control signal (no more inline flag pollution/leak).
    """
    from utils.promting import renderPrompt

    d = _prompt_dir()
    phase_block = renderPrompt(
        f"{d}/phase_{phase_name(phase_index)}.txt",
        {"framing": "", "delivery_notes": ""},
    )
    return renderPrompt(f"{d}/judge.txt", {"phase_block": phase_block})


def _load_state_block(state: str) -> str:
    """Load Voice/prompts/<LANG>/state_<state>.txt. Return "" if missing (fail-open)."""
    from utils.promting import renderPrompt

    try:
        return renderPrompt(f"{_prompt_dir()}/state_{state}.txt", {})
    except Exception:
        return ""


# ----- readiness flag ----------------------------------------------------------

def extract_advance_flag(text: str):
    """Strip the readiness flag (and any leaked model scaffolding) from the reply.

    Returns (clean_text, wants_advance). Neither the flag nor any control tokens may reach TTS
    or the transcript (D18/FR22). Tolerant of:
      - the strict {"ready_to_advance": true} token, anywhere, with fences or whitespace;
      - reformatted variants (ready_to_advance = true, unquoted key, ...);
      - harmony / channel tokens some local models (gpt-oss) leak into content, e.g.
        `<|channel|>commentary to=developer <|constrain|>json<|message|>{"ready_to_advance": true}`.
    """
    raw = text or ""

    # readiness: the explicit flag, or the developer/json commentary channel gpt-oss opens only
    # to emit it (robust to the JSON payload being truncated after the channel header).
    wants_advance = bool(_ADVANCE_RE.search(raw) or _DEV_JSON_CHANNEL_RE.search(raw))

    # drop everything from a non-final channel switch onward (harmony scaffolding + the flag)
    clean = _CHANNEL_SWITCH_RE.sub("", raw)
    # belt-and-suspenders: remove the strict token, then any reformatted variant, if either
    # survived inside the final channel (strict first so its braces aren't left orphaned)
    clean = _ADVANCE_JSON_RE.sub("", clean)
    clean = _ADVANCE_RE.sub("", clean)
    # strip any stray harmony control tokens and now-empty code fences
    clean = _HARMONY_TOKEN_RE.sub("", clean)
    clean = re.sub(r"```[a-zA-Z]*\s*```", "", clean).replace("```", "")
    return clean.strip(), wants_advance
