import json
import logging
import random
import threading
from otree.api import Currency as c, currency_range

from utils.ai import runGPT, runGPTModel
from utils.promting import renderPrompt
from . import models

from .models import BIG5_CHOICES, BIG5_FIELDS, ERQ_CHOICES, ERQ_FIELDS, Constants, Player, Profile
from otree.api import *
from sqlalchemy.inspection import inspect


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education']
    ##random.shuffle(form_fields)

    @staticmethod
    def live_method(player, data):
        player.timestamp_demographics = data['timestamp_demographics']

class Introduction(Page):
    form_model = 'player'
    form_fields = ['age','gender','education']

    @staticmethod
    def live_method(player, data):
        player.timestamp_introduction = data['timestamp_introduction']

class BigFive(Page):
    form_model = 'player'
    form_fields = [name for name, _ in BIG5_FIELDS]
    random.shuffle(form_fields)
      
    @staticmethod
    def live_method(player, data):
        player.timestamp_bigfive = data['timestamp_bigfive']


class BigFiveT1(BigFive):
    def is_displayed(self):
        if self.player.field_maybe_none('treatment_questionnaire') is None:
            number = random.choice([1, 2])
            self.player.treatment_questionnaire = number
        return self.player.treatment_questionnaire == 1

class BigFiveT2(BigFive):
    def is_displayed(self):
        if self.player.field_maybe_none('treatment_questionnaire') is None:
            number = random.choice([1, 2])
            self.player.treatment_questionnaire = random.choice([1, 2])
        return self.player.treatment_questionnaire == 2
    
class ERQ(Page):
    form_model = 'player'
    form_fields = [name for name, _ in ERQ_FIELDS]
    random.shuffle(form_fields)

    @staticmethod
    def live_method(player, data):
        player.timestamp_erq = data['timestamp_erq']

class Prolific(Page):
    form_model = 'player'
    form_fields = ['prolific_id']

    @staticmethod
    def live_method(player, data):
        player.timestamp_prolific = data['timestamp_prolific']

class Privacy(Page):
    form_model = 'player'
    form_fields = ['privacy_agreement']

    #def before_next_page(self):
    #    self.player.

    @staticmethod
    def live_method(player, data):
        player.timestamp_privacy = data['timestamp_privacy']



class Processing(Page):
    form_model = 'player'

    def vars_for_template(self):
        processing_complete = (
            bool(self.player.profile_questionnaire)
            and self.player.cachedMessages_questionnaire not in ('', '[]')
        )
        return {'processing_complete': processing_complete}

    def before_next_page(self):
        self.participant.vars['cached_messages'] = self.player.cachedMessages_questionnaire
        self.participant.vars['profile_questionnaire'] = self.player.profile_questionnaire

    @staticmethod
    async def live_method(player: Player, data):
        msg_type = data.get("type")
        if msg_type == "status" and player.profile_questionnaire == '':
            yield {player.id_in_group: 'running' }
            logging.info("Starting Profiling")
            values = {
                **{
                    attr.key: dict(BIG5_CHOICES).get(getattr(player, attr.key))
                    for attr in inspect(Player).attrs
                    if attr.key in [key for key, _ in BIG5_FIELDS]
                },
                **{
                    attr.key: dict(ERQ_CHOICES).get(getattr(player, attr.key))
                    for attr in inspect(Player).attrs
                    if attr.key in [key for key, _ in ERQ_FIELDS]
                }
            }
            data = {
                'big5_fields': BIG5_FIELDS,
                'erq_fields': ERQ_FIELDS,
                'data': values,
                'response_model': Profile.model_json_schema()
            }
            messages = [{'role': 'user', 'content': renderPrompt('Introduction/templates/Prompts/Profiling.txt', data)}]
            profile = await runGPT(messages)
            logging.info("Profile text generated")
            messages.append({'role':'assistant', 'content': profile})
            messages.append({'role':'user','content': renderPrompt('Introduction/templates/Prompts/Modelling.txt', data)})
            profile = await runGPTModel(messages, Profile)
            logging.info("Profile modeled")
            player.profilingMessages_questionnaire = json.dumps(messages)
            player.profile_questionnaire = profile.model_dump_json()
            data["profile_questionnaire"] = profile
            cachedMessages = [
                {'role': 'system', 'content': renderPrompt('Chat/templates/Prompts/System.txt', data)},
            ]
            messages_interview = cachedMessages.copy()
            messages_interview.append(
                {'role': 'user', 'content': 'Please ask your first question?'}
            )
            question_1 = await runGPT(messages_interview)
            logging.info("Generated Question")
            cachedMessages.append({'role':'assistant', 'content': question_1})
            player.cachedMessages_questionnaire = json.dumps(cachedMessages)
            yield {player.id_in_group: 'done' }
            return

page_sequence = [
    Prolific, Privacy, BigFiveT1, ERQ, BigFiveT2, Processing
]
