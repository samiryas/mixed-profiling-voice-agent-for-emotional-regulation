import json
import logging
import os
import base64
from os import environ
from otree.api import Currency as c, currency_range

from Introduction.models import Profile
from utils.ai import runGPT, runGPTModel
from utils.promting import renderPrompt
from Voice.services import transcribe, synthesize
from . import models
from .models import Constants, MessageData, Player
from otree.api import *
from datetime import datetime, timezone

# the interview is now conducted by voice; audio is saved alongside the Voice
# module's recordings so it is served at /static/Voice/recordings/<file>
RECORDINGS_DIR = '_static/Voice/recordings'
VOICE_ID = environ.get('VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')
SAVE_USER_AUDIO = True


def _save_audio(filename: str, audio: bytes) -> str:
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    with open(os.path.join(RECORDINGS_DIR, filename), 'wb') as f:
        f.write(audio)
    return filename


class Chat(Page):
    form_model = 'player'

    @staticmethod
    def _ensure_cached_messages(player: Player):
        if player.cachedMessages and player.cachedMessages != '[]':
            return
        cached = player.participant.vars.get('cached_messages')
        if cached and cached != '[]':
            player.cachedMessages = cached

    def before_next_page(self):
        self.participant.vars['cached_messages'] = self.player.cachedMessages
        if self.participant.vars.get('skip_chat'):
            pq = self.participant.vars.get('profile_questionnaire', '')
            if pq and not self.player.profile_interview:
                self.player.profile_interview = pq
                self.participant.vars['profile_interview'] = pq

    def vars_for_template(self):
        self._ensure_cached_messages(self.player)
        cached_messages = json.loads(self.player.cachedMessages or '[]')
        return {
            'cached_messages': cached_messages,
            'dev_skip_chat': environ.get('VOICE_DEV_SKIP_CHAT') == '1',
        }
    
    # live method functions (async)
    @staticmethod
    async def live_method(player: Player, data):
        Chat._ensure_cached_messages(player)
        # if no new data, just return cached messages
        if not data:
            yield {player.id_in_group: dict(
                messages=json.loads(player.cachedMessages or '[]'),
            )}
            return
        # if we have new data, process it and update cache
        messages = json.loads(player.cachedMessages or '[]')
        # create current player identifier
        currentPlayer = 'P' + str(player.id_in_group)
        # handle different event types
        if 'event' in data:
            # grab event type
            event = data['event']
            # dev-only: skip the voice interview and reuse the questionnaire profile
            if event == 'skip':
                player.participant.vars['skip_chat'] = True
                return
            # handle player input logic
            if event == 'text':
                # create message id
                dateNow = str(datetime.now(tz=timezone.utc).timestamp())
                msgId = currentPlayer + '-' + str(dateNow)

                # decode the recorded audio, persist it, then transcribe (STT)
                b64 = base64.b64decode(data['text'])
                audioPath = ''
                if SAVE_USER_AUDIO:
                    audioPath = _save_audio(f'{player.session.code}_{msgId}.webm', b64)

                try:
                    text = await transcribe(b64)
                except Exception as e:
                    logging.exception('STT failed')
                    yield {player.id_in_group: {'error': f'Transcription failed: {e}'}}
                    return

                inputMsg = {'role': 'user', 'content': text}

                # create message data in database
                MessageData.create(
                    player = player,
                    msgId = msgId,
                    timestamp = dateNow,
                    sender = 'Subject',
                    fullText = json.dumps(inputMsg),
                    msgText = text,
                    audioPath = audioPath,
                )
                # add message to list and update cache
                messages.append(inputMsg)
                player.cachedMessages = json.dumps(messages)
                # yield output to chat.html
                yield {player.id_in_group: dict(
                    event='text',
                    selfText=text,
                    sender=currentPlayer,
                    msgId=msgId,
                )}
                return
            # handle bot messages
            elif event == 'botMsg':
                assistant_count = len([msg for msg in messages if msg.get("role") == "assistant"])

                # one question per dimension: 5 Big Five + reappraisal + suppression = 7
                if assistant_count >= 7:
                    yield {player.id_in_group: 'done' }
                    return
                # grab bot info
                botId = Constants.bot_label
                # run llm on input text
                dateNow = str(datetime.now(tz=timezone.utc).timestamp())
                botMsgId = 'B' + '-' + str(dateNow)
                botMessages = messages.copy()
                botMessages.append({'role':'user','content':"Please ask your next question and stick to your system prompt and the given procedure! Ask about a dimension that has not yet been addressed so that each of the seven dimensions (the five Big Five traits plus Reappraisal and Suppression) is covered exactly once."})
                #botText = await runGPT(messages)
                botText = await runGPT(botMessages)
                botMsg = {'role': 'assistant', 'content': botText}

                # synthesize the spoken question (TTS); the stub backend returns
                # no bytes, so the client falls back to showing the transcript only
                audioURL = None
                audioPath = ''
                try:
                    audio = await synthesize(botText, voice_id=VOICE_ID)
                    if audio:
                        audioPath = _save_audio(f'{player.session.code}_{botMsgId}.mp3', audio)
                        audioURL = audioPath
                except Exception:
                    logging.exception('TTS failed (continuing text-only)')

                # save to database
                MessageData.create(
                    player=player,
                    msgId=botMsgId,
                    timestamp=dateNow,
                    sender=botId,
                    fullText=json.dumps(botMsg),
                    msgText=botText,
                    audioPath=audioPath,
                )

                # update cache with bot message
                messages.append(botMsg)
                player.cachedMessages = json.dumps(messages)

                # yield output to chat.html
                yield {player.id_in_group: dict(
                    event='botText',
                    sender=botId,
                    botMsgId=botMsgId,
                    text=botText,
                    audioFilePath=audioURL,
                )}
                return


