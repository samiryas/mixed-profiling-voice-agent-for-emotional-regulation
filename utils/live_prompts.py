"""Hardcoded live-method LLM user turns — LANG-keyed."""
from settings import LANG

_LIVE_PROMPTS = {
    'first_question': {
        'en': 'Please ask your first question?',
        'de': 'Bitte stellen Sie Ihre erste Frage.',
    },
    'next_question': {
        'en': (
            'Please ask your next question and stick to your system prompt and the given procedure! '
            'Ask about a dimension that has not yet been addressed so that each of the seven '
            'dimensions (the five Big Five traits plus Reappraisal and Suppression) is covered exactly once.'
        ),
        'de': (
            'Bitte stellen Sie Ihre nächste Frage und halten Sie sich an Ihre Systemanweisung und das '
            'vorgegebene Verfahren! Fragen Sie nach einer Dimension, die noch nicht behandelt wurde, '
            'sodass jede der sieben Dimensionen (die fünf Big-Five-Merkmale sowie Neubewertung und '
            'Unterdrückung) genau einmal abgedeckt wird.'
        ),
    },
}


def live_prompt(key: str) -> str:
    return _LIVE_PROMPTS[key].get(LANG) or _LIVE_PROMPTS[key]['en']
