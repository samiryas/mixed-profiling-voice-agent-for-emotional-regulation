import json
import random
import threading
from otree.api import Currency as c, currency_range

from . import models
from .models import ATTRIBUTES, TRAITS, Constants, Player
from otree.api import *

class EvaluationQuestionnaire(Page):
    form_model = 'player'
    form_fields = [
        f"questionnaire_{t.lower()}_{attr}"
        for t in TRAITS
        for attr in ATTRIBUTES
    ]    
    
    def vars_for_template(self):
        profile_questionnaire = json.loads(self.participant.vars.get('profile_questionnaire'))

        return {
            'extraversion': profile_questionnaire['extraversion'],
            'agreeableness': profile_questionnaire['agreeableness'],
            'conscientiousness': profile_questionnaire['conscientiousness'],
            'neuroticism': profile_questionnaire['neuroticism'],
            'openness': profile_questionnaire['openness'],
            'depression': profile_questionnaire['depression'],
            'anxiety': profile_questionnaire['anxiety'],
            'stress': profile_questionnaire['stress']
        }

    @staticmethod
    def live_method(player, data):
        player.timestamp_evaluate_questionnaire = data['timestamp_evaluate_questionnaire']


class EvaluationQuestionnaireT1(EvaluationQuestionnaire):
    def is_displayed(self):
        if self.player.field_maybe_none('treatment_evaluation') is None:
            number = random.choice([1, 2])
            self.player.treatment_evaluation = number
        return self.player.treatment_evaluation == 1

class EvaluationQuestionnaireT2(EvaluationQuestionnaire):
    def is_displayed(self):
        if self.player.field_maybe_none('treatment_evaluation') is None:
            number = random.choice([1, 2])
            self.player.treatment_evaluation = number
        return self.player.treatment_evaluation == 2


class EvaluationInterview(Page):
    form_model = 'player'
    form_fields = [
        f"interview_{t.lower()}_{attr}"
        for t in TRAITS
        for attr in ATTRIBUTES
    ]    
    
    def vars_for_template(self):
        profile_interview = json.loads(self.participant.vars.get('profile_interview'))
        return {
            'extraversion': profile_interview['extraversion'],
            'agreeableness': profile_interview['agreeableness'],
            'conscientiousness': profile_interview['conscientiousness'],
            'neuroticism': profile_interview['neuroticism'],
            'openness': profile_interview['openness'],
            'depression': profile_interview['depression'],
            'anxiety': profile_interview['anxiety'],
            'stress': profile_interview['stress']
        }

    def before_next_page(self):
        profile_interview = json.loads(self.player.participant.vars.get('profile_interview'))
        self.player.refinement_extraversion = profile_interview['extraversion']
        self.player.refinement_agreeableness = profile_interview['agreeableness']
        self.player.refinement_conscientiousness = profile_interview['conscientiousness']
        self.player.refinement_neuroticism = profile_interview['neuroticism']
        self.player.refinement_openness = profile_interview['openness']
        self.player.refinement_depression = profile_interview['depression']
        self.player.refinement_anxiety = profile_interview['anxiety']
        self.player.refinement_stress = profile_interview['stress']    

    @staticmethod
    def live_method(player, data):
        player.timestamp_evaluate_interview = data['timestamp_evaluate_interview']


class Refinement(Page):
    form_model = 'player'
    form_fields = ['refinement_extraversion','refinement_agreeableness','refinement_conscientiousness','refinement_neuroticism','refinement_openness','refinement_depression','refinement_anxiety','refinement_stress']    

    @staticmethod
    def live_method(player, data):
        player.timestamp_refinement = data['timestamp_refinement']



page_sequence = [
    EvaluationQuestionnaireT1,EvaluationInterview,EvaluationQuestionnaireT2, Refinement
]