import json
import logging
from otree.api import Currency as c, currency_range

from Introduction.models import Profile
from utils.ai import runGPT, runGPTModel
from utils.promting import renderPrompt
from . import models
from .models import Constants, MessageData, Player
from otree.api import *
from datetime import datetime, timezone


class Chat(Page):
    form_model = 'player'
    
    def before_next_page(self):
        self.participant.vars['cached_messages'] = self.player.cachedMessages

    def vars_for_template(self):
        cached = self.player.cachedMessages
        cached_questionnaire = self.participant.vars.get('cached_messages')
        if cached and cached != '[]':
            cached_messages = json.loads(cached)
        elif cached_questionnaire and cached_questionnaire != '[]':
            self.player.cachedMessages = cached_questionnaire
            cached_messages = json.loads(cached_questionnaire)
        else:
            cached_messages = []
        print(cached_messages)
        return {
            'cached_messages': cached_messages
        }
    
    # live method functions (async)
    @staticmethod
    async def live_method(player: Player, data):
        # if no new data, just return cached messages
        if not data:
            yield {player.id_in_group: dict(
                messages=json.loads(player.cachedMessages),
            )}
            return
        # if we have new data, process it and update cache
        messages = json.loads(player.cachedMessages)
        # create current player identifier
        currentPlayer = 'P' + str(player.id_in_group)
        # handle different event types
        if 'event' in data:
            # grab event type
            event = data['event']
            # handle player input logic
            if event == 'text':
                # create message id
                dateNow = str(datetime.now(tz=timezone.utc).timestamp())
                msgId = currentPlayer + '-' + str(dateNow)
                # grab text format for llm
                text = data['text']
                inputMsg = {'role': 'user', 'content': text}

                # create message data in database
                MessageData.create(
                    player = player,
                    msgId = msgId,
                    timestamp = dateNow,
                    sender = 'Subject',
                    fullText = json.dumps(inputMsg),
                    msgText = text,
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

                if assistant_count >= 8:
                    yield {player.id_in_group: 'done' }
                    return
                # grab bot info
                botId = Constants.bot_label
                # run llm on input text
                dateNow = str(datetime.now(tz=timezone.utc).timestamp())
                botMsgId = 'B' + '-' + str(dateNow)
                botMessages = messages.copy()
                botMessages.append({'role':'user','content':"Please ask your next question and stick to your system prompt and the given procedure! Consider whether it is worthwhile to ask a follow-up question or to address another dimension that has not been tackled."})
                #botText = await runGPT(messages)
                botText = await runGPT(botMessages)
                botMsg = {'role': 'assistant', 'content': botText}
                
                # save to database
                MessageData.create(
                    player=player,
                    msgId=botMsgId,
                    timestamp=dateNow,
                    sender=botId,
                    fullText=json.dumps(botMsg),
                    msgText=botText,
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
                )}
                return


class Processing(Page):
    form_model = 'player'

    def before_next_page(self):
        self.participant.vars['profile_interview'] = self.player.profile_interview

    @staticmethod
    async def live_method(player: Player, data):
        msg_type = data.get("type")        
        if msg_type == "status" and player.profile_interview == '':
            yield {player.id_in_group: 'running' }
            logging.info("Starting Profiling")
            profile_questionnaire = json.loads(player.participant.vars.get('profile_questionnaire'))
            messages = json.loads(player.cachedMessages)
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