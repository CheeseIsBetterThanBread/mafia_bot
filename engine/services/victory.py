from connection.events import ResponseBase
from connection.event_bus import EventBus

from engine.game_state import Game, GameState
from engine.roles import MAFIA_TEAM


async def check_victory(bus: EventBus, game: Game):
    alive = game.get_alive_players()

    if not alive:
        response = ResponseBase(
            game.chat_id,
            "💀 Все умерли — победа мафии",
            valid=True
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    mafia = sum(
        1 for p in alive
        if p.role in MAFIA_TEAM or (p.role == "Двуликий" and p.found_mafia)
    )

    maniac = sum(
        1 for p in alive
        if p.role.startswith("Маньяк")
    )

    town = len(alive) - mafia - maniac

    # маньяк 1v1
    if len(alive) == 2 and maniac > 0:
        response = ResponseBase(
            game.chat_id,
            "🔪 Маньяк остался один на один с жертвой! ПОБЕДА МАНЬЯКА!",
            valid=True
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    if mafia == 0 and maniac == 0:
        response = ResponseBase(
            game.chat_id,
            "🕊 Вся мафия и маньяки уничтожены! ПОБЕДА МИРНОГО ГОРОДА!",
            valid=True
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    if mafia >= town and maniac == 0:
        response = ResponseBase(
            game.chat_id,
            "🕴 Мафий за столом стало не меньше, чем мирных! ПОБЕДА МАФИИ!",
            valid=True
        )
        await bus.emit(response)
        game.state = GameState.FINISHED
        return True

    return False
