import pytest
from unittest.mock import AsyncMock

from tests.conftest import MockOperations, capture_logger_output

from engine.models import Player
from engine.phases.night import (
    start_night,
    start_night_others,
    thief_timeout_logic,
    night_timeout_logic,
    EventBus,
    Game,
    GameState,
    ResponseBase,
    ResponseWithOptions,
    THIEF_TIME,
    NIGHT_TIME,
    REMINDER_OFFSET
)


class TestStartNight:
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
            game.players[i].has_alibi = True

        game.current_preset = ["Вор", "Мафия", "Доктор"]
        game.day_count = 2

        return game

    @pytest.fixture
    def patch_dependencies(self):
        return MockOperations(
            'engine.phases.night',
            thief_timeout_logic=AsyncMock(),
            start_night_others=AsyncMock(),
            sleep=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_reset_state(self, mock_bus, game, patch_dependencies):
        with patch_dependencies:
            await start_night(mock_bus, game)

            assert game.state == GameState.NIGHT_THIEF
            assert game.night_actions == {}
            assert game.expected_night_actors == {}

            for player in game.players.values():
                assert not player.is_glued
                assert not player.has_alibi

    @pytest.mark.asyncio
    async def test_without_thief_in_preset(self, mock_bus, game, patch_dependencies):
        game.current_preset = ["Мафия", "Доктор"]

        with patch_dependencies as mocks:
            await start_night(mock_bus, game)

            mocks.thief_timeout_logic.assert_not_called()
            mocks.start_night_others.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_with_thief_alive(self, mock_bus, game, patch_dependencies):
        thief = game.players[1]
        thief.role = "Вор"

        with patch_dependencies as mocks:
            await start_night(mock_bus, game)

            mocks.thief_timeout_logic.assert_called_once_with(mock_bus, game, game.day_count)

            assert game.expected_night_actors[thief.user_id] == ["rek"]

            assert mock_bus.emit.call_count >= 2
            last_call = mock_bus.emit.call_args_list[-1][0][0]
            assert isinstance(last_call, ResponseWithOptions)

    @pytest.mark.asyncio
    async def test_with_thief_dead(self, mock_bus, game, patch_dependencies):
        game.players[1].role = "Вор"
        game.players[1].is_alive = False

        with patch_dependencies as mocks:
            await start_night(mock_bus, game)

            mocks.thief_timeout_logic.assert_called_once_with(mock_bus, game, game.day_count)
            mocks.sleep.assert_called_once()
            assert mock_bus.emit.call_count >= 2

            mocks.start_night_others.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_thief_options_generation(self, mock_bus, game, patch_dependencies):
        thief = game.players[1]
        thief.role = "Вор"

        with patch_dependencies:
            await start_night(mock_bus, game)

            response = None
            for call_args in mock_bus.emit.call_args_list:
                if isinstance(call_args[0][0], ResponseWithOptions):
                    response = call_args[0][0]
                    break

            assert response is not None
            assert len(response.candidates) == len(game.get_alive_players()) + 1
            assert "Никого не клеить" in [c[0] for c in response.candidates]

    @pytest.mark.asyncio
    async def test_emit_error_handling(self, mock_bus, game, patch_dependencies):
        thief = game.players[1]
        thief.role = "Вор"

        mock_bus.emit.side_effect = [None, Exception("Test error"), None]

        with capture_logger_output() as log_content:
            with patch_dependencies as mocks:
                await start_night(mock_bus, game)

                assert "Test error" in log_content.getvalue()

                mocks.start_night_others.assert_called_once_with(mock_bus, game)
                assert game.expected_night_actors == {}
                assert thief.last_rek is None


class TestStartNightOthers:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        roles = {
            1: "Мафия",
            2: "Доктор",
            3: "Шериф",
            4: "Дон",
            5: "Ниндзя",
            6: "Маньяк без бинтов",
            7: "Маньяк с бинтами",
            8: "Двуликий",
            9: "Адвокат",
            10: "Тула"
        }

        for uid, role in roles.items():
            game.add_player(uid, f"Player {uid}")
            game.players[uid].role = role
            game.players[uid].is_alive = True

        game.day_count = 2

        return game

    @pytest.fixture
    def patch_dependencies(self):
        return MockOperations(
            'engine.phases.night',
            night_timeout_logic=AsyncMock(),
            resolve_night=AsyncMock(),
            sleep=AsyncMock()
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("two_face_action,found_mafia", [
        ('dvul_j', False),
        ('dvul_k', True)
    ])
    async def test_set_state(self, mock_bus, game, patch_dependencies, two_face_action, found_mafia):
        game.players[8].found_mafia = found_mafia
        expected_night_actors = {
            1: ['vote'],
            2: ['heal'],
            3: ['check_s'],
            4: ['vote', 'check_d'],
            5: ['vote', 'sur'],
            6: ['man_k'],
            7: ['man_k', 'man_h'],
            8: [two_face_action],
            9: ['vote', 'alibi'],
            10: ['tula']
        }

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            assert game.state == GameState.NIGHT
            assert game.expected_night_actors == expected_night_actors

    @pytest.mark.asyncio
    async def test_create_timeout(self, mock_bus, game, patch_dependencies):
        with patch_dependencies as mocks:
            await start_night_others(mock_bus, game)

            mocks.night_timeout_logic.assert_called_once_with(mock_bus, game, game.day_count)

    @pytest.mark.asyncio
    async def test_mafia_actions(self, mock_bus, game, patch_dependencies):
        mafia = game.players[1]
        ninja = game.players[5]
        lawyer = game.players[9]
        don = game.players[4]

        mafia_team_ids = [mafia.user_id, ninja.user_id, lawyer.user_id, don.user_id]
        mafia_actions = 4 + 1 + 1 + 1

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            mafia_calls = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id in mafia_team_ids:
                    mafia_calls.append(response)

            assert len(mafia_calls) == mafia_actions

    @pytest.mark.asyncio
    async def test_doctor_action(self, mock_bus, game, patch_dependencies):
        doctor = game.players[2]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            doctor_response = None
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == doctor.user_id:
                    doctor_response = response
                    break

            assert doctor_response is not None
            assert "лечить" in doctor_response.text

    @pytest.mark.asyncio
    async def test_tula_action(self, mock_bus, game, patch_dependencies):
        tula = game.players[10]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            tula_response = None
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == tula.user_id:
                    tula_response = response
                    break

            assert tula_response is not None
            assert "хил + алиби" in tula_response.text

    @pytest.mark.asyncio
    async def test_sheriff_action(self, mock_bus, game, patch_dependencies):
        sheriff = game.players[3]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            sheriff_response = None
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == sheriff.user_id:
                    sheriff_response = response
                    break

            assert sheriff_response is not None
            assert "проверим на мафию" in sheriff_response.text

    @pytest.mark.asyncio
    async def test_don_check_action(self, mock_bus, game, patch_dependencies):
        don = game.players[4]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            don_responses = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == don.user_id:
                    don_responses.append(response)

            assert len(don_responses) == 2
            assert "проверим на Шерифа" in don_responses[0].text or "проверим на Шерифа" in don_responses[1].text

    @pytest.mark.asyncio
    async def test_ninja_shuriken_action(self, mock_bus, game, patch_dependencies):
        ninja = game.players[5]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            ninja_responses = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == ninja.user_id:
                    ninja_responses.append(response)

            assert len(ninja_responses) == 2
            assert "кидаем сюрикен" in ninja_responses[0].text or "кидаем сюрикен" in ninja_responses[1].text

    @pytest.mark.asyncio
    async def test_lawyer_alibi_action(self, mock_bus, game, patch_dependencies):
        lawyer = game.players[9]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            lawyer_responses = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == lawyer.user_id:
                    lawyer_responses.append(response)

            assert len(lawyer_responses) == 2
            assert "даем алиби" in lawyer_responses[0].text or "даем алиби" in lawyer_responses[1].text

    @pytest.mark.asyncio
    async def test_maniac_without_bandages(self, mock_bus, game, patch_dependencies):
        maniac = game.players[6]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            maniac_responses = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == maniac.user_id:
                    maniac_responses.append(response)

            assert len(maniac_responses) == 1
            assert 'убиваем' in maniac_responses[0].text

    @pytest.mark.asyncio
    async def test_maniac_with_bandages(self, mock_bus, game, patch_dependencies):
        maniac = game.players[7]

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            maniac_responses = []
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == maniac.user_id:
                    maniac_responses.append(response)

            assert len(maniac_responses) == 2

    @pytest.mark.asyncio
    async def test_two_face_not_found(self, mock_bus, game, patch_dependencies):
        two_face = game.players[8]
        two_face.found_mafia = False

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            two_face_response = None
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == two_face.user_id:
                    two_face_response = response
                    break

            assert two_face_response is not None
            assert "Ищем мафию" in two_face_response.text

    @pytest.mark.asyncio
    async def test_two_face_found(self, mock_bus, game, patch_dependencies):
        two_face = game.players[8]
        two_face.found_mafia = True

        with patch_dependencies:
            await start_night_others(mock_bus, game)

            two_face_response = None
            for call_args in mock_bus.emit.call_args_list:
                response = call_args[0][0]
                if isinstance(response, ResponseWithOptions) and response.chat_id == two_face.user_id:
                    two_face_response = response
                    break

            assert two_face_response is not None
            assert "убиваем" in two_face_response.text

    @pytest.mark.asyncio
    async def test_no_actors(self, mock_bus, game, patch_dependencies):
        for player in game.players.values():
            if player.role not in ["Мирный житель", "Бессмертный"]:
                player.is_alive = False

        game.players[11] = Player(11, "Civilian", 11)
        game.players[11].role = "Мирный житель"
        game.players[11].is_alive = True

        with patch_dependencies as mocks:
            await start_night_others(mock_bus, game)

            mocks.resolve_night.assert_called_once_with(mock_bus, game)


class TestThiefTimeoutLogic:
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

        game.players[1].role = "Вор"
        game.day_count = 2
        game.state = GameState.NIGHT_THIEF

        return game

    @pytest.fixture
    def patch_dependencies(self):
        return MockOperations(
            "engine.phases.night",
            start_night_others=AsyncMock(),
            sleep=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_no_action(self, mock_bus, game, patch_dependencies):
        with patch_dependencies as mocks:
            await thief_timeout_logic(mock_bus, game, game.day_count)

            mocks.sleep.assert_called_once_with(THIEF_TIME)

            mock_bus.emit.assert_called_once()
            response = mock_bus.emit.call_args[0][0]
            assert "Вор никого не заклеил" in response.text

            assert game.expected_night_actors == {}

            mocks.start_night_others.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_wrong_day(self, mock_bus, game, patch_dependencies):
        game.day_count = 3

        with patch_dependencies as mocks:
            await thief_timeout_logic(mock_bus, game, 2)

            mocks.sleep.assert_called_once_with(THIEF_TIME)
            mock_bus.emit.assert_not_called()
            mocks.start_night_others.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_state(self, mock_bus, game, patch_dependencies):
        game.state = GameState.NIGHT

        with patch_dependencies as mocks:
            await thief_timeout_logic(mock_bus, game, game.day_count)

            mocks.sleep.assert_called_once_with(THIEF_TIME)
            mock_bus.emit.assert_not_called()
            mocks.start_night_others.assert_not_called()


class TestNightTimeoutLogic:
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

        game.expected_night_actors = {1: ["vote"], 2: ["heal"]}
        game.day_count = 2
        game.state = GameState.NIGHT

        return game

    @pytest.fixture
    def patch_dependencies(self):
        return MockOperations(
            "engine.phases.night",
            resolve_night=AsyncMock(),
            sleep=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_reminder_is_sent(self, mock_bus, game, patch_dependencies):
        with patch_dependencies as mocks:
            await night_timeout_logic(mock_bus, game, game.day_count)

            first_sleep_call_arg = mocks.sleep.call_args_list[0][0][0]
            second_sleep_call_arg = mocks.sleep.call_args_list[1][0][0]
            assert first_sleep_call_arg == NIGHT_TIME - REMINDER_OFFSET
            assert second_sleep_call_arg == REMINDER_OFFSET

            assert mock_bus.emit.call_count >= len(game.expected_night_actors)

            for uid in game.expected_night_actors:
                found = False
                for call_args in mock_bus.emit.call_args_list:
                    response = call_args[0][0]
                    if isinstance(response, ResponseBase) and response.chat_id == uid:
                        found = True
                        assert "Поторопитесь" in response.text
                assert found

    @pytest.mark.asyncio
    async def test_resolve_call(self, mock_bus, game, patch_dependencies):
        with patch_dependencies as mocks:
            await night_timeout_logic(mock_bus, game, game.day_count)

            first_sleep_call_arg = mocks.sleep.call_args_list[0][0][0]
            second_sleep_call_arg = mocks.sleep.call_args_list[1][0][0]
            assert first_sleep_call_arg == NIGHT_TIME - REMINDER_OFFSET
            assert second_sleep_call_arg == REMINDER_OFFSET

            mocks.resolve_night.assert_called_once_with(mock_bus, game)
            assert game.expected_night_actors == {}

    @pytest.mark.asyncio
    async def test_wrong_day(self, mock_bus, game, patch_dependencies):
        game.day_count = 3

        with patch_dependencies as mocks:
            await night_timeout_logic(mock_bus, game, 2)

            mocks.sleep.assert_called_once_with(NIGHT_TIME - REMINDER_OFFSET)
            mock_bus.emit.assert_not_called()
            mocks.resolve_night.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_state(self, mock_bus, game, patch_dependencies):
        game.state = GameState.DAY

        with patch_dependencies as mocks:
            await night_timeout_logic(mock_bus, game, game.day_count)

            mocks.sleep.assert_called_once_with(NIGHT_TIME - REMINDER_OFFSET)
            mock_bus.emit.assert_not_called()
            mocks.resolve_night.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_actors(self, mock_bus, game, patch_dependencies):
        game.expected_night_actors = {}

        with patch_dependencies as mocks:
            await night_timeout_logic(mock_bus, game, game.day_count)

            first_sleep_call_arg = mocks.sleep.call_args_list[0][0][0]
            second_sleep_call_arg = mocks.sleep.call_args_list[1][0][0]
            assert first_sleep_call_arg == NIGHT_TIME - REMINDER_OFFSET
            assert second_sleep_call_arg == REMINDER_OFFSET

            mock_bus.emit.assert_called_once()
            mocks.resolve_night.assert_called_once_with(mock_bus, game)


class TestIntegrationNightPhases:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        game.add_player(1, "Thief")
        game.add_player(2, "Mafia")
        game.add_player(3, "Doctor")

        game.players[1].role = "Вор"
        game.players[2].role = "Мафия"
        game.players[3].role = "Доктор"

        for player in game.players.values():
            player.is_alive = True

        game.current_preset = ["Вор", "Мафия", "Доктор"]
        game.day_count = 2

        return game

    @pytest.fixture
    def patch_dependencies(self):
        return MockOperations(
            "engine.phases.night",
            thief_timeout_logic=AsyncMock(),
            night_timeout_logic=AsyncMock(),
            resolve_night=AsyncMock(),
            sleep=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_full_night_cycle_with_thief(self, mock_bus, game, patch_dependencies):
        with patch_dependencies:
            await start_night(mock_bus, game)

            assert game.state == GameState.NIGHT_THIEF

            await start_night_others(mock_bus, game)

            assert game.state == GameState.NIGHT
            assert len(game.expected_night_actors) >= 2
            assert len(mock_bus.emit.call_args_list) >= 2

    @pytest.mark.asyncio
    async def test_night_cycle_without_thief(self, mock_bus, game, patch_dependencies):
        game.current_preset = ["Мафия", "Доктор"]

        with patch_dependencies:
            await start_night(mock_bus, game)

            assert game.state == GameState.NIGHT
