import pytest
from unittest.mock import Mock, patch

from connection.event_bus import EventBus
from connection.events import QueryBase

from engine.core import EventDispatcher, Game, GameEngine


class TestGameEngine:
    @pytest.fixture
    def mock_bus(self):
        bus = Mock(spec=EventBus)
        bus.on = Mock(return_value=lambda x: x)
        return bus

    @pytest.fixture
    def engine(self, mock_bus):
        with patch('engine.core.EventDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock(spec=EventDispatcher)
            mock_dispatcher_class.return_value = mock_dispatcher

            engine = GameEngine(mock_bus)

            engine._mock_dispatcher = mock_dispatcher
            engine._mock_dispatcher_class = mock_dispatcher_class

            return engine

    def test_engine_initialization(self, mock_bus):
        with patch('engine.core.EventDispatcher') as mock_dispatcher:
            engine = GameEngine(mock_bus)

            assert engine.bus == mock_bus
            assert engine.games == {}
            assert engine.game_counter == 0
            mock_dispatcher.assert_called_once_with(engine)
            assert isinstance(engine.dispatcher, Mock)

    def test_engine_creates_dispatcher(self, mock_bus):
        with patch('engine.core.EventDispatcher') as mock_dispatcher:
            engine = GameEngine(mock_bus)

            mock_dispatcher.assert_called_once_with(engine)
            assert engine.dispatcher == mock_dispatcher.return_value

    def test_get_game_nonexistent(self, engine):
        chat_id = -100123456789

        game = engine.get_game(chat_id)

        assert game is None
        assert chat_id not in engine.games

    def test_get_game_existing(self, engine):
        chat_id = -100123456789
        engine.create_game(chat_id)

        game = engine.get_game(chat_id)

        assert game is not None
        assert isinstance(game, Game)
        assert game.chat_id == chat_id
        assert engine.games[chat_id] == game

    def test_create_game_first_game(self, engine):
        chat_id = -100123456789
        engine.create_game(chat_id)

        assert len(engine.games) == 1
        assert chat_id in engine.games
        assert engine.game_counter == 1

        game = engine.games[chat_id]
        assert isinstance(game, Game)
        assert game.chat_id == chat_id
        assert game.game_number == 1

    def test_create_game_multiple_games(self, engine):
        chat_ids = [-100111, -100222, -100333]
        for chat_id in chat_ids:
            engine.create_game(chat_id)

        assert len(engine.games) == 3
        assert engine.game_counter == 3

        for i, chat_id in enumerate(chat_ids, 1):
            assert chat_id in engine.games
            assert engine.games[chat_id].game_number == i

    def test_create_game_same_chat_twice(self, engine):
        chat_id = -100123456789
        engine.create_game(chat_id)
        first_game = engine.games[chat_id]

        engine.create_game(chat_id)

        assert len(engine.games) == 1
        assert engine.game_counter == 2
        assert engine.games[chat_id].game_number == 2
        assert engine.games[chat_id] != first_game

    def test_game_counter_increments(self, engine):
        assert engine.game_counter == 0

        engine.create_game(-100)
        assert engine.game_counter == 1

        engine.create_game(-200)
        assert engine.game_counter == 2

        engine.create_game(-300)
        assert engine.game_counter == 3

    def test_multiple_games_different_chats(self, engine):
        chat1 = -100111
        chat2 = -100222

        engine.create_game(chat1)
        engine.create_game(chat2)

        game1 = engine.get_game(chat1)
        game2 = engine.get_game(chat2)

        assert game1 is not game2
        assert game1.chat_id == chat1
        assert game2.chat_id == chat2

        game1.day_count = 5
        assert game2.day_count == 0

    @pytest.mark.asyncio
    async def test_register_subscribes_to_query_base(self, mock_bus):
        with patch('engine.core.EventDispatcher'):
            engine = GameEngine(mock_bus)
            engine.register()

            mock_bus.on.assert_called_once_with(QueryBase)

    @pytest.mark.asyncio
    async def test_register_creates_dispatch_handler(self, mock_bus):
        with patch('engine.core.EventDispatcher'):
            engine = GameEngine(mock_bus)
            engine.register()

            assert mock_bus.on.call_count == 1

            called_types = []
            for args, kwargs in mock_bus.on.call_args_list:
                called_types.append(args[0])
            assert QueryBase in called_types

    @pytest.mark.asyncio
    async def test_dispatch_handler_calls_dispatcher(self):
        class TestQuery(QueryBase):
            pass

        query = TestQuery(
            cmd='/cmd',
            admin_ids=[],
            chat_id=0,
            user_id=-1
        )

        mock_bus = Mock(spec=EventBus)
        handlers = []

        def on_side_effect(_):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect

        with patch('engine.core.EventDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock(spec=EventDispatcher)
            mock_dispatcher_class.return_value = mock_dispatcher

            engine = GameEngine(mock_bus)
            engine.register()

            assert len(handlers) == 1
            dispatch_handler = handlers[0]

            await dispatch_handler(query)
            mock_dispatcher.handle.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_dispatch_handler_preserves_query(self):
        mock_bus = Mock(spec=EventBus)
        captured_handler = None

        def on_side_effect(_):
            def decorator(handler):
                nonlocal captured_handler
                captured_handler = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect

        with patch('engine.core.EventDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock(spec=EventDispatcher)
            mock_dispatcher_class.return_value = mock_dispatcher

            engine = GameEngine(mock_bus)
            engine.register()

            test_query = QueryBase(
                cmd='/cmd',
                admin_ids=[],
                chat_id=108332,
                user_id=92364329
            )

            assert captured_handler
            await captured_handler(test_query)

            mock_dispatcher.handle.assert_called_once_with(test_query)

    def test_game_lifecycle(self, engine):
        chat_id = -100123456789

        engine.create_game(chat_id)
        assert engine.get_game(chat_id) is not None
        assert engine.game_counter == 1

        game = engine.get_game(chat_id)
        assert game.chat_id == chat_id
        assert game.game_number == 1

        engine.create_game(chat_id)
        assert engine.game_counter == 2

        new_game = engine.get_game(chat_id)
        assert new_game.game_number == 2
        assert new_game is not game

    def test_multiple_chats_independent(self, engine):
        chats = [-100111, -100222, -100333]

        for chat_id in chats:
            engine.create_game(chat_id)

        games = [engine.get_game(chat_id) for chat_id in chats]
        assert len(set(games)) == 3

        for i, game in enumerate(games):
            game.day_count = i + 1

        for i, game in enumerate(games):
            assert game.day_count == i + 1

    @pytest.mark.asyncio
    async def test_full_flow_create_and_dispatch(self):
        mock_bus = Mock(spec=EventBus)
        captured_handler = None

        def on_side_effect(_):
            def decorator(handler):
                nonlocal captured_handler
                captured_handler = handler
                return handler

            return decorator

        mock_bus.on.side_effect = on_side_effect

        with patch('engine.core.EventDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock(spec=EventDispatcher)
            mock_dispatcher_class.return_value = mock_dispatcher

            engine = GameEngine(mock_bus)
            engine.register()

            chat_id = -100123456789
            engine.create_game(chat_id)

            assert engine.get_game(chat_id) is not None

            class TestQuery(QueryBase):
                pass

            query = TestQuery(
                cmd='/cmd',
                admin_ids=[],
                chat_id=9827348,
                user_id=17868634
            )

            assert captured_handler
            await captured_handler(query)

            mock_dispatcher.handle.assert_called_once_with(query)

    def test_create_game_with_zero_chat_id(self, engine):
        chat_id = 0
        engine.create_game(chat_id)

        assert chat_id in engine.games
        assert engine.games[chat_id].chat_id == chat_id

    def test_create_game_with_negative_chat_id(self, engine):
        chat_id = -1
        engine.create_game(chat_id)

        assert chat_id in engine.games
        assert engine.games[chat_id].chat_id == chat_id

    def test_get_game_from_empty_engine(self, engine):
        assert engine.get_game(-100) is None
        assert engine.get_game(123) is None

    def test_game_counter_overflow(self, engine):
        for i in range(100):
            engine.create_game(-100 - i)

        assert engine.game_counter == 100
        assert len(engine.games) == 100

    @pytest.mark.asyncio
    async def test_multiple_register_calls(self, mock_bus):
        with patch('engine.dispatcher.EventDispatcher'):
            engine1 = GameEngine(mock_bus)
            engine1.register()

            engine2 = GameEngine(mock_bus)
            engine2.register()

            assert mock_bus.on.call_count == 2


class TestGameEngineEdgeCases:
    @pytest.fixture
    def mock_bus(self):
        return Mock(spec=EventBus)

    def test_create_game_with_same_id_sequence(self, mock_bus):
        with patch('engine.core.EventDispatcher'):
            engine = GameEngine(mock_bus)

        chat_id = -100

        engine.create_game(chat_id)
        engine.create_game(chat_id)
        engine.create_game(chat_id)

        assert engine.game_counter == 3

        assert len(engine.games) == 1
        assert engine.games[chat_id].game_number == 3

    def test_get_game_after_deletion(self, mock_bus):
        with patch('engine.core.EventDispatcher'):
            engine = GameEngine(mock_bus)

        chat_id = -100
        engine.create_game(chat_id)
        del engine.games[chat_id]

        assert engine.get_game(chat_id) is None
