from collections import deque

import pytest
from unittest.mock import patch, Mock

from tests.conftest import MockOperations

from engine.game_state import Game, GameState, MAFIA_TEAM, ROOM_PRESETS


class TestGameInitialization:
    def test_game_initialization(self):
        chat_id = -100123456789
        game_counter = 42

        game = Game(chat_id, game_counter)

        assert game.chat_id == chat_id
        assert game.game_number == game_counter
        assert game.state == GameState.LOBBY
        assert game.players == {}
        assert game.players_by_number == {}
        assert game.day_count == 0
        assert game.day_starter_num == 1
        assert game.nominated == []
        assert game.speech_queue == deque()
        assert game.defense_queue == deque()
        assert game.current_speech_task is None
        assert game.voting_queue == deque()
        assert game.current_votes == {}
        assert game.vote_history == {}
        assert game.balance_players == []
        assert game.revote_count == 0
        assert game.night_actions == {}
        assert game.expected_night_actors == {}
        assert game.current_preset == []
        assert game.mafia_team == MAFIA_TEAM

    def test_game_different_chat_ids(self):
        game1 = Game(-100, 1)
        game2 = Game(-200, 1)

        assert game1.chat_id != game2.chat_id

    def test_game_incremental_counters(self):
        game1 = Game(-100, 1)
        game2 = Game(-100, 2)

        assert game1.game_number != game2.game_number


class TestPlayerManagement:
    @pytest.fixture
    def game(self):
        return Game(-100123456, 1)

    def test_add_player_success(self, game):
        assert game.add_player(123, "Test Player")
        assert 123 in game.players
        assert game.players[123].user_id == 123
        assert game.players[123].name == "Test Player"
        assert game.players[123].number == 1
        assert game.players_by_number[1] == game.players[123]

    def test_add_multiple_players(self, game):
        assert game.add_player(1, "Player 1")
        assert game.add_player(2, "Player 2")
        assert game.add_player(3, "Player 3")

        assert len(game.players) == 3
        assert game.players[1].number == 1
        assert game.players[2].number == 2
        assert game.players[3].number == 3

        assert game.players_by_number[1].user_id == 1
        assert game.players_by_number[2].user_id == 2
        assert game.players_by_number[3].user_id == 3

    def test_add_duplicate_player(self, game):
        assert game.add_player(123, "Test Player")
        result = game.add_player(123, "Another Name")

        assert result is False
        assert len(game.players) == 1
        assert game.players[123].name == "Test Player"

    def test_get_alive_players_initial(self, game):
        assert game.add_player(1, "Player 1")
        assert game.add_player(2, "Player 2")
        assert game.add_player(3, "Player 3")

        alive = game.get_alive_players()

        assert len(alive) == 3
        assert all(p.is_alive for p in alive)

    def test_get_alive_players_after_deaths(self, game):
        assert game.add_player(1, "Player 1")
        assert game.add_player(2, "Player 2")
        assert game.add_player(3, "Player 3")

        game.players[2].is_alive = False

        alive = game.get_alive_players()

        assert len(alive) == 2
        assert game.players[1] in alive
        assert game.players[3] in alive
        assert game.players[2] not in alive

    def test_player_numbers_sequential(self, game):
        assert game.add_player(100, "First")
        assert game.add_player(200, "Second")
        assert game.add_player(300, "Third")

        assert game.players[100].number == 1
        assert game.players[200].number == 2
        assert game.players[300].number == 3

    def test_players_by_number_mapping(self, game):
        assert game.add_player(10, "Ten")
        assert game.add_player(20, "Twenty")

        assert game.players_by_number[1].user_id == 10
        assert game.players_by_number[2].user_id == 20

        assert game.players_by_number[1] == game.players[10]
        assert game.players_by_number[2] == game.players[20]


class TestQueueBuilding:
    @pytest.fixture
    def game_with_players(self):
        game = Game(-100, 1)
        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
        return game

    def test_build_daily_queue_with_alive_players(self, game_with_players):
        queue = game_with_players.build_daily_queue()

        assert len(queue) == 5
        assert isinstance(queue, deque)
        assert game_with_players.day_starter_num in range(1, 6)

    def test_build_daily_queue_rotation(self, game_with_players):
        queue1 = game_with_players.build_daily_queue()

        game_with_players.day_starter_num += 1
        queue2 = game_with_players.build_daily_queue()

        assert queue1 != queue2

    def test_build_daily_queue_empty_players(self, game_with_players):
        for player in game_with_players.players.values():
            player.is_alive = False

        queue = game_with_players.build_daily_queue()

        assert queue == deque()

    def test_build_daily_queue_single_player(self, game_with_players):
        for player in list(game_with_players.players.values())[1:]:
            player.is_alive = False

        game_with_players.day_starter_num = len(game_with_players.players.values()) + 1
        queue = game_with_players.build_daily_queue()

        assert len(queue) == 1
        assert game_with_players.day_starter_num == 1

    def test_build_daily_queue_preserves_starter(self, game_with_players):
        initial_starter = game_with_players.day_starter_num

        _ = game_with_players.build_daily_queue()

        assert game_with_players.day_starter_num == initial_starter

    @patch("engine.game_state.rotate_queue")
    def test_build_daily_queue_calls_rotate(self, mock_rotate, game_with_players):
        mock_rotate.return_value = (deque([4, 5, 3]), 1)

        queue = game_with_players.build_daily_queue()

        mock_rotate.assert_called_once()
        assert mock_rotate.call_args[0][1] == game_with_players.day_starter_num
        assert queue == deque([4, 5, 3])
        assert game_with_players.day_starter_num == 1


