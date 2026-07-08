from otree.api import Currency as c, currency_range

from settings import LANG
from . import models
from .models import Constants, Player
from otree.api import *


class EvaluationQuestionnaire(Page):
    form_model = 'player'
    template_name = f'Evaluation/{LANG}/EvaluationQuestionnaire.html'
    form_fields = Constants.form_fields

    @staticmethod
    def live_method(player, data):
        player.timestamp_evaluate_questionnaire = data['timestamp_evaluate_questionnaire']


page_sequence = [
    EvaluationQuestionnaire
]
