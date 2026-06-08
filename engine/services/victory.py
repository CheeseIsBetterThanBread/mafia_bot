from connection.events import ResponseBase
from connection.event_bus import EventBus

from game_info.roles import MAFIA_TEAM
from game_info.teams import Team

from engine.game_state import Game, GameState

from utils.logger import LOGGER
from utils.win_rate_db import win_rate_database


async def check_victory(bus: EventBus, game: Game):
    if game.simulation:
        return False

    alive = game.get_alive_players()

    if not alive:
        LOGGER.verbose_debug("Everyone died: mafia wins")
        win_rate_database.update_win_rate_info(game, Team.MAFIA)
        response = ResponseBase(
            game.chat_id, "💀 Все умерли — победа мафии", valid=True
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    mafia = sum(
        1
        for p in alive
        if p.role in MAFIA_TEAM or (p.role == "Двуликий" and p.found_mafia)
    )

    maniac = sum(1 for p in alive if p.role.startswith("Маньяк"))

    town = len(alive) - mafia - maniac

    if len(alive) <= 2 and maniac > 0:
        LOGGER.verbose_debug("Maniac is left with the victim: maniac wins")
        win_rate_database.update_win_rate_info(game, Team.MANIAC)
        response = ResponseBase(
            game.chat_id,
            "🔪 Маньяк остался один на один с жертвой! ПОБЕДА МАНЬЯКА!",
            valid=True,
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    if mafia == 0 and maniac == 0:
        LOGGER.verbose_debug("Only citizens are left: citizens win")
        win_rate_database.update_win_rate_info(game, Team.CITIZEN)
        response = ResponseBase(
            game.chat_id,
            "🕊 Вся мафия и маньяки уничтожены! ПОБЕДА МИРНОГО ГОРОДА!",
            valid=True,
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    if mafia >= town and maniac == 0:
        LOGGER.verbose_debug("Mafia dominates table: mafia wins")
        win_rate_database.update_win_rate_info(game, Team.MAFIA)
        response = ResponseBase(
            game.chat_id,
            "🕴 Мафий за столом стало не меньше, чем мирных! ПОБЕДА МАФИИ!",
            valid=True,
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    return False
