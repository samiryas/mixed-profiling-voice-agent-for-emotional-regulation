"""Acoustic feature extraction and baseline deltas for T3 live adaptation (FR13/FR14).

Extracts pitch / speech-rate / pause-rate from a saved turn recording in a single
librosa pass, compares them against the participant's calibration baseline (cached
in memory per session), and returns proportional deltas for the state classifier.

Browser recordings are WebM/Opus; librosa/soundfile cannot read those directly, so
we decode via ffmpeg (bundled imageio-ffmpeg binary, or FFMPEG_PATH / system PATH).
"""
import logging
import os
import shutil
import subprocess
import tempfile
from glob import glob

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Calibration baselines, cached per session: {participant_code: features_dict}
_baseline_cache: dict = {}

# librosa.yin pitch search range (Hz) — roughly the human speaking voice band.
_FMIN = 65.0
_FMAX = 400.0

# Browser / MediaRecorder formats that need ffmpeg decoding.
_FFMPEG_EXTS = {".webm", ".ogg", ".opus", ".mp4", ".m4a", ".mkv"}


def _find_ffmpeg() -> str | None:
    """Resolve ffmpeg: FFMPEG_PATH env -> PATH -> imageio-ffmpeg bundle -> WinGet shim."""
    from os import environ

    env_path = (environ.get("FFMPEG_PATH") or "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    if path := shutil.which("ffmpeg"):
        return path

    try:
        import imageio_ffmpeg
        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.isfile(bundled):
            return bundled
    except Exception:
        pass

    # WinGet Gyan.FFmpeg often adds a user-level shim link.
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        winget_link = os.path.join(local_app, "Microsoft", "WinGet", "Links", "ffmpeg.EXE")
        if os.path.isfile(winget_link):
            return winget_link

    return None


def _decode_with_ffmpeg(audio_path: str, ffmpeg: str):
    """Decode any audio file to mono WAV via ffmpeg, then load with librosa."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            [ffmpeg, "-y", "-i", audio_path, "-ac", "1", "-ar", "16000", tmp_path],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")[:500]
            raise RuntimeError(f"ffmpeg decode failed: {stderr}")
        return librosa.load(tmp_path, sr=None, mono=True)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _load_audio(audio_path: str):
    """Load mono audio as (y, sr). WebM/Opus always goes through ffmpeg."""
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in _FFMPEG_EXTS:
        ffmpeg = _find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError(
                "Cannot decode WebM/Opus audio (ffmpeg not found). "
                "Install imageio-ffmpeg (pip install imageio-ffmpeg) or set FFMPEG_PATH."
            )
        return _decode_with_ffmpeg(audio_path, ffmpeg)

    try:
        return librosa.load(audio_path, sr=None, mono=True)
    except Exception:
        ffmpeg = _find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("Cannot decode audio (ffmpeg not found).") from None
        return _decode_with_ffmpeg(audio_path, ffmpeg)


def extract_features(audio_path: str) -> dict:
    """Extract pitch_mean, speech_rate and pause_rate from one audio file.

    A single librosa pass: `librosa.effects.split()` produces the voiced-segment
    intervals that feed BOTH speech_rate and pause_rate (no second segmentation).

    Returns {"pitch_mean": float, "speech_rate": float, "pause_rate": float}
      - pitch_mean:  mean F0 over voiced frames via librosa.yin()
      - speech_rate: voiced fraction = voiced_samples / total_samples
      - pause_rate:  number of silent intervals / total duration (seconds)
    """
    y, sr = _load_audio(audio_path)

    total_samples = len(y)
    if total_samples == 0 or sr == 0:
        return {"pitch_mean": 0.0, "speech_rate": 0.0, "pause_rate": 0.0}

    duration_s = total_samples / float(sr)

    # one segmentation pass shared by speech_rate AND pause_rate
    intervals = librosa.effects.split(y, top_db=30)

    voiced_samples = int(sum(end - start for start, end in intervals))
    speech_rate = voiced_samples / float(total_samples)

    # silent intervals = gaps between/around the voiced intervals
    num_voiced = len(intervals)
    if num_voiced == 0:
        num_silences = 1 if total_samples > 0 else 0
    else:
        num_silences = num_voiced - 1
        if intervals[0][0] > 0:
            num_silences += 1
        if intervals[-1][1] < total_samples:
            num_silences += 1
    pause_rate = num_silences / duration_s if duration_s > 0 else 0.0

    # mean F0 over voiced frames only
    pitch_mean = 0.0
    if voiced_samples > 0:
        voiced_audio = np.concatenate([y[start:end] for start, end in intervals])
        try:
            f0 = librosa.yin(voiced_audio, fmin=_FMIN, fmax=_FMAX, sr=sr)
            f0 = f0[np.isfinite(f0)]
            if f0.size > 0:
                pitch_mean = float(np.mean(f0))
        except Exception:
            pitch_mean = 0.0

    return {
        "pitch_mean": pitch_mean,
        "speech_rate": speech_rate,
        "pause_rate": pause_rate,
    }


def get_baseline(
    participant_code: str,
    audio_dir: str = "_static/Voice/recordings",
    calibration_path: str | None = None,
) -> dict | None:
    """Load and cache a participant's calibration baseline.

    Resolution order:
      1. Explicit `calibration_path` (from participant.vars, set during Introduction)
      2. Glob {audio_dir}/{participant_code}_calibration.*

    Returns None (fail-open) when no file exists or feature extraction fails.
    """
    if participant_code in _baseline_cache:
        return _baseline_cache[participant_code]

    path = calibration_path
    if path and not os.path.isabs(path):
        path = os.path.join(audio_dir, os.path.basename(path))
    if not path or not os.path.isfile(path):
        matches = glob(f"{audio_dir}/{participant_code}_calibration.*")
        if not matches:
            logger.info("No calibration file for %s in %s", participant_code, audio_dir)
            return None
        path = matches[0]

    try:
        features = extract_features(path)
    except Exception:
        logger.exception(
            "Calibration baseline extraction failed for %s (path=%s, fail-open)",
            participant_code, path,
        )
        return None

    logger.info(
        "Calibration baseline loaded for %s: pitch=%.1f speech_rate=%.3f pause_rate=%.3f",
        participant_code, features["pitch_mean"], features["speech_rate"], features["pause_rate"],
    )
    _baseline_cache[participant_code] = features
    return features


def compute_deltas(turn_features: dict, baseline_features: dict) -> dict:
    """Proportional delta (turn - baseline) / baseline per feature.

    Returns {"pitch_delta", "speech_rate_delta", "pause_rate_delta"}. A baseline of
    0 for any feature yields a 0.0 delta for that feature (no division by zero).
    """
    def _delta(turn_key: str) -> float:
        base = baseline_features.get(turn_key, 0.0)
        if not base:
            return 0.0
        return (turn_features.get(turn_key, 0.0) - base) / base

    return {
        "pitch_delta": _delta("pitch_mean"),
        "speech_rate_delta": _delta("speech_rate"),
        "pause_rate_delta": _delta("pause_rate"),
    }
