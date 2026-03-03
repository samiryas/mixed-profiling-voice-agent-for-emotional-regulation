from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)

doc = """
    Link to Prolific
"""


TRAITS = [
    'Extraversion','Agreeableness','Conscientiousness','Neuroticism','Openness',
    'Depression','Anxiety','Stress'
]

ATTRIBUTES = ["useful", "plausible", "trustworthy", "accurate"]

class Constants(BaseConstants):
    name_in_url = 'Outro'
    players_per_group = None
    num_rounds = 1

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    timestamp_outro  = models.FloatField(initial=0)
