import json
import random
import threading
from otree.api import Currency as c, currency_range

from . import models
from .models import ATTRIBUTES, TRAITS, Constants, Player
from otree.api import *

class Outro(Page):
    form_model = 'player'

    def vars_for_template(player):
        prolific_code = player.session.config['prolific_return_code']
        prolific_url = player.session.config['prolific_return_url']
        return {
            'prolific_code': prolific_code,
            "prolific_url": prolific_url
        }

    @staticmethod
    def live_method(player, data):
        player.timestamp_outro = data['timestamp_outro']



page_sequence = [
    Outro
]