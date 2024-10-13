class Player:
    role: str | None
    alive: bool
    alibi: bool
    tg_username: str

    def __init__(self, username: str, role: str | None) -> None:
        self.alive = True
        self.alibi = False
        self.tg_username = username
        if role:
            self.role = role
