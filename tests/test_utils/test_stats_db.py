import pytest
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from game_info.player_stats import PlayerRoleStats
from utils.stats_db import PlayerStatsDatabase


class TestPlayerStatsDatabaseInit:
    def test_role_stats_init_with_string_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)
            assert db._db_path == db_path
            assert Path(db_path).exists()
        finally:
            os.unlink(db_path)

    def test_role_stats_init_with_path_object(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)

        try:
            db = PlayerStatsDatabase(db_path)
            assert db._db_path == str(db_path)
            assert db_path.exists()
        finally:
            os.unlink(db_path)

    def test_role_stats_init_creates_directory_if_not_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "subdir" / "test.db"
            assert not db_path.parent.exists()

            _ = PlayerStatsDatabase(db_path)

            assert db_path.parent.exists()
            assert db_path.exists()

    def test_role_stats_init_creates_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            _ = PlayerStatsDatabase(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='player_role_balance'
                """)
                assert cursor.fetchone() is not None

                cursor.execute("PRAGMA table_info(player_role_balance)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]

                assert "player_id" in column_names
                assert "role" in column_names
                assert "balance" in column_names
        finally:
            os.unlink(db_path)

    def test_init_does_not_recreate_existing_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db1 = PlayerStatsDatabase(db_path)

            stats = PlayerRoleStats()
            stats.role_balance = {"Мафия": 0.5}
            db1.save_player_stats({1: stats})

            db2 = PlayerStatsDatabase(db_path)

            loaded = db2.load_player_stats([1])
            assert loaded[1].role_balance["Мафия"] == 0.5
        finally:
            os.unlink(db_path)


class TestLoadPlayerStats:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = PlayerStatsDatabase(db_path)

        stats1 = PlayerRoleStats()
        stats1.role_balance = {"Мафия": 0.8, "Комиссар": -0.2}

        stats2 = PlayerRoleStats()
        stats2.role_balance = {"Мирный житель": 0.5}

        db.save_player_stats({1: stats1, 2: stats2})

        yield db, db_path

        os.unlink(db_path)

    def test_role_stats_load_player_stats_single_player(self, db_with_data):
        db, _ = db_with_data

        result = db.load_player_stats([1])

        assert 1 in result
        assert isinstance(result[1], PlayerRoleStats)
        assert result[1].role_balance["Мафия"] == 0.8
        assert result[1].role_balance["Комиссар"] == -0.2

    def test_role_stats_load_player_stats_multiple_players(self, db_with_data):
        db, _ = db_with_data

        result = db.load_player_stats([1, 2])

        assert len(result) == 2
        assert result[1].role_balance["Мафия"] == 0.8
        assert result[2].role_balance["Мирный житель"] == 0.5

    def test_role_stats_load_player_stats_nonexistent_player(self, db_with_data):
        db, _ = db_with_data

        result = db.load_player_stats([999])

        assert 999 in result
        assert isinstance(result[999], PlayerRoleStats)
        assert set(result[999].role_balance.values()) == {0.0}

    def test_role_stats_load_player_stats_mixed_existing_and_new(self, db_with_data):
        db, _ = db_with_data

        result = db.load_player_stats([1, 999])

        assert len(result) == 2
        assert result[1].role_balance["Мафия"] == 0.8
        assert set(result[999].role_balance.values()) == {0.0}

    def test_role_stats_load_player_stats_empty_list(self, db_with_data):
        db, _ = db_with_data

        result = db.load_player_stats([])

        assert result == {}


class TestSavePlayerStats:
    @pytest.fixture
    def empty_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = PlayerStatsDatabase(db_path)

        yield db, db_path

        os.unlink(db_path)

    def test_role_stats_save_player_stats_new_player(self, empty_db):
        db, db_path = empty_db

        stats = PlayerRoleStats()
        stats.role_balance = {"Мафия": 0.9, "Комиссар": 0.1}

        db.save_player_stats({1: stats})

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ?",
                (1,),
            )
            rows = cursor.fetchall()

        assert len(rows) == 2
        role_balance = {role: balance for role, balance in rows}
        assert role_balance["Мафия"] == 0.9
        assert role_balance["Комиссар"] == 0.1

    def test_role_stats_save_player_stats_update_existing(self, empty_db):
        db, db_path = empty_db

        stats1 = PlayerRoleStats()
        stats1.role_balance = {"Мафия": 0.5}
        db.save_player_stats({1: stats1})

        stats2 = PlayerRoleStats()
        stats2.role_balance = {"Мафия": 0.8, "Комиссар": 0.2}
        db.save_player_stats({1: stats2})

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ?",
                (1,),
            )
            rows = cursor.fetchall()

        assert len(rows) == 2
        role_balance = {role: balance for role, balance in rows}
        assert role_balance["Мафия"] == 0.8
        assert role_balance["Комиссар"] == 0.2

    def test_role_stats_save_player_stats_multiple_players(self, empty_db):
        db, db_path = empty_db

        stats1 = PlayerRoleStats()
        stats1.role_balance = {"Мафия": 0.7}

        stats2 = PlayerRoleStats()
        stats2.role_balance = {"Комиссар": 0.3}

        db.save_player_stats({1: stats1, 2: stats2})

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ?",
                (1,),
            )
            rows1 = cursor.fetchall()

            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ?",
                (2,),
            )
            rows2 = cursor.fetchall()

        assert len(rows1) == 1
        assert rows1[0][0] == "Мафия"
        assert rows1[0][1] == 0.7

        assert len(rows2) == 1
        assert rows2[0][0] == "Комиссар"
        assert rows2[0][1] == 0.3

    def test_role_stats_save_player_stats_empty_balance(self, empty_db):
        db, db_path = empty_db

        stats = PlayerRoleStats()
        stats.role_balance = {}

        db.save_player_stats({1: stats})

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM player_role_balance WHERE player_id = ?", (1,)
            )
            count = cursor.fetchone()[0]

        assert count == 0


class TestDeletePlayerStats:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = PlayerStatsDatabase(db_path)

        stats1 = PlayerRoleStats()
        stats1.role_balance = {"Мафия": 0.8, "Комиссар": 0.2}

        stats2 = PlayerRoleStats()
        stats2.role_balance = {"Мирный житель": 0.5}

        db.save_player_stats({1: stats1, 2: stats2})

        yield db, db_path

        os.unlink(db_path)

    def test_role_stats_delete_player_stats_existing(self, db_with_data):
        db, db_path = db_with_data

        db.delete_player_stats(1)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM player_role_balance WHERE player_id = ?", (1,)
            )
            count1 = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM player_role_balance WHERE player_id = ?", (2,)
            )
            count2 = cursor.fetchone()[0]

        assert count1 == 0
        assert count2 == 1

    def test_role_stats_delete_player_stats_nonexistent(self, db_with_data):
        db, db_path = db_with_data

        db.delete_player_stats(999)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM player_role_balance WHERE player_id = ?", (1,)
            )
            count = cursor.fetchone()[0]

        assert count == 2

    def test_role_stats_delete_player_stats_twice(self, db_with_data):
        db, _ = db_with_data

        db.delete_player_stats(1)
        db.delete_player_stats(1)

        result = db.load_player_stats([1])
        assert set(result[1].role_balance.values()) == {0.0}


class TestLoadPlayerStatsById:
    @pytest.fixture
    def db_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = PlayerStatsDatabase(db_path)

        stats = PlayerRoleStats()
        stats.role_balance = {"Мафия": 0.7, "Комиссар": -0.3, "Мирный житель": 0.1}
        db.save_player_stats({1: stats})

        yield db, db_path

        os.unlink(db_path)

    def test_role_stats_load_existing_player(self, db_with_data):
        db, _ = db_with_data

        stats = db._load_player_stats_by_id(1)

        assert isinstance(stats, PlayerRoleStats)
        assert stats.role_balance["Мафия"] == 0.7
        assert stats.role_balance["Комиссар"] == -0.3
        assert stats.role_balance["Мирный житель"] == 0.1

    def test_role_stats_load_nonexistent_player(self, db_with_data):
        db, _ = db_with_data

        stats = db._load_player_stats_by_id(999)

        assert isinstance(stats, PlayerRoleStats)
        assert set(stats.role_balance.values()) == {0.0}

    def test_role_stats_load_player_with_no_roles(self, db_with_data):
        db, db_path = db_with_data

        stats = db._load_player_stats_by_id(2)

        assert isinstance(stats, PlayerRoleStats)
        assert set(stats.role_balance.values()) == {0.0}


class TestSavePlayerStatsById:
    @pytest.fixture
    def empty_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = PlayerStatsDatabase(db_path)

        yield db, db_path

        os.unlink(db_path)

    def test_role_stats_save_new_player(self, empty_db):
        db, db_path = empty_db

        stats = PlayerRoleStats()
        stats.role_balance = {"Мафия": 0.9}

        db._save_player_stats_by_id(1, stats)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ?",
                (1,),
            )
            rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0] == ("Мафия", 0.9)

    def test_role_stats_update_existing_player(self, empty_db):
        db, db_path = empty_db

        stats1 = PlayerRoleStats()
        stats1.role_balance = {"Мафия": 0.5}
        db._save_player_stats_by_id(1, stats1)

        stats2 = PlayerRoleStats()
        stats2.role_balance = {"Мафия": 0.8, "Комиссар": 0.2}
        db._save_player_stats_by_id(1, stats2)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, balance FROM player_role_balance WHERE player_id = ? ORDER BY role",
                (1,),
            )
            rows = cursor.fetchall()

        assert len(rows) == 2
        role_balance = {role: balance for role, balance in rows}
        assert role_balance["Мафия"] == 0.8
        assert role_balance["Комиссар"] == 0.2

    def test_role_stats_save_empty_balance(self, empty_db):
        db, db_path = empty_db

        stats = PlayerRoleStats()
        stats.role_balance = {}

        db._save_player_stats_by_id(1, stats)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM player_role_balance WHERE player_id = ?", (1,)
            )
            count = cursor.fetchone()[0]

        assert count == 0


class TestEdgeCases:
    def test_role_stats_load_large_number_of_players(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)

            stats_batch = {}
            for i in range(1000):
                stats = PlayerRoleStats()
                stats.role_balance = {f"role_{j}": i * 0.1 for j in range(5)}
                stats_batch[i] = stats

            db.save_player_stats(stats_batch)

            player_ids = list(range(1000))
            result = db.load_player_stats(player_ids)

            assert len(result) == 1000
            for i in range(1000):
                assert i in result
        finally:
            os.unlink(db_path)

    def test_role_stats_save_and_load_floating_point_precision(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)

            stats = PlayerRoleStats()
            stats.role_balance = {"Мафия": 1 / 3, "Комиссар": 0.123456789}

            db.save_player_stats({1: stats})

            loaded = db.load_player_stats([1])

            assert abs(loaded[1].role_balance["Мафия"] - 1 / 3) < 0.000001
            assert loaded[1].role_balance["Комиссар"] == 0.123456789
        finally:
            os.unlink(db_path)

    def test_role_stats_special_characters_in_role_names(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)

            stats = PlayerRoleStats()
            stats.role_balance = {
                "Роль с пробелом": 0.5,
                "Роль_с_подчеркиванием": 0.3,
                "Роль-с-дефисом": 0.2,
            }

            db.save_player_stats({1: stats})

            loaded = db.load_player_stats([1])

            assert loaded[1].role_balance["Роль с пробелом"] == 0.5
            assert loaded[1].role_balance["Роль_с_подчеркиванием"] == 0.3
            assert loaded[1].role_balance["Роль-с-дефисом"] == 0.2
        finally:
            os.unlink(db_path)

    def test_role_stats_concurrent_access(self):
        import threading

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)
            results = []
            errors = []

            def worker(worker_id):
                try:
                    for i in range(10):
                        stats = PlayerRoleStats()
                        stats.role_balance = {f"role_{worker_id}": i}
                        db.save_player_stats({worker_id: stats})

                        loaded = db.load_player_stats([worker_id])
                        assert worker_id in loaded
                        results.append(True)
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
            assert len(results) == 100  # 10 workers * 10 iterations
        finally:
            os.unlink(db_path)


class TestDatabaseConnection:
    def test_role_stats_connection_handles_error_gracefully(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)

            with open(db_path, "w") as f:
                f.write("corrupted data")

            with pytest.raises(sqlite3.DatabaseError):
                db.load_player_stats([1])
        finally:
            os.unlink(db_path)

    def test_role_stats_context_manager_closes_connection(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = PlayerStatsDatabase(db_path)

            stats = PlayerRoleStats()
            stats.role_balance = {"Мафия": 0.5}
            db.save_player_stats({1: stats})

            db.load_player_stats([1])
        finally:
            os.unlink(db_path)


class TestGlobalRolesDatabase:
    def test_role_stats_roles_database_is_singleton(self):
        from utils.stats_db import roles_database as db1
        from utils.stats_db import roles_database as db2

        assert db1 is db2

    def test_role_stats_roles_database_initialized_with_correct_path(self):
        from utils.stats_db import roles_database, DB_PATH

        assert roles_database._db_path == str(DB_PATH)