class Processing(Page):
    form_model = 'player'

    def vars_for_template(self):
        return {'processing_complete': bool(self.player.profile_interview)}

    def before_next_page(self):
        self.participant.vars['profile_interview'] = self.player.profile_interview

    @staticmethod
    async def live_method(player: Player, data):
        msg_type = data.get("type")
        if msg_type == "status" and player.profile_interview == '':
            if player.participant.vars.get('skip_chat'):
                pq = player.participant.vars.get('profile_questionnaire', '')
                if pq:
                    player.profile_interview = pq
                yield {player.id_in_group: 'done'}
                return
            yield {player.id_in_group: 'running' }
            logging.info("Starting Profiling")
            profile_questionnaire = json.loads(player.participant.vars.get('profile_questionnaire', '{}'))
            Chat._ensure_cached_messages(player)
            messages = json.loads(player.cachedMessages or '[]')
            qa = []
            for i in range(len(messages) - 1):
                if (messages[i]["role"] == "assistant" and messages[i + 1]["role"] == "user"):
                    qa.append({"question": messages[i]["content"],"answer": messages[i + 1]["content"]}
                )
            data = {
                "messages": qa,
                "profile_questionnaire": profile_questionnaire,
                'response_model': Profile.model_json_schema()
            }
            messages = [{'role': 'user', 'content': renderPrompt('Chat/templates/Prompts/Profiling.txt', data)}]
            profile = await runGPT(messages)
            logging.info("Profile text generated")
            messages.append({'role':'assistant', 'content': profile})
            messages.append({'role':'user','content': renderPrompt('Introduction/templates/Prompts/Modelling.txt', data)})
            profile = await runGPTModel(messages, Profile)
            logging.info("Profile modeled")
            player.profilingMessages_interview = json.dumps(messages)
            player.profile_interview = profile.model_dump_json()       
            yield {player.id_in_group: 'done' }
            return

# page sequence
page_sequence = [
    Chat, Processing
]