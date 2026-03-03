from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)
from pydantic import BaseModel


doc = """
    Big Five 10-item inventory and Dash
"""

BIG5_FIELDS = [
    ('b5_0', "I see myself as someone who is reserved"),
    ('b5_1', "I see myself as someone who is generally trusting"),
    ('b5_2', "I see myself as someone who tends to be lazy"),
    ('b5_3', "I see myself as someone who is relaxed, handles stress well"),
    ('b5_4', "I see myself as someone who has few artistic interests"),
    ('b5_5', "I see myself as someone who is outgoing, sociable"),
    ('b5_6', "I see myself as someone who tends to find fault with others"),
    ('b5_7', "I see myself as someone who does a thorough job"),
    ('b5_8', "I see myself as someone who gets nervous easily"),
    ('b5_9', "I see myself as someone who has an active imagination"),
]

DASS_FIELDS = [
	( 'dass_0', "I found it hard to wind down"),
	( 'dass_1', "I was aware of dryness of my mouth"),
	( 'dass_2', "I couldn’t seem to experience any positive feeling at all"),
	( 'dass_3', "I experienced breathing difficulty (e.g., excessively rapid breathing, breathlessness in the absence of physical exertion)"),
	( 'dass_4', "I found it difficult to work up the initiaive to do things"),
	( 'dass_5', "I tended to over-react to situations"),
	( 'dass_6', "I experienced trembling (e.g., in the hands)"),
	( 'dass_7', "I felt that I was using a lot of nervous energy"),
	( 'dass_8', "I was worried about situations in which I might panic and make a fool of myself"),
	( 'dass_9', "I felt that I had nothing to look forward to"),
	('dass_10', "I found myself getting agitated"),
	('dass_11', "I found it difficult to relax"),
	('dass_12', "I felt down-hearted and blue"),
	('dass_13', "I was intolerant of anything that kept me from getting on with what I was doing"),
	('dass_14', "I felt I was close to panic"),
	('dass_15', "I was unable to become enthusiastic about anything"),
	('dass_16', "I felt I wasn’t worth much as a person"),
	('dass_17', "I felt that I was rather touchy"),
	('dass_18', "I was aware of the action of my heart in the absence of physical exertion (e.g., sense of heart rate increase, heart missing a beat)"),
	('dass_19', "I felt scared without any good reason"),
	('dass_20', "I felt that life was meaningless"),
]

class Constants(BaseConstants):
    name_in_url = 'Introduction'
    players_per_group = None
    num_rounds = 1
    big5_labels = dict(BIG5_FIELDS) 
    dass_labels = dict(DASS_FIELDS) 

class Subsession(BaseSubsession):
    pass

def creating_session(subsession):
    import itertools
    import random
    treatments = [1, 2]
    random.shuffle(treatments)
    treatment_pool = itertools.cycle(treatments)    
    for player in subsession.get_players():
        player.treatment_questionnaire = next(treatment_pool)

class Group(BaseGroup):
    pass

BIG5_CHOICES = [[1,"Disagree strongly"], [2,"Disagree a little"], [3,"Neither agree nor Disagree"], [4,"Agree a little"], [5,"Agree strongly"]]
DASS_CHOICES = [[0,"Never"], [1,"Sometimes"], [2,"Often"], [3,"Almost Always"]]


class Profile(BaseModel):
    extraversion: str
    agreeableness: str
    conscientiousness: str
    neuroticism: str
    openness: str
    depression: str
    anxiety: str
    stress: str

class Player(BasePlayer):
    timestamp_bigfive  = models.FloatField(initial=0)
    timestamp_dass  = models.FloatField(initial=0)
    timestamp_prolific  = models.FloatField(initial=0)
    timestamp_privacy = models.FloatField(initial=0)
    prolific_id = models.StringField(label='Please enter your Prolific ID')

    privacy_agreement = models.BooleanField(
        label="To continue please first accept our survey privacy policy.",
        widget=widgets.CheckboxInput,
        initial=False
    )

    b5_0 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_0'],widget=widgets.RadioSelect)
    b5_1 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_1'],widget=widgets.RadioSelect)
    b5_2 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_2'],widget=widgets.RadioSelect)
    b5_3 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_3'],widget=widgets.RadioSelect)
    b5_4 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_4'],widget=widgets.RadioSelect)
    b5_5 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_5'],widget=widgets.RadioSelect)
    b5_6 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_6'],widget=widgets.RadioSelect)
    b5_7 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_7'],widget=widgets.RadioSelect)
    b5_8 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_8'],widget=widgets.RadioSelect)
    b5_9 = models.IntegerField(choices=BIG5_CHOICES,label=Constants.big5_labels['b5_9'],widget=widgets.RadioSelect)

    dass_0  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_0'], widget=widgets.RadioSelect)
    dass_1  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_1'], widget=widgets.RadioSelect)
    dass_2  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_2'], widget=widgets.RadioSelect)
    dass_3  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_3'], widget=widgets.RadioSelect)
    dass_4  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_4'], widget=widgets.RadioSelect)
    dass_5  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_5'], widget=widgets.RadioSelect)
    dass_6  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_6'], widget=widgets.RadioSelect)
    dass_7  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_7'], widget=widgets.RadioSelect)
    dass_8  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_8'], widget=widgets.RadioSelect)
    dass_9  = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_9'], widget=widgets.RadioSelect)
    dass_10 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_10'], widget=widgets.RadioSelect)
    dass_11 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_11'], widget=widgets.RadioSelect)
    dass_12 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_12'], widget=widgets.RadioSelect)
    dass_13 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_13'], widget=widgets.RadioSelect)
    dass_14 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_14'], widget=widgets.RadioSelect)
    dass_15 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_15'], widget=widgets.RadioSelect)
    dass_16 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_16'], widget=widgets.RadioSelect)
    dass_17 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_17'], widget=widgets.RadioSelect)
    dass_18 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_18'], widget=widgets.RadioSelect)
    dass_19 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_19'], widget=widgets.RadioSelect)
    dass_20 = models.IntegerField(choices=DASS_CHOICES, label=Constants.dass_labels['dass_20'], widget=widgets.RadioSelect)

    profilingMessages_questionnaire = models.LongStringField(initial='[]')
    cachedMessages_questionnaire = models.LongStringField(initial='[]')
    profile_questionnaire = models.LongStringField(initial='')
    treatment_questionnaire  = models.IntegerField(choices=[1,2])

