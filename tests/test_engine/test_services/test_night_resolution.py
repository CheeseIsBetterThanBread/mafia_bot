import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import MockOperations

from engine.services.night_resolution import (
    generate_random_moves,
    resolve_night,
    EventBus,
    Game,
    NightAction,
)


class TestGenerateRandomMoves:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Дон"),
            (4, "Player 4", "Адвокат"),
            (5, "Player 5", "Ниндзя"),
            (6, "Player 6", "Вор"),
            (7, "Player 7", "Доктор"),
            (8, "Player 8", "Тула"),
            (9, "Player 9", "Маньяк без бинтов"),
            (10, "Player 10", "Маньяк с бинтами"),
            (11, "Player 11", "Двуликий"),
            (12, "Player 12", "Бессмертный"),
            (13, "Player 13", "Шериф"),
        ]

        for uid, name, role in players_data:
            game.add_player(uid, name)
            game.players[uid].role = role
            game.players[uid].is_alive = True

        return game

    @pytest.mark.asyncio
    async def test_ninja_random_move(self, mock_bus, game):
        ninja = game.players[5]

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            target = game.players[2]
            mock_choice.return_value = target

            await generate_random_moves(mock_bus, game)

            assert ninja.user_id in game.night_actions
            assert (
                game.night_actions[ninja.user_id][NightAction.SHURIKEN] == target.number
            )

            mock_bus.emit.assert_called()

            found_ninja = False
            for index in range(mock_bus.emit.call_count):
                response = mock_bus.emit.call_args_list[index].args[0]
                if response.chat_id == ninja.user_id:
                    found_ninja = True
                    assert f"сюрикен в Игрока №{target.number}" in response.text
                    break

            assert found_ninja

    @pytest.mark.asyncio
    async def test_tula_random_move_with_valid_targets(self, mock_bus, game):
        tula = game.players[8]
        tula.last_healed = None

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            target = game.players[3]
            mock_choice.return_value = target

            await generate_random_moves(mock_bus, game)

            assert tula.user_id in game.night_actions
            assert game.night_actions[tula.user_id][NightAction.TULA] == target.number

            mock_bus.emit.assert_called()

            found_tula = False
            for index in range(mock_bus.emit.call_count):
                response = mock_bus.emit.call_args_list[index].args[0]
                if response.chat_id == tula.user_id:
                    found_tula = True
                    assert f"отправил вас к Игроку №{target.number}" in response.text
                    break

            assert found_tula

    @pytest.mark.asyncio
    async def test_tula_with_only_last_healed_target(self, mock_bus, game):
        tula = game.players[8]
        tula.last_healed = 8
        for player in game.players.values():
            if player.number != 8:
                player.is_alive = False

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            await generate_random_moves(mock_bus, game)

            assert tula.last_healed is None
            mock_choice.assert_not_called()

    @pytest.mark.asyncio
    async def test_maniac_without_bandages_random_move(self, mock_bus, game):
        maniac = game.players[9]

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            target = game.players[4]
            mock_choice.return_value = target

            await generate_random_moves(mock_bus, game)

            assert maniac.user_id in game.night_actions
            assert (
                game.night_actions[maniac.user_id][NightAction.MANIAC_KILL]
                == target.number
            )

            mock_bus.emit.assert_called()

            found_maniac = False
            for index in range(mock_bus.emit.call_count):
                response = mock_bus.emit.call_args_list[index].args[0]
                if response.chat_id == maniac.user_id:
                    found_maniac = True
                    assert f"убивать Игрока №{target.number}" in response.text
                    break

            assert found_maniac

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_random_move(self, mock_bus, game):
        maniac = game.players[10]
        maniac.last_man_heal = True

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            target = game.players[5]
            mock_choice.return_value = target

            await generate_random_moves(mock_bus, game)

            assert maniac.user_id in game.night_actions
            assert (
                game.night_actions[maniac.user_id][NightAction.MANIAC_KILL]
                == target.number
            )
            assert maniac.last_man_heal is False

            mock_bus.emit.assert_called()

            found_maniac = False
            for index in range(mock_bus.emit.call_count):
                response = mock_bus.emit.call_args_list[index].args[0]
                if response.chat_id == maniac.user_id:
                    found_maniac = True
                    assert f"убивать Игрока №{target.number}" in response.text
                    break

            assert found_maniac

    @pytest.mark.asyncio
    async def test_two_face_with_found_mafia(self, mock_bus, game):
        two_face = game.players[11]
        two_face.found_mafia = True

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            target = game.players[6]
            mock_choice.return_value = target

            await generate_random_moves(mock_bus, game)

            assert two_face.user_id in game.night_actions
            assert (
                game.night_actions[two_face.user_id][NightAction.TWO_FACE_KILL]
                == target.number
            )

            mock_bus.emit.assert_called()

            found_two_face = False
            for index in range(mock_bus.emit.call_count):
                response = mock_bus.emit.call_args_list[index].args[0]
                if response.chat_id == two_face.user_id:
                    found_two_face = True
                    assert f"убивать Игрока №{target.number}" in response.text
                    break

            assert found_two_face

    @pytest.mark.asyncio
    async def test_two_face_without_found_mafia(self, mock_bus, game):
        two_face = game.players[11]
        two_face.found_mafia = False

        await generate_random_moves(mock_bus, game)

        assert two_face.user_id not in game.night_actions

    @pytest.mark.asyncio
    async def test_doctor_resets_last_healed(self, mock_bus, game):
        doctor = game.players[7]
        doctor.last_healed = 5

        await generate_random_moves(mock_bus, game)

        assert doctor.last_healed is None

    @pytest.mark.asyncio
    async def test_lawyer_resets_last_alibi(self, mock_bus, game):
        lawyer = game.players[4]
        lawyer.last_alibi = 3

        await generate_random_moves(mock_bus, game)

        assert lawyer.last_alibi is None

    @pytest.mark.asyncio
    async def test_skip_players_with_existing_actions(self, mock_bus, game):
        ninja = game.players[5]
        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: 2}

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            mock_choice.return_value = game.players[1]

            await generate_random_moves(mock_bus, game)

            assert game.night_actions[ninja.user_id] == {NightAction.SHURIKEN: 2}

    @pytest.mark.asyncio
    async def test_skip_glued_players(self, mock_bus, game):
        ninja = game.players[5]
        ninja.is_glued = True

        with patch("engine.services.night_resolution.random.choice") as mock_choice:
            mock_choice.return_value = game.players[1]
            await generate_random_moves(mock_bus, game)

            assert ninja.user_id not in game.night_actions