class TestRolePreset:
    @pytest.fixture
    def game(self):
        game = Game(-100, 1)
        game.simulation = False
        return game

    @patch("engine.game_state.choice")
    def test_set_preset_with_valid_count(self, mock_choice, game):
        mock_preset = ["mafia", "commissar", "civilian"]
        mock_choice.return_value = mock_preset

        result = game.set_preset(10)

        mock_choice.assert_called_once_with(ROOM_PRESETS[10])
        assert result == mock_preset
        assert game.current_preset == mock_preset

    @patch("engine.game_state.choice")
    def test_set_preset_different_counts(self, mock_choice, game):
        max_count = max(ROOM_PRESETS.keys())

        test_counts = [5, 8, 10, 12, 15]

        for count in test_counts:
            mock_preset = ["test_role"]
            mock_choice.return_value = mock_preset

            expected_answer = mock_preset.copy()
            if count > max_count:
                expected_answer += ["Мирный житель"] * (count - max_count)

            result = game.set_preset(count)

            mock_choice.assert_called_with(ROOM_PRESETS[min(count, max_count)])
            assert result == expected_answer

    @patch("engine.game_state.choice")
    def test_set_preset_returns_copy(self, mock_choice, game):
        original_preset = ["mafia", "don"]
        mock_choice.return_value = original_preset

        result = game.set_preset(10)

        result.append("new_role")

        assert result != original_preset
        assert len(game.current_preset) == len(original_preset) + 1


class TestSpeechTime:
    @staticmethod
    def patch_time(speech_time, minimal_time, maximal_time):
        return MockOperations(
            "engine.game_state",
            SECONDS_PER_PLAYER=speech_time,
            SPEECH_LOWER_BOUND=minimal_time,
            SPEECH_UPPER_BOUND=maximal_time,
        )

    @pytest.fixture
    def game_with_players(self):
        game = Game(-100, 1)
        game.simulation = False
        for i in range(1, 11):
            game.add_player(i, f"Player {i}")
        return game

    def test_calculate_speech_time_normal(self, game_with_players):
        with self.patch_time(5, 10, 60):
            time = game_with_players.calculate_speech_time()

            from engine.game_state import SECONDS_PER_PLAYER

            assert (
                time == len(game_with_players.get_alive_players()) * SECONDS_PER_PLAYER
            )

    def test_calculate_speech_time_below_lower_bound(self, game_with_players):
        with self.patch_time(1, 10, 60):
            with patch.object(game_with_players, "get_alive_players") as mock_alive:
                mock_alive.return_value = [Mock() for _ in range(5)]

                time = game_with_players.calculate_speech_time()

                from engine.game_state import SPEECH_LOWER_BOUND

                assert time == SPEECH_LOWER_BOUND

    def test_calculate_speech_time_above_upper_bound(self, game_with_players):
        with self.patch_time(10, 10, 60):
            with patch.object(game_with_players, "get_alive_players") as mock_alive:
                mock_alive.return_value = [Mock() for _ in range(20)]

                time = game_with_players.calculate_speech_time()

                from engine.game_state import SPEECH_UPPER_BOUND

                assert time == SPEECH_UPPER_BOUND

    def test_calculate_speech_time_exactly_lower_bound(self, game_with_players):
        with self.patch_time(2, 10, 60):
            with patch.object(game_with_players, "get_alive_players") as mock_alive:
                mock_alive.return_value = [Mock() for _ in range(5)]

                time = game_with_players.calculate_speech_time()

                from engine.game_state import SPEECH_LOWER_BOUND

                assert time == SPEECH_LOWER_BOUND

    def test_calculate_speech_time_exactly_upper_bound(self, game_with_players):
        with self.patch_time(6, 10, 60):
            with patch.object(game_with_players, "get_alive_players") as mock_alive:
                mock_alive.return_value = [Mock() for _ in range(10)]

                time = game_with_players.calculate_speech_time()

                from engine.game_state import SPEECH_UPPER_BOUND

                assert time == SPEECH_UPPER_BOUND

    def test_calculate_speech_time_changes_with_alive_count(self, game_with_players):
        with self.patch_time(5, 10, 60):
            from engine.game_state import SECONDS_PER_PLAYER

            for player in list(game_with_players.players.values())[5:]:
                player.is_alive = False
            time1 = game_with_players.calculate_speech_time()
            expected1 = len(game_with_players.get_alive_players()) * SECONDS_PER_PLAYER

            for player in list(game_with_players.players.values())[3:5]:
                player.is_alive = False
            time2 = game_with_players.calculate_speech_time()
            expected2 = len(game_with_players.get_alive_players()) * SECONDS_PER_PLAYER

            assert time1 == expected1
            assert time2 == expected2
            assert time1 > time2


