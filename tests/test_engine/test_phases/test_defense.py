from collections import deque

import pytest
from unittest.mock import AsyncMock, patch

from engine.phases.defense import (
    start_defense,
    next_defense_speaker,
    EventBus,
    Game,
    GameState
)


class TestStartDefense:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        return game

    @pytest.mark.asyncio
    async def test_without_nominated(self, mock_bus, game):
        game.nominated = []

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)

            mock_bus.emit.assert_called_once()
            response = mock_bus.emit.call_args[0][0]
            assert response.chat_id == game.chat_id
            assert "Никто не выставлен" in response.text
            assert response.is_valid

            mock_night.assert_called_once_with(mock_bus, game)

            assert game.state != GameState.DEFENSE

    @pytest.mark.asyncio
    async def test_with_nominated_players(self, mock_bus, game):
        game.nominated = [2, 4]

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)
            mock_night.assert_not_called()

        assert game.state == GameState.DEFENSE
        assert len(game.defense_queue) == 2
        assert game.defense_queue[0].number == 2
        assert game.defense_queue[1].number == 4

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "Выставлены игроки: [2, 4]" in response.text
        assert "Первым говорит Игрок №2" in response.text
        assert response.is_valid

    @pytest.mark.asyncio
    async def test_with_single_nominated(self, mock_bus, game):
        game.nominated = [3]

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)
            mock_night.assert_not_called()

        assert game.state == GameState.DEFENSE
        assert len(game.defense_queue) == 1
        assert game.defense_queue[0].number == 3

        response = mock_bus.emit.call_args[0][0]
        assert "Выставлены игроки: [3]" in response.text
        assert "Первым говорит Игрок №3" in response.text

    @pytest.mark.asyncio
    async def test_preserve_order(self, mock_bus, game):
        game.nominated = [5, 1, 3, 2, 4]

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)
            mock_night.assert_not_called()

        expected_order = [5, 1, 3, 2, 4]
        for i, expected_num in enumerate(expected_order):
            assert game.defense_queue[i].number == expected_num


class TestNextDefenseSpeaker:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
            game.players[i].is_glued = False

        game.nominated = [2, 3, 4]
        game.state = GameState.DEFENSE
        game.defense_queue = deque([
            game.players_by_number[n]
            for n in game.nominated
        ])

        return game

    @pytest.mark.asyncio
    async def test_remove_first_and_announce_next(self, mock_bus, game):
        initial_queue = list(game.defense_queue)
        first_speaker = game.defense_queue[0]

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        assert first_speaker not in game.defense_queue
        assert len(game.defense_queue) == len(initial_queue) - 1

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert f"Очередь оправдываться Игрока №{game.defense_queue[0].number}" in response.text

    @pytest.mark.asyncio
    async def test_skip_glued_players(self, mock_bus, game):
        second_player = game.defense_queue[1]
        second_player.is_glued = True

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        assert mock_bus.emit.call_count >= 2

        first_call = mock_bus.emit.call_args_list[0][0][0]
        assert f"{second_player.number} заклеен Вором и пропускает свою оправдательную речь" in first_call.text

    @pytest.mark.asyncio
    async def test_no_defense_queue(self, mock_bus, game):
        game.defense_queue = deque()

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_last_speaker_starts_voting(self, mock_bus, game):
        game.defense_queue = deque([list(game.players.values())[2]])

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)

            mock_bus.emit.assert_called_once()
            response = mock_bus.emit.call_args[0][0]
            assert "Все оправдательные речи окончены" in response.text

            mock_voting.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_empty_queue_after_removing_glued(self, mock_bus, game):
        for player in game.defense_queue:
            player.is_glued = True

        defense_length = len(game.defense_queue)

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)

            assert mock_bus.emit.call_count == defense_length

            last_call = mock_bus.emit.call_args_list[-1][0][0]
            assert "Все оправдательные речи окончены" in last_call.text

            mock_voting.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_maintain_order(self, mock_bus, game):
        original_order = [p.number for p in game.defense_queue]

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        new_order = [p.number for p in game.defense_queue]
        assert new_order == original_order[1:]

    @pytest.mark.asyncio
    async def test_announce_correctly(self, mock_bus, game):
        second_speaker = game.defense_queue[1]

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        response = mock_bus.emit.call_args[0][0]
        assert f"🗣 Очередь оправдываться Игрока №{second_speaker.number}" in response.text

    @pytest.mark.asyncio
    async def test_multiple_calls(self, mock_bus, game):
        initial_length = len(game.defense_queue)

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            for i in range(initial_length):
                await next_defense_speaker(mock_bus, game)

            assert len(game.defense_queue) == 0

            mock_voting.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_emit_correct_message_for_glued(self, mock_bus, game):
        glued_player = game.defense_queue[1]
        glued_player.is_glued = True

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            await next_defense_speaker(mock_bus, game)
            mock_voting.assert_not_called()

        first_response = mock_bus.emit.call_args_list[0][0][0]
        assert f"🤐 Игрок №{glued_player.number} заклеен Вором" in first_response.text
        assert "пропускает свою оправдательную речь" in first_response.text


class TestIntegrationDefensePhases:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        for i in range(1, 4):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        game.nominated = [1, 2]

        return game

    @pytest.mark.asyncio
    async def test_full_defense_cycle(self, mock_bus, game):
        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)
            mock_night.assert_not_called()

        assert game.state == GameState.DEFENSE
        assert len(game.defense_queue) == 2

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            initial_queue_length = len(game.defense_queue)

            for i in range(initial_queue_length):
                await next_defense_speaker(mock_bus, game)

            mock_voting.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_defense_cycle_with_glued_players(self, mock_bus, game):
        game.players[2].is_glued = True

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)
            mock_night.assert_not_called()

        with patch('engine.phases.voting.start_voting', new_callable=AsyncMock) as mock_voting:
            required_calls = len(game.defense_queue)
            for i in range(required_calls - 1):
                await next_defense_speaker(mock_bus, game)

            mock_voting.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_no_defense_when_no_nominated(self, mock_bus, game):
        game.nominated = []

        with patch('engine.phases.night.start_night', new_callable=AsyncMock) as mock_night:
            await start_defense(mock_bus, game)

            mock_night.assert_called_once_with(mock_bus, game)
            assert game.state != GameState.DEFENSE
