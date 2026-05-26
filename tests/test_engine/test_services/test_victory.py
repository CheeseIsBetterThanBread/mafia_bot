import pytest
from unittest.mock import AsyncMock

from engine.services.victory import (
    check_victory,
    EventBus,
    Game,
    GameState,
    ResponseBase,
)


class TestCheckVictory:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def game(self):
        game = Game(chat_id=-100123456789, game_counter=1)

        game.add_player(1, "Player 1")
        game.add_player(2, "Player 2")
        game.add_player(3, "Player 3")
        game.add_player(4, "Player 4")

        return game

    @pytest.mark.asyncio
    async def test_victory_all_dead(self, mock_bus, game):
        for player in game.players.values():
            player.is_alive = False

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert isinstance(response, ResponseBase)
        assert response.chat_id == game.chat_id
        assert "Все умерли" in response.text
        assert response.is_valid is True

    @pytest.mark.asyncio
    async def test_victory_town_wins_no_mafia_no_maniac(self, mock_bus, game):
        for player in game.players.values():
            player.role = "Мирный житель"

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МИРНОГО ГОРОДА" in response.text

    @pytest.mark.asyncio
    async def test_victory_mafia_wins_outnumber_town(self, mock_bus, game):
        roles = ["Мафия", "Мафия", "Мирный житель", "Мирный житель"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МАФИИ" in response.text

    @pytest.mark.asyncio
    async def test_maniac_1v1_victory(self, mock_bus, game):
        for i, player in enumerate(game.players.values()):
            player.is_alive = i < 2

        players = list(game.players.values())
        players[0].role = "Маньяк"
        players[1].role = "Мирный житель"

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МАНЬЯКА" in response.text

    @pytest.mark.asyncio
    async def test_maniac_1v1_with_mafia(self, mock_bus, game):
        for i, player in enumerate(game.players.values()):
            player.is_alive = i < 2

        players = list(game.players.values())
        players[0].role = "Маньяк"
        players[1].role = "Мафия"

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED
        assert "ПОБЕДА МАНЬЯКА" in mock_bus.emit.call_args[0][0].text

    @pytest.mark.asyncio
    async def test_no_victory_mafia_less_than_town(self, mock_bus, game):
        roles = ["Мафия", "Мирный житель", "Мирный житель", "Мирный житель"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        result = await check_victory(mock_bus, game)

        assert result is False
        assert game.state != GameState.FINISHED
        mock_bus.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_victory_maniac_not_1v1(self, mock_bus, game):
        roles = ["Маньяк", "Мафия", "Мирный житель", "Мирный житель"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        result = await check_victory(mock_bus, game)

        assert result is False
        assert game.state != GameState.FINISHED

    @pytest.mark.asyncio
    async def test_no_victory_with_maniac_present(self, mock_bus, game):
        roles = ["Маньяк", "Мафия", "Дон", "Мирный житель"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        result = await check_victory(mock_bus, game)

        assert result is False
        mock_bus.assert_not_called()

    @pytest.mark.asyncio
    async def test_two_face_as_mafia_when_found(self, mock_bus, game):
        roles = ["Мирный житель", "Мирный житель", "Мафия", "Двуликий"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        two_face = list(game.players.values())[3]
        two_face.found_mafia = True

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МАФИИ" in response.text

    @pytest.mark.asyncio
    async def test_two_face_not_mafia_when_not_found(self, mock_bus, game):
        roles = ["Мафия", "Мирный житель", "Мирный житель", "Двуликий"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        two_face = list(game.players.values())[3]
        two_face.found_mafia = False

        result = await check_victory(mock_bus, game)

        assert result is False
        mock_bus.assert_not_called()

    @pytest.mark.asyncio
    async def test_maniac_victory_all_dead_except_maniac(self, mock_bus, game):
        for i, player in enumerate(game.players.values()):
            player.is_alive = i == 0
            player.role = "Маньяк с бинтами"

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МАНЬЯКА" in response.text

    @pytest.mark.asyncio
    async def test_maniac_1v1_without_victory_three_players(self, mock_bus, game):
        for i, player in enumerate(game.players.values()):
            player.is_alive = i < 3

        players = list(game.players.values())
        players[0].role = "Маньяк"
        players[1].role = "Мирный житель"
        players[2].role = "Мирный житель"

        result = await check_victory(mock_bus, game)

        assert result is False
        mock_bus.assert_not_called()

    @pytest.mark.asyncio
    async def test_town_victory_with_maniac_present(self, mock_bus, game):
        for player in game.players.values():
            player.role = "Мирный житель"

        list(game.players.values())[0].role = "Маньяк"
        list(game.players.values())[0].is_alive = False

        result = await check_victory(mock_bus, game)

        assert result is True
        assert game.state == GameState.FINISHED

        mock_bus.emit.assert_called_once()
        response = mock_bus.emit.call_args[0][0]
        assert "ПОБЕДА МИРНОГО ГОРОДА" in response.text

    @pytest.mark.asyncio
    async def test_game_state_changes_only_on_victory(self, mock_bus, game):
        roles = ["Мафия", "Мирный житель", "Мирный житель", "Мирный житель"]
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]

        await check_victory(mock_bus, game)
        assert game.state != GameState.FINISHED

        for player in game.players.values():
            player.is_alive = False

        await check_victory(mock_bus, game)
        assert game.state == GameState.FINISHED
