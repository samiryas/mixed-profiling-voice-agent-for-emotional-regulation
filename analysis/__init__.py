"""Offline data analysis & evaluation pipeline for the emotion-regulation voice study.

Turns the raw study exports — the oTree ``all_apps_wide`` CSV, the per-participant
Polar H10 HRV recordings (``participant_<code>_hrv_raw.csv``), and optionally the
Voice app's per-turn ``custom_export`` CSV — into scored, segmented, visualized,
stats-ready outputs:

- questionnaire scale scores (BFI-10, ERQ-10, WAI-SR, UEQ+, personalization check,
  perceived hallucination, VAS stress),
- a unified per-participant session timeline reconstructed from the app's own
  timestamps (HRV baseline, calibration, interview, Voice phases, recovery),
- HRV metrics (RMSSD/SDNN/mean HR) per timeline segment with artifact/BLE-gap
  handling, plus reactivity and recovery deltas against baseline,
- per-participant HTML reports with annotated plots, and cohort-level master CSVs
  and condition (T1/T2/T3) comparisons for the paper.

Deliberately oTree-free: only pandas/numpy/matplotlib (scipy optional, for p-values),
so it runs on any machine that has the exported CSVs.

Usage:  python -m analysis --wide <all_apps_wide.csv> --hrv-dir <dir> --out results/
"""
