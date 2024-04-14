import json
import logging
import random
import requests

from config import DEFAULT_HOST


ACCEPTED_COLORS = "red green blue yellow black purple orange pink".split()
ACCEPTED_OPTIONS = {
    "венера": "venusNext",
    "колонии": "colonies",
    "прологи": "prelude",
    "прологи2": "prelude2",
    "луна": "moonExpansion",
    "промо": "promoCardsOption",
    "следопыты": "pathfinders",
    "венера-must": "requiresVenusTrackCompletion",
    "венера-альт": "altVenusBoard",
}


class GameCreator:
    def __init__(self, num_players):
        self.num_players = num_players
        self.host = DEFAULT_HOST
        self.players = []
        self.options = None
        self.accepts_players = num_players > 0
        self.started = False
        self.game_id = None

    def add_player(self, player_name, color):
        if not self.accepts_players:
            raise RuntimeError()
        if color not in ACCEPTED_COLORS:
            raise ValueError()
        self.players.append((player_name, color))
        if len(self.players) >= self.num_players:
            self.accepts_players = False

    def consume_message(self, text):
        if self.accepts_players:
            self.add_player(*text.rsplit(maxsplit=1))
        elif self.options is None:
            if text == "дефолт":
                self.options = {}
            else:
                self.options = {ACCEPTED_OPTIONS[t]: True for t in text.lower().split()}
        else:
            raise RuntimeError()


    @staticmethod
    def get_usage():
        return "Использование: /new N (где N = число игроков)"

    @staticmethod
    def get_header():
        return '\n'.join([
            "Доступные цвета: {}".format(', '.join(ACCEPTED_COLORS)),
            "Доступные опции: {}".format(', '.join(ACCEPTED_OPTIONS.keys()))
        ])

    @staticmethod
    def player_link(pid):
        return f"http://{DEFAULT_HOST}/player?id={pid}"

    def get_message(self):
        if self.accepts_players:
            return "Добавьте следующего игрока в формате <имя_игрока> <цвет>"
        elif self.options is None:
            return "Введите желаемые опции через пробел или слово \"дефолт\""
        elif len(self.players) > 0:
            self.started = True
            reply = self.start_game()
            self.game_id = reply["spectatorId"]
            return '\n'.join(["Игра создана"] + [
                "{} {}".format(pl["name"], self.player_link(pl["id"])) for pl in reply["players"]
            ])
        else:
            raise RuntimeError()

    def start_game(self):
        start_url = f'http://{DEFAULT_HOST}/game'
        with open('new_game_options.json') as fopts:
            params = json.load(fopts)
            params.update(self.options)
            params['seed'] = random.random()
            params['players'] = []
            random.shuffle(self.players)
            for idx, player in enumerate(self.players):
                params['players'].append({
                    "index": idx + 1,
                    "name": player[0],
                    "color": player[1],
                    "beginner": False,
                    "handicap": 0,
                    "first": False,
                })
            logging.debug(params)
            reply = requests.put(start_url, json=params)
            logging.debug(reply.text)
            return reply.json()
