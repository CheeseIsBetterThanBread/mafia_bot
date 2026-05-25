class Player:
    def __init__(self, user_id: int, name: str, number: int):
        self.user_id = user_id
        self.name = name
        self.number = number

        self.role = None
        self.is_alive = True
        self.is_glued = False

        self.has_alibi = False
        self.has_nominated = False

        # ночные механики
        self.shurikens = 0
        self.last_healed = None
        self.last_alibi = None
        self.last_man_heal = False

        # двуликий
        self.found_mafia = False
        self.found_mafia_day = -1

        # вор
        self.last_rek = None
