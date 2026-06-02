import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *


class TestGameHandlers:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
        engine.games = {}
        engine.create_game = Mock()
        return engine

    @pytest.fixture
    def dispatcher(self, mock_engine):
        return EventDispatcher(mock_engine)

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
        return game

    @pytest.mark.asyncio
    async def test_start_game_success(self, dispatcher, mock_engine):
        query = StartGameQuery(QueryType.START_GAME, [1, 2], -100, 1, "group")

        await dispatcher._handle_start_game(query)

        mock_engine.create_game.assert_called_once_with(-100)
        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithOptions)
        assert "Регистрация на Мафию" in response.text
        assert response.candidates == [("✋ Присоединиться", "join_game")]

    @pytest.mark.asyncio
    async def test_start_game_non_admin(self, dispatcher, mock_engine):
        query = StartGameQuery(QueryType.START_GAME, [1, 2], -100, 3, "group")

        await dispatcher._handle_start_game(query)

        mock_engine.create_game.assert_not_called()
        assert mock_engine.games == {}

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "только создателю" in response.text.lower()

    @pytest.mark.asyncio
    async def test_start_game_private(self, dispatcher, mock_engine):
        query = StartGameQuery(QueryType.START_GAME, [1, 2], -100, 1, "private")

        await dispatcher._handle_start_game(query)

        mock_engine.create_game.assert_not_called()
        assert mock_engine.games == {}

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "нужно в группе" in response.text.lower()

    @pytest.mark.asyncio
    async def test_start_game_already_running(self, dispatcher, mock_engine, game):
        query = StartGameQuery(QueryType.START_GAME, [1, 2], -100, 1, "group")

        game.state = GameState.DAY
        mock_engine.games = {-100: game}

        await dispatcher._handle_start_game(query)

        mock_engine.create_game.assert_not_called()
        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра в этом чате уже запущена" in response.text

    @pytest.mark.asyncio
    async def test_start_game_finished_allows_new(self, dispatcher, mock_engine, game):
        query = StartGameQuery(QueryType.START_GAME, [1, 2], -100, 1, "group")

        game.state = GameState.FINISHED
        mock_engine.games = {-100: game}

        await dispatcher._handle_start_game(query)

        mock_engine.create_game.assert_called_once_with(-100)

    @pytest.mark.asyncio
    async def test_join_game_success(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY

        query = JoinQuery(QueryType.JOIN_GAME, [1, 2], -100, 13, Mock(), "NewPlayer")

        mock_engine.get_game.return_value = game

        await dispatcher._handle_join_game(query)

        assert 13 in game.players
        assert game.players[13].name == "NewPlayer"

        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithAlert)
        assert response.is_valid is True
        assert "Зарегистрировано: 6 чел" in response.text

    @pytest.mark.asyncio
    async def test_join_game_no_lobby(self, dispatcher, mock_engine):
        query = JoinQuery(QueryType.JOIN_GAME, [1, 2], -100, 5, Mock(), "NewPlayer")

        mock_engine.get_game.return_value = None

        await dispatcher._handle_join_game(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert isinstance(response, ResponseWithAlert)
        assert response.is_valid is False
        assert "Нет открытого лобби" in response.text

    @pytest.mark.asyncio
    async def test_join_game_wrong_state(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY

        query = JoinQuery(QueryType.JOIN_GAME, [1, 2], -100, 5, Mock(), "NewPlayer")

        mock_engine.get_game.return_value = game

        await dispatcher._handle_join_game(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нет открытого лобби" in response.text

    @pytest.mark.asyncio
    async def test_join_game_already_registered(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY
        game.players[5] = Mock()

        query = JoinQuery(QueryType.JOIN_GAME, [1, 2], -100, 5, Mock(), "NewPlayer")

        mock_engine.get_game.return_value = game

        await dispatcher._handle_join_game(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Ты уже зарегистрирован" in response.text

    @pytest.mark.asyncio
    async def test_run_success(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY
        game.game_number = 1

        query = RunQuery(QueryType.RUN, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch("engine.dispatcher.shuffle", return_value=None) as mock_shuffle:
            with patch(
                "engine.dispatcher.start_day", new_callable=AsyncMock
            ) as mock_start_day:
                await dispatcher._handle_run(query)

                assert game.current_preset is not None
                mock_shuffle.assert_called_once()
                mock_start_day.assert_called_once_with(dispatcher.bus, game)

                assert dispatcher.bus.emit.call_count >= len(game.players) + 2

    @pytest.mark.asyncio
    async def test_run_non_admin(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY

        query = RunQuery(QueryType.RUN, [1, 2], -100, 10)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_run(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "только создателю" in response.text.lower()

    @pytest.mark.asyncio
    async def test_run_wrong_player_count(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY

        query = RunQuery(QueryType.RUN, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch("engine.dispatcher.ROOM_PRESETS", {6: [], 8: [], 10: []}):
            await dispatcher._handle_run(query)

            response = dispatcher.bus.emit.call_args[0][0]
            assert "нужно другое количество игроков" in response.text

    @pytest.mark.asyncio
    async def test_run_no_game(self, dispatcher, mock_engine):
        query = RunQuery(QueryType.RUN, [1, 2], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_run(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.DAY,
            GameState.DEFENSE,
            GameState.VOTING,
            GameState.BALANCE,
            GameState.REVOTE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_run_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = RunQuery(QueryType.RUN, [1, 2], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_run(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_sends_mafia_team_info(self, dispatcher, mock_engine, game):
        game.state = GameState.LOBBY
        game.game_number = 1
        game.mafia_team = ["Мафия", "Дон"]
        roles = ["Мафия", "Мирный житель", "Дон", "Мирный житель", "Мирный житель"]

        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        query = RunQuery(QueryType.RUN, [1], -100, 1)
        mock_engine.get_game.return_value = game

        game.set_preset = Mock()
        game.set_preset.return_value = roles

        with patch("engine.dispatcher.shuffle"):
            with patch("engine.dispatcher.start_day", new_callable=AsyncMock):
                await dispatcher._handle_run(query)

        mafia_messages = []
        for call_args in dispatcher.bus.emit.call_args_list:
            response = call_args[0][0]
            if isinstance(response, ResponseBase) and "Твоя команда" in response.text:
                mafia_messages.append(response)

        assert len(mafia_messages) == 2

    @pytest.mark.asyncio
    async def test_start_night_success(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.current_speech_task = None

        query = StartNightQuery(QueryType.START_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.start_night", new_callable=AsyncMock
        ) as mock_night:
            await dispatcher._handle_start_night(query)

            mock_night.assert_called_once_with(dispatcher.bus, game)
            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "Принудительно наступает Ночь" in response.text

    @pytest.mark.asyncio
    async def test_start_night_non_admin(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.current_speech_task = None

        query = StartNightQuery(QueryType.START_NIGHT, [1], -100, 2)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.start_night", new_callable=AsyncMock
        ) as mock_night:
            await dispatcher._handle_start_night(query)

            mock_night.assert_not_called()

            dispatcher.bus.emit.assert_called_once()
            response = dispatcher.bus.emit.call_args[0][0]
            assert "только создателю" in response.text.lower()

    @pytest.mark.asyncio
    async def test_start_night_cancels_speech_task(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        mock_task = AsyncMock()
        mock_task.done = Mock()
        mock_task.done.return_value = False
        game.current_speech_task = mock_task

        query = StartNightQuery(QueryType.START_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch("engine.dispatcher.start_night", new_callable=AsyncMock):
            await dispatcher._handle_start_night(query)

            mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [GameState.LOBBY, GameState.FINISHED, GameState.NIGHT_THIEF, GameState.NIGHT],
    )
    async def test_start_night_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = StartNightQuery(QueryType.START_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.start_night", new_callable=AsyncMock
        ) as mock_night:
            await dispatcher._handle_start_night(query)

            mock_night.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_night_from_night_state(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT

        query = SkipNightQuery(QueryType.SKIP_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.resolve_night", new_callable=AsyncMock
        ) as mock_resolve:
            await dispatcher._handle_skip_night(query)

            mock_resolve.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_skip_night_from_thief_state(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT_THIEF
        game.players[1].role = "Вор"

        query = SkipNightQuery(QueryType.SKIP_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.start_night_others", new_callable=AsyncMock
        ) as mock_others:
            await dispatcher._handle_skip_night(query)

            response = dispatcher.bus.emit.call_args[0][0]
            assert "Вор никого не заклеил" in response.text
            mock_others.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_skip_night_non_admin(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT

        query = SkipNightQuery(QueryType.SKIP_NIGHT, [1], -100, 2)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.resolve_night", new_callable=AsyncMock
        ) as mock_resolve:
            await dispatcher._handle_skip_night(query)

            mock_resolve.assert_not_called()

            dispatcher.bus.emit.assert_called_once()
            response = dispatcher.bus.emit.call_args[0][0]
            assert "только создателю" in response.text.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.VOTING,
            GameState.BALANCE,
            GameState.REVOTE,
            GameState.FINISHED,
        ],
    )
    async def test_skip_night_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = SkipNightQuery(QueryType.SKIP_NIGHT, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.resolve_night", new_callable=AsyncMock
        ) as mock_resolve:
            with patch(
                "engine.dispatcher.start_night_others", new_callable=AsyncMock
            ) as mock_others:
                await dispatcher._handle_skip_night(query)

                mock_resolve.assert_not_called()
                mock_others.assert_not_called()
