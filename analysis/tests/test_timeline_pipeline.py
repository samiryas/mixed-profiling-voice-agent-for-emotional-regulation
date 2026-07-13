from datetime import datetime, timezone

from analysis.ingest import discover_hrv_files, load_wide_csv
from analysis.pipeline import analyze_participant, participant_row
from analysis.timeline import build_timeline

from . import fixtures
from .fixtures import (
    BASELINE_END,
    BASELINE_START,
    INTERVIEW_END,
    INTERVIEW_START,
    PHASE_DUR,
    RECOVERY_END,
    RECOVERY_START,
    VOICE_START,
    hrv_csv,
    wide_csv,
    wide_row,
)


def _utc(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def load_single(tmp_path, row_overrides=None):
    row = wide_row()
    row.update(row_overrides or {})
    return load_wide_csv(wide_csv(tmp_path, [row]))[0]


def test_timeline_segments(tmp_path):
    rec = load_single(tmp_path)
    segments, events = build_timeline(rec)
    by_name = {s.name: s for s in segments}

    assert by_name["hrv_baseline"].start == _utc(BASELINE_START)
    assert by_name["hrv_baseline"].end == _utc(BASELINE_END)
    assert by_name["hrv_recovery"].start == _utc(RECOVERY_START)
    assert by_name["hrv_recovery"].end == _utc(RECOVERY_END)

    # completed phases straight from the log
    for i, phase in enumerate(["checkin", "technique", "practice"]):
        seg = by_name[f"voice:{phase}"]
        assert seg.start == _utc(VOICE_START + i * PHASE_DUR)
        assert seg.duration_s == PHASE_DUR
        assert not seg.inferred

    # the in-progress final phase is reconstructed with an inferred end at recovery
    refl = by_name["voice:reflection"]
    assert refl.inferred
    assert refl.start == _utc(VOICE_START + 3 * PHASE_DUR)
    assert refl.end == _utc(RECOVERY_START)

    # voice_session spans first phase -> recovery start
    vs = by_name["voice_session"]
    assert vs.start == _utc(VOICE_START) and vs.end == _utc(RECOVERY_START)

    # interview span comes from Chat's own timestamps -- exact, not inferred
    interview = by_name["profiling_interview"]
    assert interview.start == _utc(INTERVIEW_START)
    assert interview.end == _utc(INTERVIEW_END)
    assert not interview.inferred

    names = [e.name for e in events]
    assert "vas_stress" in names and "evaluation_submitted" in names
    vas = next(e for e in events if e.name == "vas_stress")
    assert vas.meta["value"] == 4


def test_interview_falls_back_to_approximation_when_untimestamped(tmp_path):
    # older exports predate Chat.timestamp_interview_start/_end -- pipeline must
    # still produce a (coarser, inferred) interview segment rather than dropping it
    rec = load_single(tmp_path, {
        "Chat.1.player.timestamp_interview_start": "0",
        "Chat.1.player.timestamp_interview_end": "0",
    })
    segments, _ = build_timeline(rec)
    by_name = {s.name: s for s in segments}
    interview = by_name["profiling_interview"]
    assert interview.inferred
    assert interview.start == _utc(fixtures.ERQ_AT)
    assert interview.end == _utc(VOICE_START)


def test_dropout_without_recovery_still_builds(tmp_path):
    rec = load_single(tmp_path, {
        "Voice.1.player.timestamp_hrv_recovery_start": "0",
        "Voice.1.player.timestamp_hrv_recovery_end": "0",
    })
    segments, _ = build_timeline(rec)
    by_name = {s.name: s for s in segments}
    assert "hrv_recovery" not in by_name
    assert by_name["voice_session"].inferred  # end had to be derived


def test_hrv_discovery_and_segment_metrics(tmp_path):
    rec = load_single(tmp_path)

    # baseline calm (RMSSD 40), voice stressed (12), recovery rebound (30)
    def delta(epoch):
        if epoch < BASELINE_END:
            return 40.0
        if epoch < RECOVERY_START:
            return 12.0
        return 30.0

    hrv_csv(tmp_path, code=rec.participant_code, rmssd_scale_by_epoch=delta)
    files = discover_hrv_files(tmp_path)
    assert rec.participant_code in files

    res = analyze_participant(rec, files[rec.participant_code])
    seg = res.segment_metrics.set_index("segment")

    assert abs(seg.loc["hrv_baseline", "rmssd_ms"] - 40.0) < 1.5
    assert abs(seg.loc["voice_session", "rmssd_ms"] - 12.0) < 1.5
    assert abs(seg.loc["hrv_recovery", "rmssd_ms"] - 30.0) < 1.5

    row = participant_row(res)
    assert row["rmssd_delta_voice"] < -25  # clear stress reactivity
    assert -12 < row["rmssd_delta_recovery"] < -7  # partial recovery
    assert row["condition"] == "T2"
    assert row["voice_user_turns"] == 3 and row["voice_agent_turns"] == 3
    assert row["phases_completed"] == 3 and row["phases_forced"] == 1


def test_participant_without_hrv(tmp_path):
    rec = load_single(tmp_path)
    res = analyze_participant(rec, None)
    row = participant_row(res)
    assert row["has_hrv"] is False
    assert "rmssd_delta_voice" not in row or row["rmssd_delta_voice"] is None
    assert row["wai_total"] == 5.0  # questionnaire scoring unaffected
