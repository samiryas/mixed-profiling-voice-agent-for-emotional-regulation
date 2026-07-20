from analysis.ingest import ParticipantRecord
from analysis.scoring import score_participant

from .fixtures import wide_row


def rec(row_overrides=None) -> ParticipantRecord:
    row = wide_row()
    row.update(row_overrides or {})
    return ParticipantRecord(
        participant_code=row["participant.code"],
        session_code=row["session.code"],
        condition=row["Voice.1.player.condition"],
        raw=row,
    )


def test_bfi10_reverse_coding():
    # all raw 4 on a 5-point scale: reversed items count as 2 -> pair mean 3.0
    s = score_participant(rec())
    for trait in ("extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"):
        assert s[f"bfi_{trait}"] == 3.0


def test_bfi10_directional():
    # top-box extraversion: b5_0 (reserved, reversed) = 1, b5_5 (outgoing) = 5 -> 5.0
    s = score_participant(rec({
        "Introduction.1.player.b5_0": "1",
        "Introduction.1.player.b5_5": "5",
    }))
    assert s["bfi_extraversion"] == 5.0


def test_erq_subscales():
    s = score_participant(rec())
    assert s["erq_reappraisal"] == 6.0
    assert s["erq_suppression"] == 2.0


def test_wai_and_ueq_and_pers():
    s = score_participant(rec())
    assert s["wai_goal"] == s["wai_task"] == s["wai_bond"] == 5.0
    assert s["wai_total"] == 5.0
    assert s["ueq_behavior"] == s["ueq_quality"] == s["ueq_useful"] == 6.0
    # pers_3 = 2 reversed on 7-point -> 6 ; mean(6, 6, 6) = 6
    assert s["personalization"] == 6.0
    assert s["hallucination"] == 2.0
    assert s["vas_stress"] == 4


def test_missing_item_makes_scale_none():
    s = score_participant(rec({"Evaluation.1.player.wai_goal_2": ""}))
    assert s["wai_goal"] is None
    assert s["wai_total"] is None  # total requires all three subscales
    assert s["wai_task"] == 5.0  # others unaffected
