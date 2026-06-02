import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *

RUNNING_STATES = [
    GameState.DAY,
    GameState.DEFENSE,
    GameState.VOTING,
    GameState.BALANCE,
    GameState.REVOTE,
    GameState.NIGHT_THIEF,
    GameState.NIGHT,
]


class TestInfoHandlers:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
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
            game.players[i].shurikens = i % 3
        game.current_preset = [
            "Мафия",
            "Доктор",
            "Мирный житель",
            "Мирный житель",
            "Мирный житель",
        ]
        return game

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_alive_success(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.players[2].is_alive = False
        game.players[4].is_alive = False

        query = InfoQuery(QueryType.ALIVE, [1], -100, 2)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_alive(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Живые игроки за столом" in response.text
        assert "№1 — Player 1" in response.text
        assert "№3 — Player 3" in response.text
        assert "№5 — Player 5" in response.text
        assert "№2" not in response.text
        assert "№4" not in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_handle_alive_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        mock_engine.get_game.return_value = game

        query = InfoQuery(QueryType.ALIVE, [1], -100, 1)

        await dispatcher._handle_alive(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    async def test_handle_alive_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.ALIVE, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_alive(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_description_success(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state

        query = InfoQuery(QueryType.DESCRIPTION, [1], -100, 2)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.ROLE_DESCRIPTIONS",
            {
                "Мафия": "Mafia description",
                "Доктор": "Doctor description",
                "Мирный житель": "Civilian description",
            },
        ):
            await dispatcher._handle_description(query)

            dispatcher.bus.emit.assert_called_once()
            response = dispatcher.bus.emit.call_args[0][0]
            assert "Справка по ролям" in response.text
            assert "Мафия" in response.text
            assert "Доктор" in response.text
            assert "Мирный житель" in response.text
            assert response.parse_mode == "HTML"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_handle_description_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state

        query = InfoQuery(QueryType.DESCRIPTION, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.ROLE_DESCRIPTIONS",
            {
                "Мафия": "Mafia description",
                "Доктор": "Doctor description",
                "Мирный житель": "Civilian description",
            },
        ):
            await dispatcher._handle_description(query)

            dispatcher.bus.emit.assert_called_once()
            response = dispatcher.bus.emit.call_args[0][0]
            assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_description_unique_roles(
        self, dispatcher, mock_engine, game, state
    ):
        game.current_preset = ["Мафия", "Мафия", "Доктор", "Мирный", "Мирный"]
        game.state = state

        query = InfoQuery(QueryType.DESCRIPTION, [1], -100, 0)
        mock_engine.get_game.return_value = game

        with patch(
            "engine.dispatcher.ROLE_DESCRIPTIONS",
            {"Мафия": "Mafia desc", "Доктор": "Doctor desc", "Мирный": "Civilian desc"},
        ):
            await dispatcher._handle_description(query)

            response = dispatcher.bus.emit.call_args[0][0]
            assert response.text.count("Мафия") == 1
            assert response.text.count("Доктор") == 1
            assert response.text.count("Мирный") == 1

    @pytest.mark.asyncio
    async def test_handle_description_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.DESCRIPTION, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_description(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_roles_success(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.current_preset = ["Мафия", "Доктор", "Мирный", "Шериф", "Дон"]

        query = InfoQuery(QueryType.ROLES, [1], -100, 4)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_roles(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Набор ролей в этой игре" in response.text
        for role in game.current_preset:
            assert role in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_handle_roles_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        game.current_preset = ["Мафия", "Доктор", "Мирный", "Шериф", "Дон"]

        query = InfoQuery(QueryType.ROLES, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_roles(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    async def test_handle_roles_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.ROLES, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_roles(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_nominated_with_nominations(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        game.nominated = [2, 4, 5]

        query = InfoQuery(QueryType.NOMINATED, [1], -100, 8)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominated(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Выставлены: 2, 4, 5" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_handle_nominated_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        game.nominated = [2, 4, 5]

        query = InfoQuery(QueryType.NOMINATED, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominated(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_nominated_empty(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.nominated = []

        query = InfoQuery(QueryType.NOMINATED, [1], -100, 2)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_nominated(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Пока никто не выставлен" in response.text

    @pytest.mark.asyncio
    async def test_handle_nominated_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.NOMINATED, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_nominated(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.VOTING, GameState.REVOTE])
    async def test_handle_voted_in_voting_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        game.current_votes = {2: 3, 3: 1, 4: 2}
        game.vote_history = {1: 2, 2: 2, 3: 3, 4: 4, 5: 2}

        query = InfoQuery(QueryType.VOTED, [1], -100, 4)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_voted(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Текущие результаты" in response.text
        assert "Против №2: 3 голосов" in response.text
        assert "Против №3: 1 голосов" in response.text
        assert "Против №4: 2 голосов" in response.text
        assert "Игрок №1 ➡️ против №2" in response.text
        assert response.parse_mode == "HTML"

    @pytest.mark.asyncio
    async def test_handle_voted_in_balance_state(self, dispatcher, mock_engine, game):
        game.state = GameState.BALANCE
        game.current_votes = {"acquit": 2, "kill": 3, "revote": 1}
        game.vote_history = {
            1: "acquit",
            2: "kill",
            3: "kill",
            4: "revote",
            5: "acquit",
        }

        query = InfoQuery(QueryType.VOTED, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_voted(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Оправдать: 2" in response.text
        assert "Убить всех: 3" in response.text
        assert "Переголосовать: 1" in response.text
        assert "Игрок №1 ➡️ acquit" in response.text
        assert "Игрок №2 ➡️ kill" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state",
        [
            GameState.LOBBY,
            GameState.DAY,
            GameState.DEFENSE,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
            GameState.FINISHED,
        ],
    )
    async def test_handle_voted_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state

        query = InfoQuery(QueryType.VOTED, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_voted(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не идет голосование" in response.text

    @pytest.mark.asyncio
    async def test_handle_voted_no_votes(self, dispatcher, mock_engine, game):
        game.state = GameState.VOTING
        game.current_votes = {2: 0, 3: 0, 4: 0}
        game.vote_history = {}

        query = InfoQuery(QueryType.VOTED, [1], -100, 0)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_voted(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Пока никто не проголосовал" in response.text

    @pytest.mark.asyncio
    async def test_handle_voted_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.VOTED, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_voted(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не идет голосование" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", RUNNING_STATES)
    async def test_handle_status_success(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.players[1].shurikens = 0
        game.players[2].shurikens = 1
        game.players[3].shurikens = 2
        game.players[4].is_alive = False
        game.players[5].shurikens = 0

        query = InfoQuery(QueryType.STATUS, [1], -100, 10)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_status(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Живые игроки за столом" in response.text
        assert "число сюрикенов" in response.text
        assert "№1 — Player 1 - 0" in response.text
        assert "№2 — Player 2 - 1" in response.text
        assert "№3 — Player 3 - 2" in response.text
        assert "№5 — Player 5 - 0" in response.text
        assert "№4" not in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.LOBBY, GameState.FINISHED])
    async def test_handle_status_invalid_state(
        self, dispatcher, mock_engine, game, state
    ):
        game.state = state
        game.players[1].shurikens = 0
        game.players[2].shurikens = 1
        game.players[3].shurikens = 2
        game.players[4].is_alive = False
        game.players[5].shurikens = 0

        query = InfoQuery(QueryType.STATUS, [1], -100, 10)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_status(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text

    @pytest.mark.asyncio
    async def test_handle_status_no_game(self, dispatcher, mock_engine):
        query = InfoQuery(QueryType.STATUS, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_status(query)

        dispatcher.bus.emit.assert_called_once()
        response = dispatcher.bus.emit.call_args[0][0]
        assert "Игра сейчас не идет" in response.text
