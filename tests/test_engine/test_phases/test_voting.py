from collections import deque

import pytest
from unittest.mock import AsyncMock, patch

from engine.phases.voting import (
    eliminate,
    start_voting,
    finish_voting,
    start_balance,
    resolve_balance,
    EventBus,
    Game,
    GameState,
)


class TestEliminate:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 4):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
            game.players[i].has_alibi = False

        return game

    @pytest.mark.asyncio
    async def test_without_alibi(self, mock_bus, game):
        killed_number = 2

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await eliminate(mock_bus, game, killed_number)

                dead = game.players_by_number[killed_number]
                assert not dead.is_alive

                assert mock_bus.emit.call_count >= 2
                first_call = mock_bus.emit.call_args_list[0][0][0]
                assert f"💀 Игрок №{killed_number} покидает стол!" in first_call.text

                last_call = mock_bus.emit.call_args_list[-1][0][0]
                assert "Город засыпает..." in last_call.text

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_with_alibi(self, mock_bus, game):
        killed_number = 2
        game.players_by_number[killed_number].has_alibi = True

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await eliminate(mock_bus, game, killed_number)

                assert game.players[killed_number].is_alive is True

                first_call = mock_bus.emit.call_args_list[0][0][0]
                assert (
                    f"🛡 Игрок №{killed_number} должен был покинуть стол"
                    in first_call.text
                )
                assert "АЛИБИ" in first_call.text

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_triggers_victory(self, mock_bus, game):
        killed_number = 2

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = True

                await eliminate(mock_bus, game, killed_number)

                mock_night.assert_not_called()
                mock_victory.assert_called_once_with(mock_bus, game)


class TestStartVoting:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        return game

    @pytest.mark.asyncio
    async def test_multiple_nominated(self, mock_bus, game):
        game.nominated = [2, 3, 5]

        await start_voting(mock_bus, game)

        assert game.state == GameState.VOTING
        assert game.current_votes == {2: 0, 3: 0, 5: 0}
        assert game.vote_history == {}
        assert len(game.voting_queue) > 0

        response = mock_bus.emit.call_args[0][0]
        assert "Начинаем голосование!" in response.text
        assert "Выставлены: [2, 3, 5]" in response.text
        assert f"Первым голосует Игрок №{game.voting_queue[0].number}" in response.text

    @pytest.mark.asyncio
    async def test_single_nominated_autokick(self, mock_bus, game):
        game.nominated = [3]

        with patch(
            "engine.phases.voting.eliminate", new_callable=AsyncMock
        ) as mock_eliminate:
            await start_voting(mock_bus, game)

            response = mock_bus.emit.call_args[0][0]
            assert "АВТОКИК" in response.text

            mock_eliminate.assert_called_once_with(mock_bus, game, 3)

    @pytest.mark.asyncio
    async def test_initialize_vote_tracking(self, mock_bus, game):
        game.nominated = [1, 4]

        await start_voting(mock_bus, game)

        assert isinstance(game.current_votes, dict)
        assert all(v == 0 for v in game.current_votes.values())
        assert isinstance(game.vote_history, dict)
        assert isinstance(game.voting_queue, deque)


class TestFinishVoting:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        game.nominated = [2, 3, 4]

        return game

    @pytest.mark.asyncio
    async def test_clear_winner(self, mock_bus, game):
        game.current_votes = {2: 5, 3: 2, 4: 1}
        game.revote_count = 0

        with patch(
            "engine.phases.voting.eliminate", new_callable=AsyncMock
        ) as mock_eliminate:
            await finish_voting(mock_bus, game)

            mock_eliminate.assert_called_once_with(mock_bus, game, 2)

    @pytest.mark.asyncio
    async def test_tie_first_revote(self, mock_bus, game):
        game.current_votes = {2: 3, 3: 3, 4: 2}
        game.revote_count = 0

        with patch(
            "engine.phases.voting.start_balance", new_callable=AsyncMock
        ) as mock_balance:
            await finish_voting(mock_bus, game)

            mock_balance.assert_called_once_with(mock_bus, game, [2, 3])

    @pytest.mark.asyncio
    async def test_tie_second_revote(self, mock_bus, game):
        game.current_votes = {2: 3, 3: 3, 4: 2}
        game.revote_count = 1

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            await finish_voting(mock_bus, game)

            response = mock_bus.emit.call_args[0][0]
            assert "Автоматическое оправдание" in response.text

            mock_night.assert_called_once_with(mock_bus, game)


class TestStartBalance:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        return game

    @pytest.mark.asyncio
    async def test_start_balance(self, mock_bus, game):
        players = [2, 3, 5]

        await start_balance(mock_bus, game, players)

        assert game.state == GameState.BALANCE
        assert game.balance_players == players
        assert game.current_votes == {"acquit": 0, "kill": 0, "revote": 0}
        assert game.vote_history == {}

        response = mock_bus.emit.call_args[0][0]
        assert "Баланс между: [2, 3, 5]" in response.text
        assert f"Первым голосует Игрок №{game.voting_queue[0].number}" in response.text

    @pytest.mark.asyncio
    async def test_initialize_queue(self, mock_bus, game):
        players = [1, 4]

        await start_balance(mock_bus, game, players)

        assert isinstance(game.voting_queue, deque)
        assert len(game.voting_queue) > 0


