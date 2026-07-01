"""German per-turn sentiment analysis and 3-state classifier (FR12/FR13/FR14).

Runs server-side, per speaking turn, for condition T3 only. The sentiment model
(`oliverguhr/german-sentiment-bert`) is loaded once as a lazy module-level singleton.

Uses the transformers API directly (germansentiment 1.1.0 is incompatible with
transformers >= 5, which removed `batch_encode_plus`).
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

_model = None


class _GermanSentimentModel:
    """Thin wrapper around oliverguhr/german-sentiment-bert (same logic as germansentiment)."""

    def __init__(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_name = "oliverguhr/german-sentiment-bert"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model = self.model.to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._torch = torch

        self._clean_chars = re.compile(r"[^A-Za-züöäÖÜÄß ]", re.MULTILINE)
        self._clean_http_urls = re.compile(r"https*\S+", re.MULTILINE)
        self._clean_at_mentions = re.compile(r"@\S+", re.MULTILINE)

    def _replace_numbers(self, text: str) -> str:
        return (
            text.replace("0", " null").replace("1", " eins").replace("2", " zwei")
            .replace("3", " drei").replace("4", " vier").replace("5", " fünf")
            .replace("6", " sechs").replace("7", " sieben").replace("8", " acht")
            .replace("9", " neun")
        )

    def _clean_text(self, text: str) -> str:
        text = text.replace("\n", " ")
        text = self._clean_http_urls.sub("", text)
        text = self._clean_at_mentions.sub("", text)
        text = self._replace_numbers(text)
        text = self._clean_chars.sub("", text)
        text = " ".join(text.split())
        return text.strip().lower()

    def predict(self, text: str) -> dict:
        cleaned = self._clean_text(text)
        encoded = self.tokenizer(
            cleaned, padding=True, truncation=True, return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        with self._torch.no_grad():
            logits = self.model(**encoded).logits
        probs = self._torch.softmax(logits, dim=-1)[0].tolist()
        label_id = int(logits.argmax(dim=-1).item())
        label = self.model.config.id2label[label_id]
        score = float(probs[label_id])
        return {"label": label, "score": score}


def _get_model():
    global _model
    if _model is None:
        _model = _GermanSentimentModel()
    return _model


def analyse_sentiment(text: str) -> dict:
    """Classify the sentiment of a German utterance.

    Returns {"label": "positive"|"negative"|"neutral", "score": float} where score
    is the probability of the predicted label. Empty/blank text is treated as
    neutral with full confidence (nothing to analyse).
    """
    if not text or not text.strip():
        return {"label": "neutral", "score": 1.0}

    try:
        return _get_model().predict(text)
    except Exception:
        logger.exception("Sentiment analysis failed (fail-open -> neutral)")
        return {"label": "neutral", "score": 1.0}


def classify_state(
    sentiment: dict,
    pitch_delta: float,
    speech_rate_delta: float,
    pause_rate_delta: float,
) -> str:
    """Map sentiment + acoustic deltas to calm | moderate_distress | high_distress.

    Thresholds (env-var overridable):
      VOICE_SENTIMENT_NEG_HIGH = 0.80
      VOICE_SENTIMENT_NEG_MOD  = 0.55
      VOICE_PITCH_DELTA_THRESH = -0.20
      VOICE_RATE_DELTA_THRESH  = -0.20
      VOICE_PAUSE_DELTA_THRESH =  0.20
    """
    neg_high = float(os.environ.get("VOICE_SENTIMENT_NEG_HIGH", 0.80))
    neg_mod = float(os.environ.get("VOICE_SENTIMENT_NEG_MOD", 0.55))
    pitch_thresh = float(os.environ.get("VOICE_PITCH_DELTA_THRESH", -0.20))
    rate_thresh = float(os.environ.get("VOICE_RATE_DELTA_THRESH", -0.20))
    pause_thresh = float(os.environ.get("VOICE_PAUSE_DELTA_THRESH", 0.20))

    label = sentiment.get("label")
    score = sentiment.get("score", 0.0)

    is_negative = label == "negative"

    if (is_negative and score >= neg_high) or (
        pitch_delta <= pitch_thresh and speech_rate_delta <= rate_thresh
    ):
        return "high_distress"

    if (
        (is_negative and score >= neg_mod)
        or speech_rate_delta <= rate_thresh
        or pause_rate_delta >= pause_thresh
    ):
        return "moderate_distress"

    return "calm"
