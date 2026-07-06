from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)

from settings import LANG

doc = """
    Evaluating the profiles
"""

REFINEMENT_LABELS = {
    'extraversion': 'Extraversion',
    'agreeableness': 'Verträglichkeit' if LANG == 'de' else 'Agreeableness',
    'conscientiousness': 'Gewissenhaftigkeit' if LANG == 'de' else 'Conscientiousness',
    'neuroticism': 'Neurotizismus' if LANG == 'de' else 'Neuroticism',
    'openness': 'Offenheit' if LANG == 'de' else 'Openness',
    'reappraisal': 'Neubewertung' if LANG == 'de' else 'Reappraisal',
    'suppression': 'Unterdrückung' if LANG == 'de' else 'Suppression',
}


TRAITS = [
    'Extraversion','Agreeableness','Conscientiousness','Neuroticism','Openness',
    'Reappraisal','Suppression'
]

ATTRIBUTES = ["useful", "plausible", "trustworthy", "accurate"]

class Constants(BaseConstants):
    name_in_url = 'Evaluation'
    players_per_group = None
    num_rounds = 1

class Subsession(BaseSubsession):
    pass

def creating_session(subsession):
    import itertools
    import random
    treatments = [1, 2]
    random.shuffle(treatments)
    treatment_pool = itertools.cycle(treatments)    
    for player in subsession.get_players():
        player.treatment_evaluation = next(treatment_pool)

class Group(BaseGroup):
    pass


BIG5_CHOICES = [[1,"Disagree strongly"], [2,"Disagree a little"], [3,"Neither agree nor Disagree"], [4,"Agree a little"], [5,"Agree strongly"]]

SEVEN_LIKERT_SCALE = [i for i in range(1,8)]

class Player(BasePlayer):
    timestamp_evaluate_questionnaire = models.FloatField()
    timestamp_evaluate_interview = models.FloatField()
    timestamp_refinement = models.FloatField()
    
    interview_extraversion_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_extraversion_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_extraversion_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_extraversion_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_agreeableness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_agreeableness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_agreeableness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_agreeableness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_conscientiousness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_conscientiousness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_conscientiousness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_conscientiousness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_neuroticism_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_neuroticism_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_neuroticism_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_neuroticism_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_openness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_openness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_openness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_openness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_reappraisal_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_reappraisal_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_reappraisal_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_reappraisal_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    interview_suppression_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_suppression_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_suppression_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    interview_suppression_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_extraversion_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_extraversion_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_extraversion_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_extraversion_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_agreeableness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_agreeableness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_agreeableness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_agreeableness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_conscientiousness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_conscientiousness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_conscientiousness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_conscientiousness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_neuroticism_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_neuroticism_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_neuroticism_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_neuroticism_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_openness_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_openness_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_openness_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_openness_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_reappraisal_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_reappraisal_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_reappraisal_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_reappraisal_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    questionnaire_suppression_useful      = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_suppression_plausible   = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_suppression_trustworthy = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)
    questionnaire_suppression_accurate    = models.IntegerField(choices=SEVEN_LIKERT_SCALE, widget=widgets.RadioSelect)

    refinement_extraversion = models.LongStringField(label=REFINEMENT_LABELS['extraversion'])
    refinement_agreeableness = models.LongStringField(label=REFINEMENT_LABELS['agreeableness'])
    refinement_conscientiousness = models.LongStringField(label=REFINEMENT_LABELS['conscientiousness'])
    refinement_neuroticism = models.LongStringField(label=REFINEMENT_LABELS['neuroticism'])
    refinement_openness = models.LongStringField(label=REFINEMENT_LABELS['openness'])
    refinement_reappraisal = models.LongStringField(label=REFINEMENT_LABELS['reappraisal'])
    refinement_suppression = models.LongStringField(label=REFINEMENT_LABELS['suppression'])
    treatment_evaluation  = models.IntegerField(choices=[1,2])


