"""Unit tests for the Voice phase-control logic (advance_decision / extract_advance_flag).

These exercise the pure phase machinery without the oTree runtime. Run from the repo root:

    python3 -m Voice.tests.test_phase_control     # stdlib, no pytest needed
    pytest Voice/tests/test_phase_control.py       # also works if pytest is installed
"""
import importlib.util
import os
import pathlib
import sys

# Load Voice/prompts.py directly by path so the test does not import the Voice package
# __init__ (which pulls in the oTree runtime). prompts.py has no relative imports, so this
# gives us the pure phase-control logic in isolation. Its only dependency is `settings`, so
# the repo root must be importable.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PROMPTS_PATH = pathlib.Path(__file__).resolve().parents[1] / "prompts.py"
_spec = importlib.util.spec_from_file_location("voice_prompts_under_test", _PROMPTS_PATH)
_prompts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prompts)

advance_decision = _prompts.advance_decision
phase_config = _prompts.phase_config
extract_advance_flag = _prompts.extract_advance_flag
PHASES = _prompts.PHASES

# Same isolation trick for services.py (the readiness-judge parser).
_SERVICES_PATH = pathlib.Path(__file__).resolve().parents[1] / "services.py"
_sspec = importlib.util.spec_from_file_location("voice_services_under_test", _SERVICES_PATH)
_services = importlib.util.module_from_spec(_sspec)
_sspec.loader.exec_module(_services)

_parse_met = _services._parse_met

CHECKIN = 0        # min_turns=2, max_turns=6, max_seconds=240
REFLECTION = len(PHASES) - 1


def test_flag_ignored_before_turn_floor():
    # model wants to advance but the turn floor (min_turns) is not met yet -> stay
    advance, reason = advance_decision(CHECKIN, turns=1, elapsed_seconds=10, wants_advance=True)
    assert advance is False and reason == ""


def test_flag_honoured_once_turn_floor_met():
    advance, reason = advance_decision(CHECKIN, turns=2, elapsed_seconds=10, wants_advance=True)
    assert advance is True and reason == "flag"


def test_no_flag_no_advance_below_ceiling():
    advance, reason = advance_decision(CHECKIN, turns=4, elapsed_seconds=10, wants_advance=False)
    assert advance is False and reason == ""


def test_turn_ceiling_forces_advance_without_flag():
    cfg = phase_config(CHECKIN)
    advance, reason = advance_decision(
        CHECKIN, turns=cfg.max_turns, elapsed_seconds=1, wants_advance=False)
    assert advance is True and reason == "forced"


def test_time_ceiling_forces_advance_without_flag():
    cfg = phase_config(CHECKIN)
    # a single very long turn is still capped by the wall-clock ceiling
    advance, reason = advance_decision(
        CHECKIN, turns=1, elapsed_seconds=cfg.max_seconds + 1, wants_advance=False)
    assert advance is True and reason == "forced"


def test_ceiling_beats_flag_reason():
    cfg = phase_config(CHECKIN)
    advance, reason = advance_decision(
        CHECKIN, turns=cfg.max_turns, elapsed_seconds=1, wants_advance=True)
    assert advance is True and reason == "forced"


def test_last_phase_still_advances_so_session_can_end():
    # reflection must be able to advance (the caller turns that into session_done)
    cfg = phase_config(REFLECTION)
    advance, reason = advance_decision(
        REFLECTION, turns=cfg.max_turns, elapsed_seconds=1, wants_advance=False)
    assert advance is True and reason == "forced"


def test_fast_phases_env_collapses_bounds():
    os.environ["VOICE_FAST_PHASES"] = "1"
    try:
        cfg = phase_config(CHECKIN)
        assert cfg.min_turns == 1 and cfg.max_turns == 2 and cfg.max_seconds == 8
        advance, reason = advance_decision(CHECKIN, turns=1, elapsed_seconds=0, wants_advance=True)
        assert advance is True and reason == "flag"
    finally:
        del os.environ["VOICE_FAST_PHASES"]


def test_extract_advance_flag_strips_token():
    clean, wants = extract_advance_flag('That sounds hard.\n{"ready_to_advance": true}')
    assert wants is True and "ready_to_advance" not in clean and clean == "That sounds hard."


def test_extract_advance_flag_tolerates_code_fence():
    clean, wants = extract_advance_flag('Okay.\n```json\n{"ready_to_advance": true}\n```')
    assert wants is True and "ready_to_advance" not in clean and "`" not in clean


def test_extract_advance_flag_absent():
    clean, wants = extract_advance_flag("Let's keep going.")
    assert wants is False and clean == "Let's keep going."


def test_harmony_channel_leak_is_stripped_and_detected():
    # gpt-oss appends a developer-directed commentary channel to carry the flag; LM Studio
    # hands it back raw. The channel scaffolding must not reach the participant, and readiness
    # must still be detected. (Real transcript reported during a pilot run.)
    raw = (
        "When you think back over the past week, what comes up when you wake late?"
        "<|channel|>commentary to=developer <|constrain|>json<|message|>"
        '{"ready_to_advance": true}'
    )
    clean, wants = extract_advance_flag(raw)
    assert wants is True
    assert "<|" not in clean and "channel" not in clean and "developer" not in clean
    assert clean == "When you think back over the past week, what comes up when you wake late?"


def test_harmony_channel_leak_detected_even_if_json_truncated():
    # the channel header alone (JSON cut off) still signals readiness and is scrubbed
    raw = "That makes sense.<|channel|>commentary to=developer <|constrain|>json<|message|>"
    clean, wants = extract_advance_flag(raw)
    assert wants is True and clean == "That makes sense."


def test_stray_harmony_tokens_are_removed_without_advancing():
    clean, wants = extract_advance_flag("Take a breath.<|end|>")
    assert wants is False and clean == "Take a breath."


def test_reformatted_flag_variant_detected():
    clean, wants = extract_advance_flag("Okay.\nready_to_advance = true")
    assert wants is True and "ready_to_advance" not in clean and clean == "Okay."


# ----- readiness-judge parser (Option B) ---------------------------------------

def test_parse_met_strict_json():
    assert _parse_met('{"met": true}') is True
    assert _parse_met('{"met": false}') is False


def test_parse_met_tolerates_reformatting_and_junk():
    assert _parse_met('Sure — {"met": true}') is True
    assert _parse_met('met = false') is False
    assert _parse_met('"met":"true"') is True


def test_parse_met_survives_harmony_wrapping():
    # even if the judge model leaks channel tokens, the verdict is recoverable
    assert _parse_met('<|channel|>final<|message|>{"met": true}') is True


def test_parse_met_lone_boolean_fallback():
    assert _parse_met("true") is True
    assert _parse_met("false") is False


def test_parse_met_unparseable_returns_none():
    assert _parse_met("") is None
    assert _parse_met("I am not sure, both true and false apply") is None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
