from game_info.roles import ROLE_DESCRIPTIONS


class PlayerRoleStats:
    def __init__(self, role_balance: dict[str, float] | None = None):
        self.role_balance = {role: 0.0 for role in ROLE_DESCRIPTIONS.keys()}

        if role_balance:
            self.role_balance.update(role_balance)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "PlayerRoleStats":
        return cls(data)
