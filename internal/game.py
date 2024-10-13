from random import shuffle

from player import Player


class Game:
    # General information about game
    # amount of actions that need to happen during the night
    night_actions: int
    # roles in the game
    roles: list[str] = []
    # list of players
    players: list[Player] = []
    # amount of actions per player
    actions: dict[str, int] = {}

    # Information relevant to the night
    # who was healed last night
    last_healed: int
    # where Tula went last night
    last_visited: int
    # last action of a maniac
    last_maniac: str
    # amount of players with role that already made a decision
    state: int
    # who was killed and healed
    important: dict[str, int] = {}

    # Information relevant to the day
    # put up for votes
    for_vote: dict[str, int] = {}
    # votes
    voted: dict[str, int] = {}
    # allowed to vote
    allowed_to_vote: bool
    # about to be kicked
    kicked: list[int] = []

    def __init__(self):
        pass


    def set_up(self, players: list[str]) -> None:
        self.actions: dict[str, int] = {
            "Peace": 0,
            "Mafia": 1,
            "Sheriff": 1,
            "Doctor": 1,
            "Don": 2,
            "Maniac": 1,
            "Tula": 1,
            "Immortal": 0
        }
        self.last_healed = -1
        self.last_visited = -1
        self.last_maniac = "maniac_kill"
        roles = ["Mafia", "Mafia", "Doctor", "Sheriff"]
        if len(players) <= 7:
            for i in range(len(players) - 4):
                roles.append("Peace")
        else: # count == 8
            self.night_actions += 1
            for i in range(len(players) - 5):
                roles.append("Peace")
            roles.append("Maniac")

        for _ in range(len(players) // 2):
            shuffle(roles)

        for index in range(len(players)):
            self.players.append(Player(players[index], roles[index]))
            self.night_actions += self.actions[roles[index]]


    def find_user(self, username: str) -> int:
        for index in range(len(self.players)):
            if self.players[index].tg_username == username:
                return index

        return -1
