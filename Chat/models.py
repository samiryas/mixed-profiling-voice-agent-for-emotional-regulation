import json
from os import environ
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)


doc = """
Chat interaction
"""

class Constants(BaseConstants):
    name_in_url = 'Chat'
    players_per_group = None
    num_rounds = 1
    bot_label = 'Bot'


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    cachedMessages = models.LongStringField(initial='[]')
    profile_interview = models.LongStringField(initial='')
    profilingMessages_interview = models.LongStringField(initial='[]')

class MessageData(ExtraModel):
    player = models.Link(Player)
    # msg info
    msgId = models.StringField()
    timestamp = models.StringField()
    sender = models.StringField()
    fullText = models.StringField()
    msgText = models.StringField()
    audioPath = models.StringField(initial='')

# custom export of chatLog
def custom_export(players):
    # header row
    yield [ 'sessionId',  'subjectId', 'msgId', 'timestamp', 'sender', 'fullText', 'msgText', 'audioPath']
    mData = MessageData.filter()
    for m in mData:
        player = m.player
        participant = player.participant
        session = player.session
        try:
            fullText = json.loads(m.fullText)
        except:
            fullText = m.fullText

        # write to csv
        yield [ session.code, participant.code, m.msgId, m.timestamp, m.sender, fullText, m.msgText, m.audioPath]