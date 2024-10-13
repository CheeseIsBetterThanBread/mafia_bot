from random import randint, shuffle

from internal.player import Player


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
    # who was muted last night
    last_robbed: int
    # amount of players with role that already made a decision
    state: int
    # which group was muted
    muted_group: str
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
            "Immortal": 0,
            "Thief": 1
        }

        self.night_actions = 0
        self.last_healed = -1
        self.last_visited = -1
        self.last_robbed = -1
        self.last_maniac = "maniac_kill"

        if len(players) == 5:
            self.roles = ["Thief", "Tula", "Maniac", "Sheriff", "Don"]

        elif len(players) == 6:
            roles_first = ["Mafia", "Mafia", "Doctor", "Sheriff", "Peace", "Peace"]
            roles_second = ["Mafia", "Maniac", "Peace", "Peace", "Peace", "Peace"]
            roles = [roles_first, roles_second]
            index: int = randint(0, len(roles) - 1)
            self.roles = roles[index]

        elif len(players) == 7:
            roles_first = ["Don", "Mafia", "Tula", "Sheriff", "Peace", "Peace", "Peace"]
            roles_second = ["Mafia", "Maniac", "Thief", "Peace", "Peace", "Peace", "Peace"]
            roles_third = ["Don", "Mafia", "Sheriff", "Immortal", "Peace", "Peace", "Peace"]
            roles = [roles_first, roles_second, roles_third]
            index: int = randint(0, len(roles) - 1)
            self.roles = roles[index]

        elif len(players) == 8:
            roles_first = ["Mafia", "Mafia", "Thief", "Peace", "Peace", "Peace", "Peace", "Peace"]
            roles_second = ["Don", "Mafia", "Sheriff", "Maniac", "Doctor", "Peace", "Peace", "Peace"]
            roles_third = ["Don", "Mafia", "Sheriff", "Maniac", "Tula", "Peace", "Peace", "Peace"]
            roles_fourth = ["Don", "Mafia", "Sheriff", "Immortal", "Peace", "Peace", "Peace", "Peace"]
            roles = [roles_first, roles_second, roles_third, roles_fourth]
            index: int = randint(0, len(roles) - 1)
            self.roles = roles[index]

        elif len(players) <= 10:
            self.roles = ["Don", "Mafia", "Mafia", "Sheriff", "Doctor", "Immortal", "Maniac"]
            for _ in range(len(players) - 7):
                self.roles.append("Peace")

        for _ in range(len(players) // 2):
            shuffle(self.roles)

        for index in range(len(players)):
            self.players.append(Player(players[index], self.roles[index]))
            self.night_actions += self.actions[self.roles[index]]


    def find_user(self, username: str) -> int:
        for index in range(len(self.players)):
            if self.players[index].tg_username == username:
                return index

        return -1


    def find_role(self, role: str) -> list[int]:
        answer: list[int] = []
        for index in range(len(self.players)):
            player: Player = self.players[index]
            if not player.alive:
                continue

            if player.role == role or (player.role == "Don" and role == "Mafia"):
                answer.append(index)

        return answer


    def find_alive(self) -> list[str]:
        answer: list[str] = []
        for player in self.players:
            if player.alive:
                answer.append(player.tg_username)
        return answer
