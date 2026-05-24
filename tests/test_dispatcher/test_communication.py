import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *


class TestSpeechHandlers:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
        engine.games = {}
        return engine

    @pytest.fixture
    def dispatcher(self, mock_engine):
        return EventDispatcher(mock_engine)

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        for i in range(1, 4):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
        game.speech_queue = None
        game.defense_queue = None
        game.current_speech_task = None
        return game

    @pytest.mark.asyncio
    async def test_handle_speech_day_success(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[1], game.players[2]]
        game.calculate_speech_time = Mock(return_value=30)

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch('asyncio.create_task') as mock_create_task:
            await dispatcher._handle_speech(query)

            dispatcher.bus.emit.assert_called()
            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "ваши 30 секунд пошли" in response.text
            assert "/nominate" in response.text

            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_speech_defense_success(self, dispatcher, mock_engine, game):
        game.state = GameState.DEFENSE
        game.defense_queue = [game.players[1], game.players[2]]
        game.calculate_speech_time = Mock(return_value=45)

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch('asyncio.create_task'):
            await dispatcher._handle_speech(query)

            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "ваши 45 секунд на оправдание пошли" in response.text
            assert "/nominate" not in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [
        GameState.LOBBY,
        GameState.VOTING,
        GameState.BALANCE,
        GameState.REVOTE,
        GameState.NIGHT_THIEF,
        GameState.NIGHT,
        GameState.FINISHED
    ])
    async def test_handle_speech_invalid_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 12039)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_speech(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.DAY, GameState.DEFENSE])
    async def test_handle_speech_no_player(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 12039)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_speech(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_speech_wrong_turn_day(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[2], game.players[3]]

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_speech(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь говорить" in response.text

    @pytest.mark.asyncio
    async def test_handle_speech_wrong_turn_defense(self, dispatcher, mock_engine, game):
        game.state = GameState.DEFENSE
        game.defense_queue = [game.players[2], game.players[3]]

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_speech(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Сейчас не ваша очередь оправдываться" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.DAY, GameState.DEFENSE])
    async def test_handle_speech_already_speaking(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.speech_queue = [game.players[1], game.players[2]]
        game.defense_queue = [game.players[1], game.players[2]]
        game.current_speech_task = AsyncMock()
        game.current_speech_task.done = Mock(return_value=False)

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_speech(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Вы уже выступаете" in response.text

    @pytest.mark.asyncio
    async def test_handle_speech_no_game(self, dispatcher, mock_engine):
        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_speech(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.DAY, GameState.DEFENSE])
    async def test_handle_speech_creates_timer_task(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.speech_queue = [game.players[2]]
        game.defense_queue = [game.players[2]]
        game.calculate_speech_time = Mock(return_value=30)

        query = SpeechRelatedQuery(QueryType.SPEECH, [1], -100, 2)
        mock_engine.get_game.return_value = game

        with patch('asyncio.create_task') as mock_create_task:
            mock_create_task.return_value = AsyncMock()

            await dispatcher._handle_speech(query)

            mock_create_task.assert_called_once()
            assert game.current_speech_task is not None

    @pytest.mark.asyncio
    async def test_handle_end_speech_day(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[1], game.players[2]]
        game.current_speech_task = AsyncMock()
        game.current_speech_task.done = Mock(return_value=False)
        game.current_speech_task.cancel = Mock()

        query = SpeechRelatedQuery(QueryType.END_SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.next_speaker', new_callable=AsyncMock) as mock_next:
            await dispatcher._handle_end_speech(query)

            game.current_speech_task.cancel.assert_called_once()
            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "завершил свою речь" in response.text
            mock_next.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_handle_end_speech_defense(self, dispatcher, mock_engine, game):
        game.state = GameState.DEFENSE
        game.defense_queue = [game.players[1], game.players[2]]
        game.current_speech_task = AsyncMock()
        game.current_speech_task.done = Mock(return_value=False)
        game.current_speech_task.cancel = Mock()

        query = SpeechRelatedQuery(QueryType.END_SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.next_defense_speaker', new_callable=AsyncMock) as mock_next:
            await dispatcher._handle_end_speech(query)

            game.current_speech_task.cancel.assert_called_once()
            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "завершил свою оправдательную речь" in response.text
            mock_next.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_handle_end_speech_no_game(self, dispatcher, mock_engine):
        query = SpeechRelatedQuery(QueryType.END_SPEECH, [1], -100, 12039)
        mock_engine.get_game.return_value = None

        await dispatcher._handle_end_speech(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.DAY, GameState.DEFENSE])
    async def test_handle_end_speech_no_player(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = SpeechRelatedQuery(QueryType.END_SPEECH, [1], -100, 12039)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_end_speech(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_end_speech_not_speaking(self, dispatcher, mock_engine, game):
        game.state = GameState.DAY
        game.speech_queue = [game.players[2]]

        query = SpeechRelatedQuery(QueryType.END_SPEECH, [1], -100, 1)
        mock_engine.get_game.return_value = game

        await dispatcher._handle_end_speech(query)

        dispatcher.bus.emit.assert_not_called()


class TestMafiaChatHandlers:
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.bus = AsyncMock()
        engine.get_game = Mock()
        engine.games = {}
        return engine

    @pytest.fixture
    def dispatcher(self, mock_engine):
        return EventDispatcher(mock_engine)

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        for i in range(1, 5):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
        game.mafia_team = ["Мафия", "Дон"]
        game.state = GameState.NIGHT
        return game

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_success(self, dispatcher, mock_engine, game, state):
        game.state = state
        game.players[1].role = "Мафия"
        game.players[2].role = "Дон"
        game.players[3].role = "Мирный житель"

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [3], 1, 1, "Hello mafia")

        await dispatcher._handle_mafia_chat(query)

        assert dispatcher.bus.emit.call_count >= 1

        calls = dispatcher.bus.emit.call_args_list
        sent_to_don = False
        for call_args in calls:
            response = call_args[0][0]
            if response.chat_id == 2 and "Hello mafia" in response.text:
                sent_to_don = True
                break
        assert sent_to_don

    @pytest.mark.asyncio
    async def test_mafia_chat_no_active_game(self, dispatcher, mock_engine):
        mock_engine.games = {}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_not_in_mafia_team(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мирный житель"
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_player_dead(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мафия"
        game.players[1].is_alive = False
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        dispatcher.bus.emit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_glued(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мафия"
        game.players[1].is_glued = True
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Вы заклеены Вором" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_only_alive_sends(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мафия"
        game.players[2].role = "Дон"
        game.players[2].is_alive = False
        game.players[3].role = "Мафия"
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        calls = dispatcher.bus.emit.call_args_list
        sent_to = [call_args[0][0].chat_id for call_args in calls]

        assert 3 in sent_to
        assert 2 not in sent_to

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [GameState.NIGHT_THIEF, GameState.NIGHT])
    async def test_mafia_chat_last_mafia(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мафия"
        game.players[2].role = "Дон"
        game.players[2].is_alive = False
        game.players[3].role = "Мафия"
        game.players[3].is_alive = False
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "остались единственным живым мафиози" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [
        GameState.LOBBY,
        GameState.DAY,
        GameState.DEFENSE,
        GameState.VOTING,
        GameState.BALANCE,
        GameState.REVOTE,
        GameState.FINISHED
    ])
    async def test_mafia_chat_invalid_state(self, dispatcher, mock_engine, game, state):
        game.players[1].role = "Мафия"
        game.state = state

        mock_engine.games = {-100: game}

        query = MafiaChatQuery(QueryType.MAFIA_CHAT, [1], 1, 1, "Hello")

        await dispatcher._handle_mafia_chat(query)

        dispatcher.bus.emit.assert_not_called()
