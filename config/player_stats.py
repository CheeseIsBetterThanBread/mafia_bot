from config.roles import ROLE_DESCRIPTIONS


class PlayerRoleStats:
    role_balance: dict[str, float] = {role: 0.0 for role in ROLE_DESCRIPTIONS.keys()}
