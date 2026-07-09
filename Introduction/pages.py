import asyncio
import base64
import json
import logging
import os
import random
import threading
from otree.api import Currency as c, currency_range

from settings import LANG, HRV_REST_SECONDS, hrv_rest_duration_label
from utils.ai import runGPT, runGPTModel
from utils.live_prompts import live_prompt
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
    template_name = f'Introduction/{LANG}/BigFive.html'

    def get_form_fields(self):
        order = self.participant.vars.get('big5_order')
        if not order:
            order = [name for name, _ in BIG5_FIELDS]
            random.shuffle(order)
            self.participant.vars['big5_order'] = order
        return order
      
    @staticmethod
    def live_method(player, data):
        player.timestamp_bigfive = data['timestamp_bigfive']


class BigFiveT1(BigFive):
    template_name = f'Introduction/{LANG}/BigFiveT1.html'

    def is_displayed(self):
        if self.player.field_maybe_none('treatment_questionnaire') is None:
            number = random.choice([1, 2])
            self.player.treatment_questionnaire = number
        return self.player.treatment_questionnaire == 1

class BigFiveT2(BigFive):
    template_name = f'Introduction/{LANG}/BigFiveT2.html'

    def is_displayed(self):
        if self.player.field_maybe_none('treatment_questionnaire') is None:
            number = random.choice([1, 2])
            self.player.treatment_questionnaire = random.choice([1, 2])
        return self.player.treatment_questionnaire == 2
    
class ERQ(Page):
    form_model = 'player'
    template_name = f'Introduction/{LANG}/ERQ.html'

    def get_form_fields(self):
        order = self.participant.vars.get('erq_order')
        if not order:
            order = [name for name, _ in ERQ_FIELDS]
            random.shuffle(order)
            self.participant.vars['erq_order'] = order
        return order

    @staticmethod
    def live_method(player, data):
        player.timestamp_erq = data['timestamp_erq']

class Privacy(Page):
    form_model = 'player'
    form_fields = ['privacy_agreement']
    template_name = f'Introduction/{LANG}/Privacy.html'

    #def before_next_page(self):
    #    self.player.

    @staticmethod
    def live_method(player, data):
        player.timestamp_privacy = data['timestamp_privacy']


class HRVBaseline(Page):
    form_model = 'player'
    template_name = f'Introduction/{LANG}/HRVBaseline.html'

    def vars_for_template(self):
        return dict(
            hrv_rest_seconds=HRV_REST_SECONDS,
            hrv_rest_duration=hrv_rest_duration_label(),
        )

    @staticmethod
    def live_method(player, data):
        if data.get('timestamp_hrv_baseline_start'):
            player.timestamp_hrv_baseline_start = data['timestamp_hrv_baseline_start']
            return
        if data.get('timestamp_hrv_baseline_end'):
            player.timestamp_hrv_baseline_end = data['timestamp_hrv_baseline_end']
            return


# Voice calibration baseline lives where the live session reads it from
# (Voice/acoustics.get_baseline globs {dir}/{participant.code}_calibration.*).
CALIBRATION_DIR = '_static/Voice/recordings'


