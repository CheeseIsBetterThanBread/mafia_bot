from random import shuffle

from player import Player


class Game:
    # General information about game
    # amount of players that are not peaceful
    not_trivial: int
    # roles in the game
    roles: list[str] = []
    # list of players
    players: list[Player] = []

    # Information relevant to the night
    # who was healed last night
    last_healed: int
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
        self.last_healed = -1
        self.not_trivial = 4
        roles = ["Mafia", "Mafia", "Doctor", "Sheriff"]
        if len(players) <= 7:
            for i in range(len(players) - 4):
                roles.append("Peace")
        else: # count == 8
            self.not_trivial += 1
            for i in range(len(players) - 5):
                roles.append("Peace")
            roles.append("Maniac")

        for _ in range(len(players) // 2):
            shuffle(roles)

        for index in range(len(players)):
            self.players.append(Player(players[index], roles[index]))


    def find_user(self, username: str) -> int:
        for index in range(len(self.players)):
            if self.players[index].tg_username == username:
                return index

        return -1