class TestResolveNight:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @staticmethod
    def create_game(players_data):
        game = Game(chat_id=-100123456789, game_counter=1)

        for uid, name, role in players_data:
            game.add_player(uid, name)
            game.players[uid].role = role
            game.players[uid].is_alive = True

        return game

    @staticmethod
    def patch_night():
        return MockOperations(
            "engine.services.night_resolution",
            generate_random_moves=AsyncMock(),
            start_day=AsyncMock(),
            check_victory=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_resolve_night_no_actions(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Дон"),
            (4, "Player 4", "Адвокат"),
            (5, "Player 5", "Ниндзя"),
            (6, "Player 6", "Вор"),
            (7, "Player 7", "Доктор"),
            (8, "Player 8", "Тула"),
            (9, "Player 9", "Маньяк без бинтов"),
            (10, "Player 10", "Маньяк с бинтами"),
            (11, "Player 11", "Двуликий"),
            (12, "Player 12", "Бессмертный"),
            (13, "Player 13", "Шериф"),
        ]
        game = self.create_game(players_data)

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            mocks.generate_random_moves.assert_called_once_with(mock_bus, game)
            mocks.check_victory.assert_called_once()
            mocks.start_day.assert_called_once()

    @pytest.mark.asyncio
    async def test_mafia_vote_no_choice(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Дон"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[2]
        don = game.players[3]
        target = game.players[1]

        game.night_actions[mafia.user_id] = {NightAction.VOTE: target.number}
        game.night_actions[don.user_id] = {NightAction.VOTE: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_mafia_vote_don_weight(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Дон"),
            (4, "Player 4", "Мирный житель"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[2]
        don = game.players[3]

        mafia_target = game.players[1]
        don_target = game.players[4]

        game.night_actions[mafia.user_id] = {NightAction.VOTE: mafia_target.number}
        game.night_actions[don.user_id] = {NightAction.VOTE: don_target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not don_target.is_alive
            assert mafia_target.is_alive

    @pytest.mark.asyncio
    async def test_mafia_vote_balance(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Мафия"),
            (4, "Player 4", "Мирный житель"),
        ]
        game = self.create_game(players_data)

        mafia_1 = game.players[2]
        mafia_2 = game.players[3]

        mafia_1_target = game.players[1]
        mafia_2_target = game.players[4]

        game.night_actions[mafia_1.user_id] = {NightAction.VOTE: mafia_1_target.number}
        game.night_actions[mafia_2.user_id] = {NightAction.VOTE: mafia_2_target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            response = mock_bus.emit.call_args[0][0]

            first_won = (
                (not mafia_1_target.is_alive)
                and f"{mafia_1_target.number}" in response.text
                and "убиты" in response.text
            )
            second_won = (
                (not mafia_2_target.is_alive)
                and f"{mafia_2_target.number}" in response.text
                and "убиты" in response.text
            )

            assert (first_won and mafia_2_target.is_alive) or (
                second_won and mafia_1_target.is_alive
            )

    @pytest.mark.asyncio
    async def test_doctor_heal(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Доктор"),
        ]
        game = self.create_game(players_data)

        doctor = game.players[3]
        mafia = game.players[2]
        target = game.players[1]

        game.night_actions[doctor.user_id] = {NightAction.HEAL: target.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive

            response = mock_bus.emit.call_args[0][0]
            assert "никто не умер" in response.text

    @pytest.mark.asyncio
    async def test_tula_heal(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        tula = game.players[3]
        mafia = game.players[2]
        target = game.players[1]

        game.night_actions[tula.user_id] = {NightAction.TULA: target.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive

            response = mock_bus.emit.call_args[0][0]
            assert "никто не умер" in response.text

    @pytest.mark.asyncio
    async def test_tula_double_kill(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        tula = game.players[3]
        mafia = game.players[2]
        target = game.players[1]

        game.night_actions[tula.user_id] = {NightAction.TULA: target.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not tula.is_alive
            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_tula_self_heal(self, mock_bus):
        players_data = [(2, "Player 2", "Мафия"), (3, "Player 3", "Тула")]
        game = self.create_game(players_data)

        tula = game.players[3]
        mafia = game.players[2]

        game.night_actions[tula.user_id] = {NightAction.TULA: tula.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert tula.is_alive

            response = mock_bus.emit.call_args[0][0]
            assert "никто не умер" in response.text

    @pytest.mark.asyncio
    async def test_shuriken(self, mock_bus):
        players_data = [(1, "Player 1", "Мирный житель"), (2, "Player 2", "Ниндзя")]
        game = self.create_game(players_data)

        ninja = game.players[2]
        target = game.players[1]

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.shurikens == 1

    @pytest.mark.asyncio
    async def test_double_shuriken_kill(self, mock_bus):
        players_data = [(1, "Player 1", "Мирный житель"), (2, "Player 2", "Ниндзя")]
        game = self.create_game(players_data)

        ninja = game.players[2]
        target = game.players[1]

        target.shurikens = 1
        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_shuriken_with_doctor(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Ниндзя"),
            (3, "Player 3", "Доктор"),
        ]
        game = self.create_game(players_data)

        doctor = game.players[3]
        ninja = game.players[2]
        target = game.players[1]

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: target.number}
        game.night_actions[doctor.user_id] = {NightAction.HEAL: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.shurikens == 0

    @pytest.mark.asyncio
    async def test_shuriken_with_tula(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Ниндзя"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        tula = game.players[3]
        ninja = game.players[2]
        target = game.players[1]

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: target.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.shurikens == 0

    @pytest.mark.asyncio
    async def test_shuriken_with_tula_double_kill(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Ниндзя"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        tula = game.players[3]
        ninja = game.players[2]
        target = game.players[1]

        tula.shurikens = 1

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: tula.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not tula.is_alive
            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_shuriken_with_tula_self_heal(self, mock_bus):
        players_data = [(1, "Player 1", "Ниндзя"), (2, "Player 2", "Тула")]
        game = self.create_game(players_data)

        tula = game.players[2]
        ninja = game.players[1]

        tula.shurikens = 1

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: tula.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: tula.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert tula.shurikens == 0

    @pytest.mark.asyncio
    async def test_two_face_kill(self, mock_bus):
        players_data = [(1, "Player 1", "Мирный житель"), (2, "Player 2", "Двуликий")]
        game = self.create_game(players_data)

        two_face = game.players[2]
        target = game.players[1]

        two_face.found_mafia = True

        game.night_actions[two_face.user_id] = {
            NightAction.TWO_FACE_KILL: target.number
        }

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_without_bandages_kill(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Маньяк без бинтов"),
        ]
        game = self.create_game(players_data)

        maniac = game.players[2]
        target = game.players[1]

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_KILL: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_kill(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Маньяк с бинтами"),
        ]
        game = self.create_game(players_data)

        maniac = game.players[2]
        target = game.players[1]

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_KILL: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_survives_shot(self, mock_bus):
        players_data = [(1, "Player 1", "Мафия"), (2, "Player 2", "Маньяк с бинтами")]
        game = self.create_game(players_data)

        maniac = game.players[2]
        mafia = game.players[1]

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_HEAL: maniac.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: maniac.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert maniac.is_alive

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_survives_shurikens(self, mock_bus):
        players_data = [(1, "Player 1", "Ниндзя"), (2, "Player 2", "Маньяк с бинтами")]
        game = self.create_game(players_data)

        maniac = game.players[2]
        ninja = game.players[1]

        maniac.shurikens = 1

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_HEAL: maniac.number}
        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: maniac.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert maniac.is_alive
            assert maniac.shurikens == 0

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_survives_tula(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мафия"),
            (2, "Player 2", "Маньяк с бинтами"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        maniac = game.players[2]
        mafia = game.players[1]
        tula = game.players[3]

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_HEAL: maniac.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: maniac.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert maniac.is_alive

    @pytest.mark.asyncio
    async def test_immortal_survives_shot(self, mock_bus):
        players_data = [(1, "Player 1", "Мафия"), (2, "Player 2", "Бессмертный")]
        game = self.create_game(players_data)

        immortal = game.players[2]
        mafia = game.players[1]

        immortal.is_glued = True

        game.night_actions[mafia.user_id] = {NightAction.VOTE: immortal.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert immortal.is_alive

    @pytest.mark.asyncio
    async def test_immortal_survives_shurikens(self, mock_bus):
        players_data = [(1, "Player 1", "Ниндзя"), (2, "Player 2", "Бессмертный")]
        game = self.create_game(players_data)

        immortal = game.players[2]
        ninja = game.players[1]

        immortal.shurikens = 1
        immortal.is_glued = True

        game.night_actions[ninja.user_id] = {NightAction.SHURIKEN: immortal.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert immortal.is_alive
            assert immortal.shurikens == 0

    @pytest.mark.asyncio
    async def test_immortal_survives_tula(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мафия"),
            (2, "Player 2", "Бессмертный"),
            (3, "Player 3", "Тула"),
        ]
        game = self.create_game(players_data)

        immortal = game.players[2]
        mafia = game.players[1]
        tula = game.players[3]

        immortal.is_glued = True

        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: immortal.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert immortal.is_alive

    @pytest.mark.asyncio
    async def test_healed_survives_tula(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мафия"),
            (2, "Player 2", "Доктор"),
            (3, "Player 3", "Тула"),
            (4, "Player 4", "Мирный житель"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[1]
        doctor = game.players[2]
        tula = game.players[3]
        healed = game.players[4]

        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}
        game.night_actions[doctor.user_id] = {NightAction.HEAL: healed.number}
        game.night_actions[tula.user_id] = {NightAction.TULA: healed.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert healed.is_alive

    @pytest.mark.asyncio
    async def test_victory_ends_night(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Дон"),
            (4, "Player 4", "Адвокат"),
            (5, "Player 5", "Ниндзя"),
            (6, "Player 6", "Вор"),
            (7, "Player 7", "Доктор"),
            (8, "Player 8", "Тула"),
            (9, "Player 9", "Маньяк без бинтов"),
            (10, "Player 10", "Маньяк с бинтами"),
            (11, "Player 11", "Двуликий"),
            (12, "Player 12", "Бессмертный"),
            (13, "Player 13", "Шериф"),
        ]
        game = self.create_game(players_data)

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = True

            await resolve_night(mock_bus, game)

            mocks.start_day.assert_not_called()

    @pytest.mark.asyncio
    async def test_tula_gives_alibi(self, mock_bus):
        players_data = [(1, "Player 1", "Тула"), (2, "Player 2", "Мирный житель")]
        game = self.create_game(players_data)

        tula = game.players[1]
        target = game.players[2]

        game.night_actions[tula.user_id] = {NightAction.TULA: target.user_id}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.has_alibi

    @pytest.mark.asyncio
    async def test_tula_self_alibi(self, mock_bus):
        players_data = [
            (1, "Player 1", "Тула"),
        ]
        game = self.create_game(players_data)

        tula = game.players[1]

        game.night_actions[tula.user_id] = {NightAction.TULA: tula.user_id}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert tula.has_alibi

    @pytest.mark.asyncio
    async def test_lawyer_gives_alibi(self, mock_bus):
        players_data = [(1, "Player 1", "Адвокат"), (2, "Player 2", "Мирный житель")]
        game = self.create_game(players_data)

        lawyer = game.players[1]
        target = game.players[2]

        game.night_actions[lawyer.user_id] = {NightAction.ALIBI: target.user_id}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.has_alibi

    @pytest.mark.asyncio
    async def test_mafia_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Мафия"),
        ]
        game = self.create_game(players_data)

        mafia_1 = game.players[2]
        mafia_2 = game.players[3]
        target = game.players[1]

        mafia_1.is_glued = True

        game.night_actions[mafia_1.user_id] = {NightAction.VOTE: target.number}
        game.night_actions[mafia_2.user_id] = {NightAction.VOTE: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive

    @pytest.mark.asyncio
    async def test_two_face_not_blocked_by_mafia_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Двуликий"),
            (4, "Player 4", "Мирный житель"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[2]
        two_face = game.players[3]
        mafia_target = game.players[1]
        two_face_target = game.players[4]

        mafia.is_glued = True

        game.night_actions[mafia.user_id] = {NightAction.VOTE: mafia_target.number}
        game.night_actions[two_face.user_id] = {
            NightAction.TWO_FACE_KILL: two_face_target.number
        }

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert mafia_target.is_alive
            assert not two_face_target.is_alive

    @pytest.mark.asyncio
    async def test_ninja_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Ниндзя"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[2]
        ninja = game.players[3]
        target = game.players[1]

        ninja.is_glued = True

        game.night_actions[mafia.user_id] = {NightAction.VOTE: target.number}
        game.night_actions[ninja.user_id] = {
            NightAction.VOTE: target.number,
            NightAction.SHURIKEN: target.number,
        }

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive
            assert target.shurikens == 0

    @pytest.mark.asyncio
    async def test_lawyer_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Мафия"),
            (3, "Player 3", "Адвокат"),
        ]
        game = self.create_game(players_data)

        mafia = game.players[2]
        lawyer = game.players[3]
        target = game.players[1]

        lawyer.is_glued = True

        game.night_actions[mafia.user_id] = {NightAction.VOTE: target.number}
        game.night_actions[lawyer.user_id] = {
            NightAction.VOTE: target.number,
            NightAction.ALIBI: mafia.number,
        }

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive
            assert not mafia.has_alibi

    @pytest.mark.asyncio
    async def test_two_face_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Двуликий"),
            (3, "Player 3", "Мафия"),
            (4, "Player 4", "Мирный житель"),
        ]
        game = self.create_game(players_data)

        two_face = game.players[2]
        two_face_target = game.players[1]
        mafia = game.players[3]
        mafia_target = game.players[4]

        two_face.is_glued = True

        game.night_actions[two_face.user_id] = {
            NightAction.TWO_FACE_KILL: two_face_target.number
        }
        game.night_actions[mafia.user_id] = {NightAction.VOTE: mafia_target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert two_face_target.is_alive
            assert not mafia_target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_without_bandages_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Маньяк без бинтов"),
        ]
        game = self.create_game(players_data)

        maniac = game.players[2]
        target = game.players[1]

        maniac.is_glued = True

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_KILL: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_kill_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Мирный житель"),
            (2, "Player 2", "Маньяк с бинтами"),
        ]
        game = self.create_game(players_data)

        maniac = game.players[2]
        target = game.players[1]

        maniac.is_glued = True

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_KILL: target.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert target.is_alive

    @pytest.mark.asyncio
    async def test_maniac_with_bandages_heal_blocked_by_glue(self, mock_bus):
        players_data = [(1, "Player 1", "Маньяк без бинтов"), (2, "Plater 2", "Мафия")]
        game = self.create_game(players_data)

        maniac = game.players[1]
        mafia = game.players[2]

        maniac.is_glued = True

        game.night_actions[maniac.user_id] = {NightAction.MANIAC_HEAL: maniac.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: maniac.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not maniac.is_alive

    @pytest.mark.asyncio
    async def test_doctor_blocked_by_glue(self, mock_bus):
        players_data = [(1, "Player 1", "Доктор"), (2, "Plater 2", "Мафия")]
        game = self.create_game(players_data)

        doctor = game.players[1]
        mafia = game.players[2]

        doctor.is_glued = True

        game.night_actions[doctor.user_id] = {NightAction.HEAL: doctor.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: doctor.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not doctor.is_alive

    @pytest.mark.asyncio
    async def test_tula_heal_blocked_by_glue(self, mock_bus):
        players_data = [(1, "Player 1", "Тула"), (2, "Plater 2", "Мафия")]
        game = self.create_game(players_data)

        tula = game.players[1]
        mafia = game.players[2]

        tula.is_glued = True

        game.night_actions[tula.user_id] = {NightAction.TULA: tula.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert not tula.is_alive

    @pytest.mark.asyncio
    async def test_tula_alibi_blocked_by_glue(self, mock_bus):
        players_data = [
            (1, "Player 1", "Тула"),
            (2, "Plater 2", "Мафия"),
            (3, "Player 3", "Доктор"),
        ]
        game = self.create_game(players_data)

        tula = game.players[1]
        mafia = game.players[2]
        doctor = game.players[3]

        tula.is_glued = True

        game.night_actions[tula.user_id] = {NightAction.TULA: tula.number}
        game.night_actions[mafia.user_id] = {NightAction.VOTE: tula.number}
        game.night_actions[doctor.user_id] = {NightAction.HEAL: tula.number}

        with self.patch_night() as mocks:
            mocks.check_victory.return_value = False

            await resolve_night(mock_bus, game)

            assert tula.is_alive
            assert not tula.has_alibi