class Calibration(Page):
    form_model = 'player'
    template_name = f'Introduction/{LANG}/Calibration.html'

    @staticmethod
    def live_method(player, data):
        if data.get('timestamp_calibration'):
            player.timestamp_calibration = data['timestamp_calibration']
            return

        if data.get('event') == 'calibration':
            audio = base64.b64decode(data['audio'])
            os.makedirs(CALIBRATION_DIR, exist_ok=True)
            filename = f'{player.participant.code}_calibration.webm'
            filepath = os.path.join(CALIBRATION_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(audio)
            player.calibration_audio = filename
            # hand off to Voice (FullExperiment + IntroVoice share participant.vars)
            player.participant.vars['calibration_audio'] = filename
            player.participant.vars['calibration_audio_path'] = filepath
            return {player.id_in_group: {'event': 'saved'}}


    def before_next_page(self):
        if self.player.calibration_audio:
            filepath = os.path.join(CALIBRATION_DIR, self.player.calibration_audio)
            self.participant.vars['calibration_audio'] = self.player.calibration_audio
            self.participant.vars['calibration_audio_path'] = filepath



class Processing(Page):
    form_model = 'player'
    template_name = f'Introduction/{LANG}/Processing.html'

    def vars_for_template(self):
        processing_complete = (
            bool(self.player.profile_questionnaire)
            and self.player.cachedMessages_questionnaire not in ('', '[]')
        )
        return {'processing_complete': processing_complete}

    def before_next_page(self):
        self.participant.vars['cached_messages'] = self.player.cachedMessages_questionnaire
        self.participant.vars['profile_questionnaire'] = self.player.profile_questionnaire
        if self.player.calibration_audio:
            self.participant.vars['calibration_audio'] = self.player.calibration_audio
            self.participant.vars['calibration_audio_path'] = os.path.join(
                CALIBRATION_DIR, self.player.calibration_audio,
            )

        # Freeze the ERQ reappraisal-framing category once, here (design ref D4-rev, issue #8).
        # The Voice session reads only this label; the decision is never remade per turn (NFR6).
        from utils.erq import framing_category
        erq_vals = [self.player.field_maybe_none(f'erq_{i}') for i in range(10)]
        if all(v is not None for v in erq_vals):
            category, z_reapp, z_supp = framing_category(erq_vals)
            self.participant.vars['erq_framing_category'] = category
            self.participant.vars['erq_framing_z'] = {
                'reappraisal': round(z_reapp, 3), 'suppression': round(z_supp, 3),
            }

    @staticmethod
    async def _ensure_voice_models_warm():
        from Voice.warmup import is_warm, warmup

        if not is_warm():
            await asyncio.to_thread(warmup)

    @staticmethod
    async def _run_questionnaire_profiling(player: Player):
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
        prompt_data = {
            'big5_fields': BIG5_FIELDS,
            'erq_fields': ERQ_FIELDS,
            'data': values,
            'response_model': Profile.model_json_schema()
        }
        messages = [{'role': 'user', 'content': renderPrompt(f'Introduction/templates/Prompts/{LANG}/Profiling.txt', prompt_data)}]
        profile = await runGPT(messages)
        logging.info("Profile text generated")
        messages.append({'role':'assistant', 'content': profile})
        messages.append({'role':'user','content': renderPrompt(f'Introduction/templates/Prompts/{LANG}/Modelling.txt', prompt_data)})
        profile = await runGPTModel(messages, Profile)
        logging.info("Profile modeled")
        prompt_data["profile_questionnaire"] = profile
        cachedMessages = [
            {'role': 'system', 'content': renderPrompt(f'Chat/templates/Prompts/{LANG}/System.txt', prompt_data)},
        ]
        messages_interview = cachedMessages.copy()
        messages_interview.append(
            {'role': 'user', 'content': live_prompt('first_question')}
        )
        question_1 = await runGPT(messages_interview)
        logging.info("Generated Question")
        cachedMessages.append({'role':'assistant', 'content': question_1})
        return messages, cachedMessages, profile

    @staticmethod
    async def live_method(player: Player, data):
        msg_type = data.get("type")
        if msg_type == "status" and player.profile_questionnaire == '':
            yield {player.id_in_group: 'running' }
            (messages, cachedMessages, profile), _ = await asyncio.gather(
                Processing._run_questionnaire_profiling(player),
                Processing._ensure_voice_models_warm(),
            )
            # All awaits are finished here, safe to write profiling info into player data.
            player.profilingMessages_questionnaire = json.dumps(messages)
            player.cachedMessages_questionnaire = json.dumps(cachedMessages)
            player.profile_questionnaire = profile.model_dump_json()
            yield {player.id_in_group: 'done' }
            return

page_sequence = [
    Privacy, HRVBaseline, Calibration, BigFiveT1, ERQ, BigFiveT2, Processing
]