class TestResolveBalance:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True
            game.players[i].has_alibi = False

        game.balance_players = [2, 3, 4]

        return game

    @pytest.mark.asyncio
    async def test_acquit_wins(self, mock_bus, game):
        game.current_votes = {"acquit": 5, "kill": 2, "revote": 1}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            await resolve_balance(mock_bus, game)

            response = mock_bus.emit.call_args[0][0]
            assert "Все ОПРАВДАНЫ" in response.text

            mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_revote_wins(self, mock_bus, game):
        game.current_votes = {"acquit": 2, "kill": 1, "revote": 5}
        game.revote_count = 0

        await resolve_balance(mock_bus, game)

        assert game.revote_count == 1
        assert game.state == GameState.REVOTE
        assert game.current_votes == {2: 0, 3: 0, 4: 0}

        response = mock_bus.emit.call_args[0][0]
        assert "ПЕРЕГОЛОСОВАНИЕ" in response.text

    @pytest.mark.asyncio
    async def test_kill_wins(self, mock_bus, game):
        game.current_votes = {"acquit": 1, "kill": 5, "revote": 2}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await resolve_balance(mock_bus, game)

                assert not game.players[2].is_alive
                assert not game.players[4].is_alive
                assert not game.players[3].is_alive

                response = mock_bus.emit.call_args_list[0][0][0]
                assert "По результатам баланса убиты: 2, 3, 4" in response.text

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_kill_with_alibi(self, mock_bus, game):
        game.players[3].has_alibi = True
        game.current_votes = {"acquit": 1, "kill": 5, "revote": 2}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await resolve_balance(mock_bus, game)

                assert not game.players[2].is_alive
                assert game.players[3].is_alive
                assert not game.players[4].is_alive

                response = mock_bus.emit.call_args_list[0][0][0]
                assert "По результатам баланса убиты: 2, 4" in response.text
                assert "Спасены алиби: 3" in response.text

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_all_saved_by_alibi(self, mock_bus, game):
        for player in game.balance_players:
            game.players_by_number[player].has_alibi = True

        game.current_votes = {"acquit": 1, "kill": 5, "revote": 2}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await resolve_balance(mock_bus, game)

                for player in game.balance_players:
                    assert game.players_by_number[player].is_alive

                response = mock_bus.emit.call_args_list[0][0][0]
                assert "убиты: никто" in response.text

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_trigger_victory(self, mock_bus, game):
        game.current_votes = {"acquit": 1, "kill": 5, "revote": 2}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = True

                await resolve_balance(mock_bus, game)

                mock_night.assert_not_called()


class TestIntegrationVotingPhases:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)
        game.simulation = False

        for i in range(1, 6):
            game.add_player(i, f"Player {i}")
            game.players[i].is_alive = True

        return game

    @pytest.mark.asyncio
    async def test_full_voting_cycle_with_elimination(self, mock_bus, game):
        game.nominated = [2, 3, 4]

        await start_voting(mock_bus, game)
        assert game.state == GameState.VOTING

        game.current_votes = {2: 4, 3: 1, 4: 2}

        with patch(
            "engine.phases.voting.eliminate", new_callable=AsyncMock
        ) as mock_eliminate:
            with patch("engine.phases.night.start_night", new_callable=AsyncMock):
                await finish_voting(mock_bus, game)
                mock_eliminate.assert_called_once_with(mock_bus, game, 2)

    @pytest.mark.asyncio
    async def test_full_balance_cycle(self, mock_bus, game):
        game.nominated = [2, 3]
        game.revote_count = 0

        await start_balance(mock_bus, game, [2, 3])
        assert game.state == GameState.BALANCE

        game.current_votes = {"acquit": 2, "kill": 4, "revote": 1}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            with patch(
                "engine.phases.voting.check_victory", new_callable=AsyncMock
            ) as mock_victory:
                mock_victory.return_value = False

                await resolve_balance(mock_bus, game)

                assert not game.players[2].is_alive
                assert not game.players[3].is_alive

                mock_night.assert_called_once_with(mock_bus, game)

    @pytest.mark.asyncio
    async def test_revote_cycle(self, mock_bus, game):
        game.nominated = [2, 3, 4]
        game.revote_count = 0

        await start_voting(mock_bus, game)

        game.current_votes = {2: 2, 3: 2, 4: 2}

        await finish_voting(mock_bus, game)
        assert game.state == GameState.BALANCE

        game.current_votes = {"acquit": 2, "kill": 1, "revote": 4}

        await resolve_balance(mock_bus, game)

        game.current_votes = {2: 2, 3: 2, 4: 2}

        with patch(
            "engine.phases.night.start_night", new_callable=AsyncMock
        ) as mock_night:
            await finish_voting(mock_bus, game)

            response = mock_bus.emit.call_args[0][0]
            assert "Автоматическое оправдание" in response.text

            mock_night.assert_called_once_with(mock_bus, game)
