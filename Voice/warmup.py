"""Eager loading for Voice turn-path models (Whisper, sentiment, librosa JIT).

Started in a background thread at server import time (best-effort head start).
Introduction Processing gates on ``is_warm()`` so participants cannot reach Voice
until warm-up has finished (or been attempted — failures fall back to lazy load).
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_warmup_done = False
_librosa_warmed = False


def _warm_whisper() -> None:
    from .services import STT_BACKEND, _get_whisper_model

    if STT_BACKEND != 'whisper-local':
        return
    _get_whisper_model()


def _warm_sentiment() -> None:
    from .sentiment import _get_model

    _get_model()


def _warm_librosa() -> None:
    global _librosa_warmed

    import numpy as np
    import librosa

    from .acoustics import _FMIN, _FMAX

    sr = 16000
    y = np.zeros(sr * 2, dtype=np.float32)
    librosa.yin(y, fmin=_FMIN, fmax=_FMAX, sr=sr)
    _librosa_warmed = True


def warmup() -> None:
    """Load Whisper / sentiment / librosa JIT once per process (idempotent)."""
    global _warmup_done

    with _lock:
        if _warmup_done:
            return

        t0 = time.perf_counter()
        logger.info('Voice model warm-up starting')

        try:
            _warm_whisper()
        except Exception:
            logger.warning('Whisper warm-up failed (will lazy-load on first STT)', exc_info=True)

        try:
            _warm_sentiment()
        except Exception:
            logger.warning('Sentiment warm-up failed (will lazy-load on first T3 turn)', exc_info=True)

        try:
            _warm_librosa()
        except Exception:
            logger.warning('Librosa JIT warm-up failed (will compile on first T3 turn)', exc_info=True)

        _warmup_done = True
        logger.info('Voice model warm-up finished in %.1fs', time.perf_counter() - t0)


def is_warm() -> bool:
    """True once warm-up has completed (or was skipped for stub backends)."""
    return _warmup_done
