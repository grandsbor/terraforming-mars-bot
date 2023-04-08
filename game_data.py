from config import DEFAULT_DELAY
from tf_tracker import TerraformingTracker


class GameData:
    def __init__(self, state, game_id=None, last_ping=None):
        self.state = state
        self.game_id = game_id
        self.last_ping = last_ping
        self.ping_delay_min = DEFAULT_DELAY
        self.users_tag = {}
        self.users_info = {}  # keys are tg usernames
        self.scheduled_turns = {}
        self.tft = TerraformingTracker()

    def __str__(self):
        return f"GameData(state={self.state}, game_id={self.game_id}, last_ping={self.last_ping}, " \
               f"users_info={self.users_info}, scheduled_turns={self.scheduled_turns}"

    def restore(self):
        """ for handling class structure updates during single game """
        if not hasattr(self, 'scheduled_turns'):
            self.scheduled_turns = {}
        return self