class TestGameStateTransitions:
    def test_initial_state(self):
        game = Game(-100, 1)
        assert game.state == GameState.LOBBY

    def test_state_change(self):
        game = Game(-100, 1)

        game.state = GameState.DAY
        assert game.state == GameState.DAY

        game.state = GameState.NIGHT
        assert game.state == GameState.NIGHT

        game.state = GameState.FINISHED
        assert game.state == GameState.FINISHED

    def test_all_states_exist(self):
        expected_states = [
            "LOBBY",
            "DAY",
            "DEFENSE",
            "VOTING",
            "BALANCE",
            "REVOTE",
            "NIGHT_THIEF",
            "NIGHT",
            "FINISHED",
        ]

        for state in expected_states:
            assert hasattr(GameState, state)
            assert isinstance(getattr(GameState, state), GameState)


class TestGameAttributes:
    @pytest.fixture
    def game(self):
        game = Game(-100, 1)
        game.simulation = False
        return game

    def test_night_actions_initialization(self, game):
        assert game.night_actions == {}
        assert isinstance(game.night_actions, dict)

    def test_expected_night_actors_initialization(self, game):
        assert game.expected_night_actors == {}
        assert isinstance(game.expected_night_actors, dict)

    def test_vote_history_initialization(self, game):
        assert game.vote_history == {}
        assert isinstance(game.vote_history, dict)

    def test_current_votes_initialization(self, game):
        assert game.current_votes == {}
        assert isinstance(game.current_votes, dict)

    def test_balance_players_initialization(self, game):
        assert game.balance_players == []
        assert isinstance(game.balance_players, list)

    def test_revote_count_initialization(self, game):
        assert game.revote_count == 0
        assert isinstance(game.revote_count, int)

    def test_day_count_increments(self, game):
        assert game.day_count == 0

        game.day_count += 1
        assert game.day_count == 1

        game.day_count += 1
        assert game.day_count == 2


class TestEdgeCases:
    def test_get_alive_players_when_all_dead(self):
        game = Game(-100, 1)
        game.simulation = False

        game.add_player(1, "Player 1")
        game.add_player(2, "Player 2")

        game.players[1].is_alive = False
        game.players[2].is_alive = False

        alive = game.get_alive_players()

        assert alive == []
        assert len(alive) == 0

    def test_build_daily_queue_after_all_dead(self):
        game = Game(-100, 1)
        game.simulation = False

        game.add_player(1, "Player 1")
        game.players[1].is_alive = False

        queue = game.build_daily_queue()

        assert queue == deque()

    @patch("engine.game_state.ROOM_PRESETS", {5: ["preset1", "preset2"]})
    def test_set_preset_random_selection(self):
        game = Game(-100, 1)
        game.simulation = False

        results = set()
        with patch("engine.game_state.choice") as mock_choice:
            mock_choice.side_effect = [["preset1"], ["preset2"], ["preset1"]]

            for _ in range(3):
                result = game.set_preset(5)
                results.add(tuple(result))

        assert len(results) >= 2

    def test_large_number_of_players(self):
        game = Game(-100, 1)
        game.simulation = False

        for i in range(1, 101):
            game.add_player(i, f"Player {i}")

        assert len(game.players) == 100
        assert len(game.players_by_number) == 100

        alive = game.get_alive_players()
        assert len(alive) == 100


class TestIntegration:
    def test_full_player_lifecycle(self):
        game = Game(-100, 1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")

        assert len(game.get_alive_players()) == 5

        game.players[3].is_alive = False

        alive = game.get_alive_players()
        assert len(alive) == 4
        assert 3 not in [p.user_id for p in alive]

        game.day_starter_num = 3
        queue = game.build_daily_queue()

        assert len(queue) == 4
        assert game.day_starter_num == 3 + 1

    def test_multiple_games_independent(self):
        game1 = Game(-100, 1)
        game1.simulation = False
        game2 = Game(-200, 2)
        game2.simulation = False

        assert game1.add_player(1, "Game1 Player")
        assert game2.add_player(1, "Game2 Player")

        assert len(game1.players) == 1
        assert len(game2.players) == 1
        assert game1.players[1].name == "Game1 Player"
        assert game2.players[1].name == "Game2 Player"

        game1.state = GameState.DAY
        assert game1.state == GameState.DAY
        assert game2.state == GameState.LOBBY
