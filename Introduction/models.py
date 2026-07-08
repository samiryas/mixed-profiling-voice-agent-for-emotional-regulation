from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)
from pydantic import BaseModel

from settings import LANG


doc = """
    Big Five 10-item inventory and ERQ-10
"""

BIG5_FIELDS_EN = [
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

# Rammstedt & John (2007), BFI-10 — published German items (Appendix A).
BIG5_FIELDS_DE = [
    ('b5_0', "Ich bin eher zurückhaltend, reserviert."),
    ('b5_1', "Ich schenke anderen leicht Vertrauen, glaube an das Gute im Menschen."),
    ('b5_2', "Ich bin bequem, neige zur Faulheit."),
    ('b5_3', "Ich bin entspannt, lasse mich durch Stress nicht aus der Ruhe bringen."),
    ('b5_4', "Ich habe nur wenig künstlerisches Interesse."),
    ('b5_5', "Ich gehe aus mir heraus, bin gesellig."),
    ('b5_6', "Ich neige dazu, andere zu kritisieren."),
    ('b5_7', "Ich erledige Aufgaben gründlich."),
    ('b5_8', "Ich werde leicht nervös und unsicher."),
    ('b5_9', "Ich habe eine aktive Vorstellungskraft, bin phantasievoll."),
]

BIG5_FIELDS = BIG5_FIELDS_DE if LANG == 'de' else BIG5_FIELDS_EN

ERQ_FIELDS_EN = [
    ('erq_0', "When I want to feel more positive emotion (such as joy or amusement), I change what I'm thinking about."),
    ('erq_1', "I keep my emotions to myself."),
    ('erq_2', "When I want to feel less negative emotion (such as sadness or anger), I change what I'm thinking about."),
    ('erq_3', "When I am feeling positive emotions, I am careful not to express them."),
    ('erq_4', "When I'm faced with a stressful situation, I make myself think about it in a way that helps me stay calm."),
    ('erq_5', "I control my emotions by not expressing them."),
    ('erq_6', "When I want to feel more positive emotion, I change the way I'm thinking about the situation."),
    ('erq_7', "I control my emotions by changing the way I think about the situation I'm in."),
    ('erq_8', "When I am feeling negative emotions, I make sure not to express them."),
    ('erq_9', "When I want to feel less negative emotion, I change the way I'm thinking about the situation."),
]

ERQ_FIELDS_DE = [
    ('erq_0', "Wenn ich mehr positive Gefühle (wie Freude oder Heiterkeit) empfinden möchte, ändere ich, woran ich denke."),
    ('erq_1', "Ich behalte meine Gefühle für mich."),
    ('erq_2', "Wenn ich weniger negative Gefühle (wie Traurigkeit oder Ärger) empfinden möchte, ändere ich, woran ich denke."),
    ('erq_3', "Wenn ich positive Gefühle empfinde, bemühe ich mich, sie nicht nach außen zu zeigen."),
    ('erq_4', "Wenn ich in eine stressige Situation gerate, ändere ich meine Gedanken über die Situation so, dass es mich beruhigt."),
    ('erq_5', "Ich halte meine Gefühle unter Kontrolle, indem ich sie nicht nach außen zeige."),
    ('erq_6', "Wenn ich mehr positive Gefühle empfinden möchte, versuche ich über die Situation anders zu denken."),
    ('erq_7', "Ich halte meine Gefühle unter Kontrolle, indem ich über meine aktuelle Situation anders nachdenke."),
    ('erq_8', "Wenn ich negative Gefühle empfinde, sorge ich dafür, sie nicht nach außen zu zeigen."),
    ('erq_9', "Wenn ich weniger negative Gefühle empfinden möchte, versuche ich über die Situation anders zu denken."),
]

ERQ_FIELDS = ERQ_FIELDS_DE if LANG == 'de' else ERQ_FIELDS_EN

class Constants(BaseConstants):
    name_in_url = 'Introduction'
    players_per_group = None
    num_rounds = 1
    big5_labels = dict(BIG5_FIELDS)
    erq_labels = dict(ERQ_FIELDS)

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

BIG5_CHOICES_EN = [
    [1, "Disagree strongly"],
    [2, "Disagree a little"],
    [3, "Neither agree nor Disagree"],
    [4, "Agree a little"],
    [5, "Agree strongly"],
]
BIG5_CHOICES_DE = [
    [1, "trifft überhaupt nicht zu"],
    [2, "trifft eher nicht zu"],
    [3, "weder noch"],
    [4, "trifft eher zu"],
    [5, "trifft voll und ganz zu"],
]
BIG5_CHOICES = BIG5_CHOICES_DE if LANG == 'de' else BIG5_CHOICES_EN

ERQ_CHOICES_EN = [
    [1, "Strongly disagree"],
    [2, "Disagree"],
    [3, "Slightly disagree"],
    [4, "Neutral"],
    [5, "Slightly agree"],
    [6, "Agree"],
    [7, "Strongly agree"],
]

ERQ_CHOICES_DE = [
    [1, "stimmt überhaupt nicht"],
    [2, "2"],
    [3, "3"],
    [4, "neutral"],
    [5, "5"],
    [6, "6"],
    [7, "stimmt vollkommen"],
]

ERQ_CHOICES = ERQ_CHOICES_DE if LANG == 'de' else ERQ_CHOICES_EN

PRIVACY_AGREEMENT_LABEL_EN = "To continue please first accept our survey privacy policy."
PRIVACY_AGREEMENT_LABEL_DE = "Um fortzufahren, akzeptieren Sie bitte zuerst unsere Datenschutzerklärung zur Studie."
PRIVACY_AGREEMENT_LABEL = PRIVACY_AGREEMENT_LABEL_DE if LANG == 'de' else PRIVACY_AGREEMENT_LABEL_EN


class Profile(BaseModel):
    extraversion: str
    agreeableness: str
    conscientiousness: str
    neuroticism: str
    openness: str
    reappraisal: str
    suppression: str

class Player(BasePlayer):
    timestamp_bigfive  = models.FloatField(initial=0)
    timestamp_erq  = models.FloatField(initial=0)
    timestamp_privacy = models.FloatField(initial=0)
    timestamp_hrv_baseline_start = models.FloatField(initial=0)
    timestamp_hrv_baseline_end = models.FloatField(initial=0)
    timestamp_calibration = models.FloatField(initial=0)
    calibration_audio     = models.StringField(initial='')   # saved baseline filename

    privacy_agreement = models.BooleanField(
        label=PRIVACY_AGREEMENT_LABEL,
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

    erq_0 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_0'], widget=widgets.RadioSelect)
    erq_1 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_1'], widget=widgets.RadioSelect)
    erq_2 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_2'], widget=widgets.RadioSelect)
    erq_3 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_3'], widget=widgets.RadioSelect)
    erq_4 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_4'], widget=widgets.RadioSelect)
    erq_5 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_5'], widget=widgets.RadioSelect)
    erq_6 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_6'], widget=widgets.RadioSelect)
    erq_7 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_7'], widget=widgets.RadioSelect)
    erq_8 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_8'], widget=widgets.RadioSelect)
    erq_9 = models.IntegerField(choices=ERQ_CHOICES, label=Constants.erq_labels['erq_9'], widget=widgets.RadioSelect)

    profilingMessages_questionnaire = models.LongStringField(initial='[]')
    cachedMessages_questionnaire = models.LongStringField(initial='[]')
    profile_questionnaire = models.LongStringField(initial='')
    treatment_questionnaire  = models.IntegerField(choices=[1,2])

