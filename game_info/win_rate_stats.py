from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional, Dict


@dataclass
class WinRateData:
    wins: int = 0
    total_games: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_games if self.total_games > 0 else 0.0

    @property
    def win_rate_percent(self) -> float:
        return self.win_rate * 100


@dataclass
class PlayerWinRateStats:
    player_id: int
    role_stats: Dict[str, Dict[int, "WinRateData"]] = field(default_factory=dict)

    def get_win_rate(self, role: str, room_id: Optional[int] = None) -> float:
        if role not in self.role_stats:
            return 0.0

        if room_id is not None:
            if room_id in self.role_stats[role]:
                return self.role_stats[role][room_id].win_rate
            return 0.0

        total_wins = 0
        total_games = 0
        for stats in self.role_stats[role].values():
            total_wins += stats.wins
            total_games += stats.total_games

        return total_wins / total_games if total_games > 0 else 0.0

    def get_all_win_rates(self) -> Dict[str, float]:
        return {role: self.get_win_rate(role) for role in self.role_stats}

    def add_game_result(self, role: str, room_id: int, is_win: bool):
        if role not in self.role_stats:
            self.role_stats[role] = {}

        if room_id not in self.role_stats[role]:
            self.role_stats[role][room_id] = WinRateData(wins=0, total_games=0)

        stats = self.role_stats[role][room_id]
        stats.total_games += 1
        if is_win:
            stats.wins += 1

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "role_stats": {
                role: {
                    str(room_id): {
                        "wins": stats.wins,
                        "total_games": stats.total_games,
                        "win_rate": stats.win_rate,
                    }
                    for room_id, stats in rooms.items()
                }
                for role, rooms in self.role_stats.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerWinRateStats":
        stats = cls(player_id=data["player_id"])
        for role, rooms in data.get("role_stats", {}).items():
            stats.role_stats[role] = {}
            for room_id_str, room_data in rooms.items():
                room_id = int(room_id_str)
                stats.role_stats[role][room_id] = WinRateData(
                    wins=room_data["wins"], total_games=room_data["total_games"]
                )
        return stats

    def collect_total(self) -> tuple[int, int]:
        total_wins = 0
        total_games = 0
        for room_stats in self.role_stats.values():
            for stats in room_stats.values():
                total_wins += stats.wins
                total_games += stats.total_games

        return total_wins, total_games

    def __str__(self):
        total_wins, total_games = self.collect_total()
        if total_games == 0:
            return "Данных пока нет\n"

        role_win_rates = self.get_all_win_rates()
        message = f"\tЗаписанных игр - {total_games}, побед - {total_wins}, общий процент побед - {100 * total_wins / total_games:.1f}\n"
        for role, rate in role_win_rates.items():
            message += f"\t{role}: {100 * rate:.1f}\n"

        return message
