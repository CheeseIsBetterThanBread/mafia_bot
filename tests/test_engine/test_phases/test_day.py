from collections import deque

import pytest
from unittest.mock import AsyncMock, patch

from engine.phases.day import start_day, next_speaker, EventBus, Game, GameState


class TestStartDay:
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
            game.players[i].has_nominated = True

        return game

    @pytest.mark.asyncio
    async def test_first_day(self, mock_bus, game):
        game.day_count = 0
        game.day_starter_num = 1

        await start_day(mock_bus, game)

        assert game.state == GameState.DAY
        assert game.day_count == 1
        assert game.revote_count == 0

        for player in game.players.values():
            assert player.has_nominated is False

        assert len(game.speech_queue) == 5

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert response.chat_id == game.chat_id
        assert "Наступает День 1" in response.text
        assert "Первым говорит Игрок №1" in response.text
        assert response.is_valid

    @pytest.mark.asyncio
    async def test_subsequent_day_with_alive_next(self, mock_bus, game):
        game.day_count = 2
        game.day_starter_num = 2

        await start_day(mock_bus, game)

        assert game.day_count == 3
        assert game.day_starter_num == 3

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "Наступает День 3" in response.text
        assert "Первым говорит Игрок №3" in response.text

    @pytest.mark.asyncio
    async def test_subsequent_day_with_dead_next(self, mock_bus, game):
        game.day_count = 2
        game.day_starter_num = 2

        game.players[3].is_alive = False

        await start_day(mock_bus, game)

        assert game.day_count == 3
        assert game.day_starter_num == 4

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "Наступает День 3" in response.text
        assert "Первым говорит Игрок №4" in response.text

    @pytest.mark.asyncio
    async def test_starter_cycles_to_beginning(self, mock_bus, game):
        game.day_count = 2
        game.day_starter_num = 5

        await start_day(mock_bus, game)

        assert game.day_starter_num == 1

    @pytest.mark.asyncio
    async def test_all_dead(self, mock_bus, game):
        for player in game.players.values():
            player.is_alive = False

        await start_day(mock_bus, game)

        assert game.speech_queue == deque()
        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_nominated_flag(self, mock_bus, game):
        for player in game.players.values():
            player.has_nominated = True

        await start_day(mock_bus, game)

        for player in game.players.values():
            assert player.has_nominated is False

    @pytest.mark.asyncio
    async def test_reset_nominated_list(self, mock_bus, game):
        game.nominated = [1, 2, 3]

        await start_day(mock_bus, game)

        assert game.nominated == []

    @pytest.mark.asyncio
    async def test_reset_revote_count(self, mock_bus, game):
        game.revote_count = 3

        await start_day(mock_bus, game)

        assert game.revote_count == 0


class TestNextSpeaker:
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

        game.speech_queue = game.build_daily_queue()
        return game

    @pytest.mark.asyncio
    async def test_remove_first_and_announce_next(self, mock_bus, game):
        initial_queue = list(game.speech_queue)
        first_speaker = game.speech_queue[0]

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        assert first_speaker not in game.speech_queue
        assert len(game.speech_queue) == len(initial_queue) - 1

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert f"Очередь Игрока №{game.speech_queue[0].number}" in response.text

    @pytest.mark.asyncio
    async def test_skip_glued_players(self, mock_bus, game):
        second_player = list(game.players.values())[(game.day_starter_num - 1) + 1]
        second_player.is_glued = True

        game.speech_queue = game.build_daily_queue()

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        assert mock_bus.emit.call_count >= 2

        first_call = mock_bus.emit.call_args_list[0][0][0]
        assert (
            f"{second_player.number} заклеен Вором и пропускает свою речь"
            in first_call.text
        )

    @pytest.mark.asyncio
    async def test_no_speech_queue(self, mock_bus, game):
        game.speech_queue = deque()

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_last_speaker_starts_defense(self, mock_bus, game):
        game.speech_queue = deque(
            [list(game.players.values())[game.day_starter_num - 1]]
        )

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)

            mock_bus.emit.assert_called_once()
            response = mock_bus.emit.call_args[0][0]
            assert "Все речи окончены" in response.text

            mock_defense.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_empty_queue_after_removing_glued(self, mock_bus, game):
        for player in game.players.values():
            player.is_glued = True

        game.speech_queue = game.build_daily_queue()

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)

            assert mock_bus.emit.call_count == len(game.players)
            last_call = mock_bus.emit.call_args_list[-1][0][0]
            assert "Все речи окончены" in last_call.text

            mock_defense.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_maintain_order(self, mock_bus, game):
        original_order = [p.number for p in game.speech_queue]

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        new_order = [p.number for p in game.speech_queue]
        assert new_order == original_order[1:]

    @pytest.mark.asyncio
    async def test_announce_correctly(self, mock_bus, game):
        second_speaker = game.speech_queue[(game.day_starter_num - 1) + 1]

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        response = mock_bus.emit.call_args[0][0]
        assert f"🗣 Очередь Игрока №{second_speaker.number}" in response.text

    @pytest.mark.asyncio
    async def test_multiple_calls(self, mock_bus, game):
        initial_length = len(game.speech_queue)

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            for i in range(initial_length):
                await next_speaker(mock_bus, game)

            mock_defense.assert_called_once_with(mock_bus, game)

        assert len(game.speech_queue) == 0

    @pytest.mark.asyncio
    async def test_emit_correct_message_for_glued(self, mock_bus, game):
        glued_player = list(game.speech_queue)[(game.day_starter_num - 1) + 1]
        glued_player.is_glued = True

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            await next_speaker(mock_bus, game)
            mock_defense.assert_not_called()

        first_response = mock_bus.emit.call_args_list[0][0][0]
        assert f"🤐 Игрок №{glued_player.number} заклеен Вором" in first_response.text


class TestIntegrationDayPhases:
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

        return game

    @pytest.mark.asyncio
    async def test_full_speech_cycle(self, mock_bus, game):
        await start_day(mock_bus, game)

        assert game.state == GameState.DAY
        assert len(game.speech_queue) == 3

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            initial_queue_length = len(game.speech_queue)

            for i in range(initial_queue_length):
                await next_speaker(mock_bus, game)

            mock_defense.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_speech_cycle_with_glued_players(self, mock_bus, game):
        game.players[2].is_glued = True

        await start_day(mock_bus, game)

        with patch(
            "engine.phases.defense.start_defense", new_callable=AsyncMock
        ) as mock_defense:
            initial_queue_length = len(game.speech_queue)

            for i in range(initial_queue_length - 1):
                await next_speaker(mock_bus, game)

            mock_defense.assert_called_once()

    @pytest.mark.asyncio
    async def test_day_count_increments_correctly(self, mock_bus, game):
        game.day_count = 1

        await start_day(mock_bus, game)

        assert game.day_count == 2

        await start_day(mock_bus, game)

        assert game.day_count == 3
