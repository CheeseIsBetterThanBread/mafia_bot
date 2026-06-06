from collections import Counter
import random

from config.settings import (
    ADAPTER_TYPE,
    TELEGRAM_DB_PATH,
    VK_DB_PATH,
    PLAIN_ASSIGNMENT,
    BALANCE_ASSIGNMENT,
    SIMULATION_ASSIGNMENT,
    CURRENT_ASSIGNMENT,
    BALANCE_CUT_OFF,
    PROBABILITY_THRESHOLD,
    AdapterType,
)

from game_info.player_stats import PlayerRoleStats

from engine.models import Player

from utils.stats_db import PlayerStatsDatabase
from utils.user_confirmation import confirm

match ADAPTER_TYPE:
    case AdapterType.TELEGRAM:
        db_path = TELEGRAM_DB_PATH
    case AdapterType.VK:
        db_path = VK_DB_PATH
stats_database = PlayerStatsDatabase(db_path)


class RoleBalancer:
    _max_balance = BALANCE_CUT_OFF
    __precision_threshold = 0.01

    @classmethod
    def assign_roles(cls, players: list[Player], roles: list[str]) -> bool:
        plain_allowed: bool = (CURRENT_ASSIGNMENT & PLAIN_ASSIGNMENT) != 0
        balance_allowed: bool = (CURRENT_ASSIGNMENT & BALANCE_ASSIGNMENT) != 0
        simulation_allowed: bool = (CURRENT_ASSIGNMENT & SIMULATION_ASSIGNMENT) != 0

        if simulation_allowed and random.random() < PROBABILITY_THRESHOLD:
            return cls._assign_roles_simulation(players)

        player_ids: list[int] = [player.user_id for player in players]
        stats: dict[int, PlayerRoleStats] = stats_database.load_player_stats(player_ids)

        if not balance_allowed:
            assert plain_allowed
            return cls._assign_roles_plain(players, roles, stats)

        return cls._assign_roles_balance(players, roles, stats)

    @classmethod
    def _assign_roles_plain(
        cls, players: list[Player], roles: list[str], stats: dict[int, PlayerRoleStats]
    ) -> bool:
        random.shuffle(roles)
        assignments: dict[int, str] = {}
        for i, player in enumerate(players):
            player.role = roles[i]
            assignments[player.user_id] = player.role

        cls._update_balances(stats, assignments)

        return False

    @classmethod
    def _assign_roles_balance(
        cls, players: list[Player], roles: list[str], stats: dict[int, PlayerRoleStats]
    ) -> bool:
        player_ids: list[int] = [player.user_id for player in players]
        assignments: dict[int, str] = {}
        available_players = set(player_ids)

        for role in roles:
            player = cls._select_player(role, available_players, stats)

            assignments[player] = role
            available_players.remove(player)

        cls._update_balances(stats, assignments)

        for player in players:
            player.role = assignments[player.user_id]

        return False

    @staticmethod
    def _assign_roles_simulation(players: list[Player]) -> bool:
        for player in players:
            player.role = "Мирный житель"

        return True

    @classmethod
    def _select_player(
        cls, role: str, candidates: set[int], stats: dict[int, PlayerRoleStats]
    ) -> int:
        scores: list[tuple[int, float]] = []

        for player_id in candidates:
            player_stats = stats.get(player_id, PlayerRoleStats())

            score = player_stats.role_balance.get(role, 0.0)
            scores.append((player_id, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        best_score = scores[0][1]

        eligible_players = [
            player_id
            for player_id, score in scores
            if score >= best_score - cls.__precision_threshold
        ]
        return random.choice(eligible_players)

    @classmethod
    def _update_balances(
        cls, stats: dict[int, PlayerRoleStats], assignments: dict[int, str]
    ) -> None:
        if not confirm("Update role statistics for players?", True):
            return

        probabilities = cls._calculate_probabilities(list(assignments.values()))

        for player_stats in stats.values():
            for role, probability in probabilities.items():
                current_balance = player_stats.role_balance.get(role, 0.0)
                current_balance += probability

                player_stats.role_balance[role] = cls._clamp(current_balance)

        for player_id, role in assignments.items():
            current_balance = stats[player_id].role_balance.get(role, 0.0)
            current_balance -= 1.0

            stats[player_id].role_balance[role] = cls._clamp(current_balance)

        stats_database.save_player_stats(stats)

    @staticmethod
    def _calculate_probabilities(roles: list[str]) -> dict[str, float]:
        role_counter = Counter(roles)
        total_roles = len(roles)

        return {role: count / total_roles for role, count in role_counter.items()}

    @classmethod
    def _clamp(cls, value: float) -> float:
        return max(-cls._max_balance, min(value, cls._max_balance))
