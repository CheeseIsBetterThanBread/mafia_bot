from collections import deque
from enum import Enum
from random import choice

from config.settings import SECONDS_PER_PLAYER, SPEECH_LOWER_BOUND, SPEECH_UPPER_BOUND
from utils.helpers import alive_sorted, rotate_queue

from engine.models import Player
from engine.presets import ROOM_PRESETS
from engine.roles import MAFIA_TEAM


class GameState(Enum):
    LOBBY = "lobby"
    DAY = "day"
    DEFENSE = "defense"
    VOTING = "voting"
    BALANCE = "balance"
    REVOTE = "revote"
    NIGHT_THIEF = "night_thief"
    NIGHT = "night"
    FINISHED = "finished"


class Game:
    def __init__(self, chat_id: int, game_counter: int):
        self.chat_id = chat_id

        self.players = {}          # user_id -> Player
        self.players_by_number = {}

        self.state = GameState.LOBBY

        self.day_count = 0
        self.game_number = game_counter
        self.day_starter_num = 1

        self.nominated = []
        self.speech_queue = deque()
        self.defense_queue = deque()
        self.current_speech_task = None

        self.voting_queue = deque()
        self.current_votes = {}
        self.vote_history = {}

        self.balance_players = []
        self.revote_count = 0

        self.night_actions = {}

        self.expected_night_actors = {}

        self.current_preset = []

        self.mafia_team = MAFIA_TEAM

    # --- PLAYERS ---

    def add_player(self, user_id: int, name: str):
        if user_id in self.players:
            return False

        number = len(self.players) + 1
        p = Player(user_id, name, number)

        self.players[user_id] = p
        self.players_by_number[number] = p
        return True

    def get_alive_players(self):
        return [p for p in self.players.values() if p.is_alive]

    # --- QUEUE ---

    def build_daily_queue(self):
        alive = alive_sorted(self.get_alive_players())

        if not alive:
            return deque(), -1

        queue, self.day_starter_num = rotate_queue(alive, self.day_starter_num)
        return queue, self.day_starter_num

    # --- ROLE PRESET PICK ---

    def set_preset(self, count: int):
        max_count = max(ROOM_PRESETS.keys())
        self.current_preset = choice(ROOM_PRESETS[min(count, max_count)]).copy()

        if count > max_count:
            self.current_preset += ['Мирный житель'] * (count - max_count)

        return self.current_preset

    # --- DYNAMIC SPEECH TIME ---

    def calculate_speech_time(self):
        alive_count = len(self.get_alive_players())
        raw_time = alive_count * SECONDS_PER_PLAYER
        return min(SPEECH_UPPER_BOUND, max(SPEECH_LOWER_BOUND, raw_time))
