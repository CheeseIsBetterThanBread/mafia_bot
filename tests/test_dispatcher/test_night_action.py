import pytest
from unittest.mock import AsyncMock, Mock, patch

from engine.dispatcher import *


class TestNightActionHandlers:
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
        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
        game.day_count = 2
        game.state = GameState.NIGHT
        game.night_actions = {}
        for i in range(1, 6):
            game.night_actions.setdefault(i, {})

        game.expected_night_actors = {
            1: ["vote", "heal"],
            2: ["check_d"],
            3: ["check_s"],
            4: ["dvul_j"],
            5: ["man_k", "man_h"]
        }
        return game

    @pytest.mark.asyncio
    async def test_night_action_success(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "vote", 2
        )
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.resolve_night', new_callable=AsyncMock):
            await dispatcher._handle_night_action(query)

            assert game.night_actions[1]["vote"] == 2
            assert "vote" not in game.expected_night_actors[1]

            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert isinstance(response, ResponseWithAlert)
            assert response.is_valid is True

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
    async def test_night_action_wrong_state(self, dispatcher, mock_engine, game, state):
        game.state = state

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "vote", 2
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Ночь уже прошла" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_night_action_invalid_action(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "invalid_action", 2
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Это действие вам сейчас недоступно" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_night_action_no_game(self, dispatcher, mock_engine):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "vote", 2
        )
        mock_engine.get_game.return_value = None

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Ночь уже прошла" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_thief_action_success(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT_THIEF
        game.expected_night_actors = {1: ["rek"]}
        game.players[1].last_rek = None

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "rek", 2
        )
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.start_night_others', new_callable=AsyncMock) as mock_others:
            await dispatcher._handle_night_action(query)

            assert game.players[2].is_glued is True
            assert game.players[1].last_rek == 2

            assert "Вы заклеили Игрока №2" in dispatcher.bus.emit.call_args_list[0][0][0].text

            mock_others.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_thief_action_no_target(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT_THIEF
        game.expected_night_actors = {1: ["rek"]}
        game.players[1].last_rek = None

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "rek", NULL_OPTION
        )
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.start_night_others', new_callable=AsyncMock) as mock_others:
            await dispatcher._handle_night_action(query)

            assert game.players[1].last_rek == NULL_OPTION

            response = dispatcher.bus.emit.call_args_list[0][0][0]
            assert "Вы решили никого не клеить" in response.text
            assert response.chat_id == 1
            mock_others.assert_called_once()

    @pytest.mark.asyncio
    async def test_thief_action_same_target_two_nights(self, dispatcher, mock_engine, game):
        game.state = GameState.NIGHT_THIEF
        game.expected_night_actors = {1: ["rek"]}
        game.players[1].last_rek = 2

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "rek", 2
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нельзя клеить одного и того же игрока" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_heal_action_success(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "heal", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.night_actions[1]["heal"] == 3
        assert "heal" not in game.expected_night_actors[1]

    @pytest.mark.asyncio
    async def test_heal_action_same_target_two_nights(self, dispatcher, mock_engine, game):
        game.players[1].last_healed = 3

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "heal", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нельзя лечить этого игрока две ночи подряд" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_tula_action_success(self, dispatcher, mock_engine, game):
        game.expected_night_actors[1] = ["tula"]
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "tula", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.night_actions[1]["tula"] == 3
        assert "tula" not in game.expected_night_actors[1]

    @pytest.mark.asyncio
    async def test_tula_action_same_target_two_nights(self, dispatcher, mock_engine, game):
        game.expected_night_actors[1] = ["tula"]
        game.players[1].last_healed = 3

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "tula", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нельзя лечить этого игрока две ночи подряд" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    async def test_maniac_kill_action(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [5], -100, 5, Mock(),
            "man_k", 2
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.night_actions[5]["man_k"] == 2
        assert "man_k" not in game.expected_night_actors[5]
        assert "man_h" not in game.expected_night_actors[5]

    @pytest.mark.asyncio
    async def test_maniac_heal_action(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [5], -100, 5, Mock(),
            "man_h", 5
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert "man_h" not in game.expected_night_actors[5]
        assert "man_k" not in game.expected_night_actors[5]
        assert game.players[5].last_man_heal is True

    @pytest.mark.asyncio
    async def test_maniac_heal_two_days_in_row(self, dispatcher, mock_engine, game):
        game.players[5].last_man_heal = True

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [5], -100, 5, Mock(),
            "man_h", 5
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нельзя лечить себя 2 дня подряд" in response.text
        assert response.chat_id == 5

    @pytest.mark.asyncio
    async def test_alibi_action_success(self, dispatcher, mock_engine, game):
        game.expected_night_actors[1].append("alibi")

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "alibi", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.night_actions[1]["alibi"] == 3

    @pytest.mark.asyncio
    async def test_alibi_same_target_two_nights(self, dispatcher, mock_engine, game):
        game.players[1].last_alibi = 3
        game.expected_night_actors[1].append("alibi")

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "alibi", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args[0][0]
        assert "Нельзя давать алиби этому игроку две ночи подряд" in response.text
        assert response.chat_id == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", ["Мафия", "Дон", "Ниндзя", "Адвокат"])
    async def test_two_face_finds_mafia(self, dispatcher, mock_engine, game, role):
        game.players[1].role = role
        game.players[2].role = "Мафия"

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [4], -100, 4, Mock(),
            "dvul_j", 1
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.players[4].found_mafia is True
        assert game.players[4].found_mafia_day == game.day_count

        for call in dispatcher.bus.emit.call_args_list:
            response = call[0][0]
            if type(response) is not ResponseBase:
                continue
            if response.chat_id == 4:
                assert "Вы нашли Мафию" in response.text
            elif response.chat_id in [1, 2]:
                assert "Двуликий нашел нас" in response.text
            else:
                assert "Вы нашли Мафию" not in response.text and "Двуликий нашел нас" not in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [
        "Мирный житель",
        "Бессмертный",
        "Доктор",
        "Тула",
        "Шериф",
        "Маньяк с бинтами",
        "Маньяк без бинтов",
        "Вор"
    ])
    async def test_two_face_not_finds_mafia(self, dispatcher, mock_engine, game, role):
        game.players[5].role = role

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [4], -100, 4, Mock(),
            "dvul_j", 5
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        assert game.players[4].found_mafia is False

        response = dispatcher.bus.emit.call_args_list[0][0][0]

        assert isinstance(response, ResponseBase)
        assert response.chat_id == 4
        assert "не состоит в Мафии" in response.text

    @pytest.mark.asyncio
    async def test_check_don_sheriff_found(self, dispatcher, mock_engine, game):
        game.players[3].role = "Шериф"

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [2], -100, 2, Mock(),
            "check_d", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args_list[0][0][0]
        assert isinstance(response, ResponseBase)
        assert response.chat_id == 2
        assert "✅" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [
        "Мирный житель",
        "Бессмертный",
        "Доктор",
        "Тула",
        "Маньяк с бинтами",
        "Маньяк без бинтов",
        "Вор",
        "Мафия",
        "Ниндзя",
        "Адвокат"
    ])
    async def test_check_don_sheriff_not_found(self, dispatcher, mock_engine, game, role):
        game.players[3].role = role

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [2], -100, 2, Mock(),
            "check_d", 3
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args_list[0][0][0]
        assert isinstance(response, ResponseBase)
        assert response.chat_id == 2
        assert "НЕ ШЕРИФ" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [
        "Дон",
        "Мафия",
        "Ниндзя",
        "Адвокат"
    ])
    async def test_check_sheriff_mafia_found(self, dispatcher, mock_engine, game, role):
        game.players[4].role = role

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [3], -100, 3, Mock(),
            "check_s", 4
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args_list[0][0][0]

        assert isinstance(response, ResponseBase)
        assert response.chat_id == 3
        assert "МАФИЯ" in response.text and "✅" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [
        "Мирный житель",
        "Бессмертный",
        "Доктор",
        "Тула",
        "Маньяк с бинтами",
        "Маньяк без бинтов",
        "Вор",
        "Шериф"
    ])
    async def test_check_sheriff_not_mafia(self, dispatcher, mock_engine, game, role):
        game.players[4].role = role

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [3], -100, 3, Mock(),
            "check_s", 4
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args_list[0][0][0]

        assert isinstance(response, ResponseBase)
        assert response.chat_id == 3
        assert "НЕ МАФИЯ" in response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("found,day_offset,expected", [
        (False, -1, False),
        (True, 0, False),
        (True, -1, True)
    ])
    async def test_check_sheriff_and_two_face(self, dispatcher, mock_engine, game, found, day_offset, expected):
        two_face = game.players[4]
        two_face.role = "Двуликий"
        two_face.found_mafia = found
        two_face.found_mafia_day = game.day_count + day_offset

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [3], -100, 3, Mock(),
            "check_s", 4
        )
        mock_engine.get_game.return_value = game

        await dispatcher._handle_night_action(query)

        response = dispatcher.bus.emit.call_args_list[0][0][0]

        assert isinstance(response, ResponseBase)
        assert response.chat_id == 3
        found_two_face = "НЕ МАФИЯ" not in response.text
        assert found_two_face == expected

    @pytest.mark.asyncio
    async def test_all_actions_done_calls_resolve(self, dispatcher, mock_engine, game):
        game.expected_night_actors = {1: ['vote']}

        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "vote", 2
        )
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.resolve_night', new_callable=AsyncMock) as mock_resolve:
            await dispatcher._handle_night_action(query)

            mock_resolve.assert_called_once_with(dispatcher.bus, game)

    @pytest.mark.asyncio
    async def test_not_all_actions_done(self, dispatcher, mock_engine, game):
        query = NightActionQuery(
            QueryType.NIGHT_ACTION, [1], -100, 1, Mock(),
            "vote", 2
        )
        mock_engine.get_game.return_value = game

        with patch('engine.dispatcher.resolve_night', new_callable=AsyncMock) as mock_resolve:
            await dispatcher._handle_night_action(query)

            mock_resolve.assert_not_called()
