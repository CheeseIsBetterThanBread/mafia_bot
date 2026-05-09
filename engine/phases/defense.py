from collections import deque

from connection.events import ResponseBase
from connection.event_bus import EventBus

from engine.game_state import Game, GameState


async def start_defense(bus: EventBus, game: Game):
    if not game.nominated:
        response = ResponseBase(
            game.chat_id,
            "Никто не выставлен. Город засыпает...",
            valid=True
        )
        await bus.emit(response)

        from engine.phases.night import start_night
        await start_night(bus, game)
        return

    game.state = GameState.DEFENSE
    game.defense_queue = deque([
        game.players_by_number[n]
        for n in game.nominated
        if game.players_by_number[n].is_alive
    ])

    assert game.defense_queue

    first = game.defense_queue[0]
    response = ResponseBase(
        game.chat_id,
        f"⚖️ Выставлены игроки: {game.nominated}.\nПереходим к оправдательным речам! Первым говорит Игрок №{first.number}. Напишите /speech.",
        valid=True
    )
    await bus.emit(response)


async def next_defense_speaker(bus: EventBus, game: Game):
    if not game.defense_queue:
        return
    game.defense_queue.popleft()

    while game.defense_queue and game.defense_queue[0].is_glued:
        glued = game.defense_queue.popleft()
        response = ResponseBase(
            game.chat_id,
            f"🤐 Игрок №{glued.number} заклеен Вором и пропускает свою оправдательную речь.",
            valid=True
        )
        await bus.emit(response)

    if game.defense_queue:
        current = game.defense_queue[0]
        response = ResponseBase(
            game.chat_id,
            f"🗣 Очередь оправдываться Игрока №{current.number}. Напишите /speech для начала речи.",
            valid=True
        )
        await bus.emit(response)
        return

    response = ResponseBase(
        game.chat_id,
        "🎙 Все оправдательные речи окончены!",
        valid=True
    )
    await bus.emit(response)

    from engine.phases.voting import start_voting
    await start_voting(bus, game)
