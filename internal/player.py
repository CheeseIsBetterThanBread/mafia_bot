class Player:
    role: str | None
    alive: bool
    tg_username: str

    def __init__(self, username: str, role: str | None) -> None:
        self.alive = True
        self.tg_username = username
        if role:
            self.role = role
