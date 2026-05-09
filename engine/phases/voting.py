from connection.events import ResponseBase
from connection.event_bus import EventBus

from engine.game_state import Game, GameState
from engine.models import Player


async def eliminate(bus: EventBus, game: Game, killed: int):
    player: Player = game.players_by_number[killed]

    if player.has_alibi:
        response = ResponseBase(
            game.chat_id,
            f"🛡 Игрок №{killed} должен был покинуть стол, но у него оказалось АЛИБИ! Он выживает.",
            valid=True
        )
        await bus.emit(response)
    else:
        player.alive = False
        response = ResponseBase(
            game.chat_id,
            f"💀 Игрок №{killed} покидает стол!",
            valid=True
        )
        await bus.emit(response)

        from engine.services.victory import check_victory
        if await check_victory(bus, game):
            return

    response = ResponseBase(
        game.chat_id,
        "Город засыпает...",
        valid=True
    )
    await bus.emit(response)

    from engine.phases.night import start_night
    await start_night(bus, game)


async def start_voting(bus: EventBus, game: Game):
    if len(game.nominated) > 1:
        game.state = GameState.VOTING
        game.current_votes = {num: 0 for num in game.nominated}
        game.vote_history = {}
        game.voting_queue = game.build_daily_queue()

        response = ResponseBase(
            game.chat_id,
            f"🗳 Начинаем голосование! Выставлены: {game.nominated}.\nПервым голосует Игрок №{game.voting_queue[0].number}. Пишите /vote",
            valid=True
        )
        await bus.emit(response)
        return

    scapegoat = game.nominated[0]
    response = ResponseBase(
        game.chat_id,
        f"⚡️ Так как выставлен всего 1 игрок, голосование не проводится. Срабатывает АВТОКИК!",
        valid=True
    )
    await bus.emit(response)

    await eliminate(bus, game, scapegoat)


async def finish_voting(bus: EventBus, game: Game):
    max_v = max(game.current_votes.values())
    leaders = [n for n, v in game.current_votes.items() if v == max_v]

    if len(leaders) == 1:
        await eliminate(bus, game, leaders[0])
        return

    if game.revote_count == 0:
        await start_balance(bus, game, leaders)
        return

    response = ResponseBase(
        game.chat_id,
        "⚖️ Голоса снова разделились! Автоматическое оправдание. Город засыпает...",
        valid=True
    )
    await bus.emit(response)

    from engine.phases.night import start_night
    await start_night(bus, game)


async def start_balance(bus: EventBus, game: Game, players):
    game.state = GameState.BALANCE
    game.balance_players = players
    game.current_votes = {"acquit": 0, "kill": 0, "revote": 0}
    game.vote_history = {}
    game.voting_queue = game.build_daily_queue()

    response = ResponseBase(
        game.chat_id,
        f"⚖️ Баланс между: {players}.\nПервым голосует Игрок №{game.voting_queue[0].number}. Пишите /balance",
        valid=True
    )
    await bus.emit(response)


async def resolve_balance(bus: EventBus, game: Game):
    v = game.current_votes
    max_v = max(v.values())

    if v["acquit"] == max_v:
        response = ResponseBase(
            game.chat_id,
            "🕊 Все ОПРАВДАНЫ.\nГород засыпает...",
            valid=True
        )
        await bus.emit(response)

        from engine.phases.night import start_night
        await start_night(bus, game)
        return

    if v["revote"] == max_v:
        game.revote_count += 1
        game.state = GameState.REVOTE
        game.current_votes = {num: 0 for num in game.balance_players}
        game.vote_history = {}
        game.voting_queue = game.build_daily_queue()

        response = ResponseBase(
            game.chat_id,
            "🔄 ПЕРЕГОЛОСОВАНИЕ! Пишите /vote за игроков на балансе.",
            valid=True
        )
        await bus.emit(response)
        return

    killed = []
    saved = []
    for num in game.balance_players:
        if game.players_by_number[num].has_alibi:
            saved.append(num)
        else:
            game.players_by_number[num].is_alive = False
            killed.append(num)

    killed_str = ", ".join(map(str, killed)) if killed else "никто"
    msg = f"💀 По результатам баланса убиты: {killed_str}."
    if saved:
        saved_str = ", ".join(map(str, saved))
        msg += f"\n🛡 Спасены алиби: {saved_str}."

    response = ResponseBase(
        game.chat_id,
        msg,
        valid=True
    )
    await bus.emit(response)

    from engine.services.victory import check_victory
    if await check_victory(bus, game):
        return

    response = ResponseBase(
        game.chat_id,
        "Город засыпает...",
        valid=True
    )
    await bus.emit(response)

    from engine.phases.night import start_night
    await start_night(bus, game)
