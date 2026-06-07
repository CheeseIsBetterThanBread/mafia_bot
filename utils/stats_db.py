from pathlib import Path
from typing import Union
import os
import sqlite3

from config.settings import DB_PATH

from game_info.player_stats import PlayerRoleStats


class PlayerStatsDatabase:
    def __init__(self, db_path: Union[str, Path]):
        if isinstance(db_path, str):
            self._db_path = db_path
        if isinstance(db_path, Path):
            self._db_path = str(db_path)

        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_role_balance (
                    player_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    balance REAL NOT NULL DEFAULT 0,

                    PRIMARY KEY (
                        player_id,
                        role
                    )
                )
                """)

            conn.commit()

    def load_player_stats(self, player_ids: list[int]) -> dict[int, PlayerRoleStats]:
        result: dict[int, PlayerRoleStats] = {}
        for player_id in player_ids:
            result[player_id] = self._load_player_stats_by_id(player_id)

        return result

    def save_player_stats(self, stats: dict[int, PlayerRoleStats]) -> None:
        for player_id, player_stats in stats.items():
            self._save_player_stats_by_id(player_id, player_stats)

    def delete_player_stats(self, player_id: int) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE
                FROM player_role_balance
                WHERE player_id = ?
                """,
                (player_id,),
            )

            conn.commit()

    def _load_player_stats_by_id(self, player_id: int) -> PlayerRoleStats:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    role,
                    balance
                FROM player_role_balance
                WHERE player_id = ?
                """,
                (player_id,),
            )

            rows = cursor.fetchall()

        if not rows:
            return PlayerRoleStats()

        role_balance = {role: balance for role, balance in rows}

        return PlayerRoleStats.from_dict(role_balance)

    def _save_player_stats_by_id(self, player_id: int, stats: PlayerRoleStats) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            for role, balance in stats.role_balance.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE
                    INTO player_role_balance (
                        player_id,
                        role,
                        balance
                    )
                    VALUES (?, ?, ?)
                    """,
                    (player_id, role, balance),
                )

            conn.commit()


roles_database = PlayerStatsDatabase(DB_PATH)
