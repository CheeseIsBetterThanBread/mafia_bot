import pytest
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

from utils.win_rate_db import (
    WinRateDatabase,
    Game,
    Player,
    Team,
    PlayerWinRateStats,
)


class TestWinRateDatabaseInit:
    def test_win_rate_stats_init_with_string_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)
            assert db._db_path == db_path
            assert Path(db_path).exists()
        finally:
            os.unlink(db_path)

    def test_win_rate_stats_init_with_path_object(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)

        try:
            db = WinRateDatabase(db_path)
            assert db._db_path == str(db_path)
            assert db_path.exists()
        finally:
            os.unlink(db_path)

    def test_win_rate_stats_init_creates_directory_if_not_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "subdir" / "test.db"
            assert not db_path.parent.exists()

            _ = WinRateDatabase(db_path)

            assert db_path.parent.exists()
            assert db_path.exists()

    def test_win_rate_stats_init_creates_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            _ = WinRateDatabase(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='win_rate_info'
                """)
                assert cursor.fetchone() is not None

                cursor.execute("PRAGMA table_info(win_rate_info)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]

                assert "player_id" in column_names
                assert "role" in column_names
                assert "room_id" in column_names
                assert "wins" in column_names
                assert "total_games" in column_names
        finally:
            os.unlink(db_path)


class TestLoadWinRateByPlayers:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    (1, "Мафия", 1, 5, 10),
                    (1, "Комиссар", 1, 3, 8),
                    (1, "Мирный житель", 1, 2, 7),
                    (2, "Мафия", 1, 4, 6),
                    (2, "Комиссар", 2, 6, 10),
                ],
            )
            conn.commit()

        yield db, db_path

        os.unlink(db_path)

    def test_win_rate_stats_load_win_rate_single_player(self, db_with_data):
        db, _ = db_with_data

        result = db.load_win_rate_by_players([1])

        assert 1 in result
        assert isinstance(result[1], PlayerWinRateStats)
        assert result[1].player_id == 1
        assert len(result[1].role_stats) == 3

        assert "Мафия" in result[1].role_stats
        assert 1 in result[1].role_stats["Мафия"]
        assert result[1].role_stats["Мафия"][1].wins == 5
        assert result[1].role_stats["Мафия"][1].total_games == 10

    def test_win_rate_stats_load_win_rate_multiple_players(self, db_with_data):
        db, _ = db_with_data

        result = db.load_win_rate_by_players([1, 2])

        assert len(result) == 2
        assert result[1].player_id == 1
        assert result[2].player_id == 2
        assert len(result[1].role_stats) == 3
        assert len(result[2].role_stats) == 2

    def test_win_rate_stats_load_win_rate_nonexistent_player(self, db_with_data):
        db, _ = db_with_data

        result = db.load_win_rate_by_players([999])

        assert 999 in result
        assert isinstance(result[999], PlayerWinRateStats)
        assert result[999].player_id == 999
        assert result[999].role_stats == {}

    def test_win_rate_stats_load_win_rate_empty_list(self, db_with_data):
        db, _ = db_with_data

        result = db.load_win_rate_by_players([])

        assert result == {}


class TestUpdateWinRateInfo:
    @pytest.fixture
    def db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)
        yield db

        os.unlink(db_path)

    @pytest.fixture
    def mock_game(self):
        game = Mock(spec=Game)
        game.current_preset = Mock()

        player1 = Player(user_id=1, name="Player1", number=1)
        player1.role = "Мафия"

        player2 = Player(user_id=2, name="Player2", number=2)
        player2.role = "Шериф"

        player3 = Player(user_id=3, name="Player3", number=3)
        player3.role = "Мирный житель"

        player4 = Player(user_id=4, name="Player4", number=4)
        player4.role = "Двуликий"

        game.players = {1: player1, 2: player2, 3: player3, 4: player4}

        return game

    @pytest.mark.parametrize("found,win_count", [(False, 0), (True, 1)])
    def test_win_rate_stats_update_win_rate_info_mafia_win(
        self, db, mock_game, found, win_count
    ):
        two_face = mock_game.players[4]
        two_face.found_mafia = found
        with patch("utils.win_rate_db.get_room_id", return_value=1):
            db.update_win_rate_info(mock_game, Team.MAFIA)

            results = db.load_win_rate_by_players([1, 2, 3, 4])

            assert results[1].role_stats["Мафия"][1].wins == 1
            assert results[1].role_stats["Мафия"][1].total_games == 1

            assert results[2].role_stats["Шериф"][1].wins == 0
            assert results[2].role_stats["Шериф"][1].total_games == 1

            assert results[3].role_stats["Мирный житель"][1].wins == 0
            assert results[3].role_stats["Мирный житель"][1].total_games == 1

            assert results[4].role_stats["Двуликий"][1].wins == win_count
            assert results[4].role_stats["Двуликий"][1].total_games == 1

    def test_win_rate_stats_update_win_rate_info_citizen_win(self, db, mock_game):
        with patch("utils.win_rate_db.get_room_id", return_value=1):
            db.update_win_rate_info(mock_game, Team.CITIZEN)

            results = db.load_win_rate_by_players([1, 2, 3])

            assert results[1].role_stats["Мафия"][1].wins == 0
            assert results[1].role_stats["Мафия"][1].total_games == 1

            assert results[2].role_stats["Шериф"][1].wins == 1
            assert results[2].role_stats["Шериф"][1].total_games == 1

            assert results[3].role_stats["Мирный житель"][1].wins == 1
            assert results[3].role_stats["Мирный житель"][1].total_games == 1

    def test_win_rate_stats_update_win_rate_info_uses_room_id(self, db, mock_game):
        with patch("utils.win_rate_db.get_room_id", return_value=42):
            db.update_win_rate_info(mock_game, Team.MAFIA)

            results = db.load_win_rate_by_players([1])
            assert 42 in results[1].role_stats["Мафия"]

    def test_win_rate_stats_update_win_rate_info_multiple_games(self, db, mock_game):
        with patch("utils.win_rate_db.get_room_id", return_value=1):
            db.update_win_rate_info(mock_game, Team.MAFIA)

            db.update_win_rate_info(mock_game, Team.CITIZEN)

            results = db.load_win_rate_by_players([1])

            assert results[1].role_stats["Мафия"][1].wins == 1
            assert results[1].role_stats["Мафия"][1].total_games == 2


class TestDeletePlayerInfo:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    (1, "Мафия", 1, 5, 10),
                    (1, "Комиссар", 1, 3, 8),
                    (2, "Мафия", 1, 4, 6),
                ],
            )
            conn.commit()

        yield db, db_path

        os.unlink(db_path)

    def test_win_rate_stats_delete_player_info_existing(self, db_with_data):
        db, db_path = db_with_data

        db.delete_player_info(1)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM win_rate_info WHERE player_id = ?", (1,)
            )
            count1 = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM win_rate_info WHERE player_id = ?", (2,)
            )
            count2 = cursor.fetchone()[0]

        assert count1 == 0
        assert count2 == 1

    def test_win_rate_stats_delete_player_info_nonexistent(self, db_with_data):
        db, db_path = db_with_data

        db.delete_player_info(999)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM win_rate_info")
            count = cursor.fetchone()[0]

        assert count == 3


class TestGetTeamWinRatesByRoom:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    (1, "Мафия", 1, 5, 10),
                    (2, "Мафия", 1, 6, 12),
                    (3, "Шериф", 1, 3, 8),
                    (4, "Мирный житель", 1, 4, 10),
                    (5, "Двуликий", 1, 2, 5),
                    (6, "Мафия", 2, 1, 5),
                    (7, "Шериф", 2, 7, 10),
                    (8, "Мирный житель", 2, 6, 9),
                ],
            )
            conn.commit()

        yield db, db_path

        os.unlink(db_path)

    def test_win_rate_stats_get_team_win_rates_by_room_room1(self, db_with_data):
        db, _ = db_with_data

        result = db.get_team_win_rates_by_room(1)

        assert Team.MAFIA in result
        assert abs(result[Team.MAFIA] - 13 / 27) < 0.0001

        assert Team.CITIZEN in result
        assert abs(result[Team.CITIZEN] - 7 / 18) < 0.0001

    def test_win_rate_stats_get_team_win_rates_by_room_room2(self, db_with_data):
        db, _ = db_with_data

        result = db.get_team_win_rates_by_room(2)

        assert Team.MAFIA in result
        assert result[Team.MAFIA] == 0.2

        assert Team.CITIZEN in result
        assert abs(result[Team.CITIZEN] - 13 / 19) < 0.0001

    def test_win_rate_stats_get_team_win_rates_by_room_no_data(self, db_with_data):
        db, _ = db_with_data

        result = db.get_team_win_rates_by_room(999)

        assert result == {}

    def test_win_rate_stats_get_team_win_rates_by_room_empty_teams(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)
            result = db.get_team_win_rates_by_room(1)
            assert result == {}
        finally:
            os.unlink(db_path)


class TestIsPlayerWinner:
    @pytest.mark.parametrize("role", ["Мафия", "Дон", "Ниндзя", "Адвокат"])
    def test_win_rate_stats_mafia_winner(self, role):
        player = Player(1, "name", 1)
        player.role = role
        assert WinRateDatabase._is_player_winner(player, Team.MAFIA) is True

    @pytest.mark.parametrize(
        "role", ["Мирный житель", "Бессмертный", "Вор", "Доктор", "Тула", "Шериф"]
    )
    def test_win_rate_stats_citizen_winner(self, role):
        player = Player(1, "name", 1)
        player.role = role
        assert WinRateDatabase._is_player_winner(player, Team.CITIZEN) is True

    @pytest.mark.parametrize("role", ["Маньяк с бинтами", "Маньяк без бинтов"])
    def test_win_rate_stats_maniac_winner(self, role):
        player = Player(1, "name", 1)
        player.role = role
        assert WinRateDatabase._is_player_winner(player, Team.MANIAC) is True

    @pytest.mark.parametrize("found", [False, True])
    def test_win_rate_stats_two_face_winner(self, found):
        player = Player(1, "name", 1)
        player.role = "Двуликий"
        player.found_mafia = found
        assert WinRateDatabase._is_player_winner(player, Team.MAFIA) is found

    def test_win_rate_stats_unknown_role(self):
        player = Player(1, "name", 1)
        player.role = "unknown"
        with pytest.raises(KeyError):
            WinRateDatabase._is_player_winner(player, Team.MAFIA)


class TestUpdatePlayerWinRate:
    @pytest.fixture
    def db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)
        yield db

        os.unlink(db_path)

    def test_win_rate_stats_update_new_player(self, db):
        player = Player(1, "name", 1)
        player.role = "Мафия"
        db._update_player_win_rate(player, 1, Team.MAFIA)

        results = db.load_win_rate_by_players([1])

        assert results[1].role_stats["Мафия"][1].wins == 1
        assert results[1].role_stats["Мафия"][1].total_games == 1

    def test_win_rate_stats_update_existing_player(self, db):
        player = Player(1, "name", 1)
        player.role = "Мафия"
        db._update_player_win_rate(player, 1, Team.MAFIA)

        db._update_player_win_rate(player, 1, Team.CITIZEN)

        results = db.load_win_rate_by_players([1])

        assert results[1].role_stats["Мафия"][1].wins == 1
        assert results[1].role_stats["Мафия"][1].total_games == 2

    def test_win_rate_stats_update_different_rooms(self, db):
        player = Player(1, "name", 1)
        player.role = "Мафия"
        db._update_player_win_rate(player, 1, Team.MAFIA)
        db._update_player_win_rate(player, 2, Team.MAFIA)

        results = db.load_win_rate_by_players([1])

        assert results[1].role_stats["Мафия"][1].wins == 1
        assert results[1].role_stats["Мафия"][1].total_games == 1
        assert results[1].role_stats["Мафия"][2].wins == 1
        assert results[1].role_stats["Мафия"][2].total_games == 1

    def test_win_rate_stats_update_different_roles(self, db):
        player = Player(1, "name", 1)
        player.role = "Мафия"
        db._update_player_win_rate(player, 1, Team.MAFIA)
        player.role = "Шериф"
        db._update_player_win_rate(player, 1, Team.CITIZEN)

        results = db.load_win_rate_by_players([1])

        assert results[1].role_stats["Мафия"][1].wins == 1
        assert results[1].role_stats["Мафия"][1].total_games == 1
        assert results[1].role_stats["Шериф"][1].wins == 1
        assert results[1].role_stats["Шериф"][1].total_games == 1


class TestLoadPlayerWinRate:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = WinRateDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    (1, "Мафия", 1, 5, 10),
                    (1, "Мафия", 2, 3, 6),
                    (1, "Комиссар", 1, 2, 5),
                ],
            )
            conn.commit()

        yield db, db_path

        os.unlink(db_path)

    def test_win_rate_stats_load_existing_player(self, db_with_data):
        db, _ = db_with_data

        stats = db._load_player_win_rate(1)

        assert stats.player_id == 1
        assert len(stats.role_stats) == 2

        assert "Мафия" in stats.role_stats
        assert len(stats.role_stats["Мафия"]) == 2
        assert stats.role_stats["Мафия"][1].wins == 5
        assert stats.role_stats["Мафия"][1].total_games == 10
        assert stats.role_stats["Мафия"][2].wins == 3
        assert stats.role_stats["Мафия"][2].total_games == 6

        assert "Комиссар" in stats.role_stats
        assert stats.role_stats["Комиссар"][1].wins == 2
        assert stats.role_stats["Комиссар"][1].total_games == 5

    def test_win_rate_stats_load_nonexistent_player(self, db_with_data):
        db, _ = db_with_data

        stats = db._load_player_win_rate(999)

        assert stats.player_id == 999
        assert stats.role_stats == {}


class TestEdgeCases:
    def test_win_rate_stats_load_large_number_of_players(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                data = []
                for i in range(1000):
                    data.append((i, "Мафия", 1, i % 10, 10))
                cursor.executemany(
                    """
                    INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    data,
                )
                conn.commit()

            # Загружаем всех игроков
            player_ids = list(range(1000))
            result = db.load_win_rate_by_players(player_ids)

            assert len(result) == 1000
            for i in range(1000):
                assert i in result
                assert result[i].role_stats["Мафия"][1].wins == i % 10
        finally:
            os.unlink(db_path)

    def test_win_rate_stats_get_team_win_rates_with_no_games(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO win_rate_info (player_id, role, room_id, wins, total_games)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (1, "Мафия", 1, 0, 0),
                )
                conn.commit()

            result = db.get_team_win_rates_by_room(1)
            assert result == {}
        finally:
            os.unlink(db_path)

    def test_win_rate_stats_special_characters_in_roles(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)

            with patch(
                "utils.win_rate_db.ROLE_TO_TEAM", {"Роль_с_символами!": Team.MAFIA}
            ):
                player = Player(1, "name", 1)
                player.role = "Роль_с_символами!"
                db._update_player_win_rate(player, 1, Team.MAFIA)

                result = db.load_win_rate_by_players([1])
                assert "Роль_с_символами!" in result[1].role_stats
        finally:
            os.unlink(db_path)

    def test_win_rate_stats_concurrent_access(self):
        import threading

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = WinRateDatabase(db_path)
            errors = []

            def worker(worker_id):
                try:
                    for i in range(10):
                        player = Player(worker_id, "name", worker_id)
                        player.role = "Мафия"
                        db._update_player_win_rate(player, 1, Team.MAFIA)
                        result = db.load_win_rate_by_players([worker_id])
                        assert (
                            result[worker_id].role_stats["Мафия"][1].total_games
                            == i + 1
                        )
                except Exception as e:
                    errors.append(str(e))

            threads = []
            for i in range(10):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            assert len(errors) == 0
        finally:
            os.unlink(db_path)


class TestGlobalWinRateDatabase:
    def test_win_rate_stats_win_rate_database_is_singleton(self):
        from utils.win_rate_db import win_rate_database as db1
        from utils.win_rate_db import win_rate_database as db2

        assert db1 is db2

    def test_win_rate_stats_win_rate_database_initialized_with_correct_path(self):
        from utils.win_rate_db import win_rate_database, DB_PATH

        assert win_rate_database._db_path == str(DB_PATH)
