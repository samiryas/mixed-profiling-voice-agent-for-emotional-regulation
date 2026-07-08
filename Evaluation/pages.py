from settings import LANG
from . import models
from .models import Constants
from otree.api import *


class EvaluationWAI(Page):
    form_model = 'player'
    template_name = f'Evaluation/{LANG}/EvaluationWAI.html'
    form_fields = Constants.wai_form_fields

    @staticmethod
    def live_method(player, data):
        player.timestamp_evaluate_questionnaire = data['timestamp_evaluate_questionnaire']


class EvaluationUEQ(Page):
    form_model = 'player'
    template_name = f'Evaluation/{LANG}/EvaluationUEQ.html'
    form_fields = Constants.ueq_form_fields


class EvaluationAdditional(Page):
    form_model = 'player'
    template_name = f'Evaluation/{LANG}/EvaluationAdditional.html'
    form_fields = Constants.additional_form_fields


page_sequence = [
    EvaluationWAI,
    EvaluationUEQ,
    EvaluationAdditional,
]
