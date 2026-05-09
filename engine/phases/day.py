from connection.events import ResponseBase
from connection.event_bus import EventBus
from engine.game_state import Game, GameState


async def start_day(bus: EventBus, game: Game):
    game.state = GameState.DAY
    game.day_count += 1

    for p in game.players.values():
        p.has_nominated = False

    game.revote_count = 0

    if game.day_count > 1:
        alive_nums = sorted([p.number for p in game.get_alive_players()])
        if alive_nums:
            next_starter = alive_nums[0]
            for num in alive_nums:
                if num > game.day_starter_num:
                    next_starter = num
                    break
            game.day_starter_num = next_starter

    game.nominated = []
    game.speech_queue = game.build_daily_queue()
    if not game.speech_queue:
        return

    first = game.speech_queue[0]

    response = ResponseBase(
        game.chat_id,
        f"☀️ Наступает День {game.day_count}.\nПервым говорит Игрок №{first.number}. Напишите /speech.",
        valid=True
    )
    await bus.emit(response)


async def next_speaker(bus: EventBus, game: Game):
    if not game.speech_queue:
        return
    game.speech_queue.popleft()

    while game.speech_queue and game.speech_queue[0].is_glued:
        glued = game.speech_queue.popleft()
        response = ResponseBase(
            game.chat_id,
            f"🤐 Игрок №{glued.number} заклеен Вором и пропускает свою речь.",
            valid=True
        )
        await bus.emit(response)

    if game.speech_queue:
        current = game.speech_queue[0]
        response = ResponseBase(
            game.chat_id,
            f"🗣 Очередь Игрока №{current.number}. Напишите /speech для начала речи.",
            valid=True
        )
        await bus.emit(response)
        return

    response = ResponseBase(
        game.chat_id,
        "🎙 Все речи окончены!",
        valid=True
    )
    await bus.emit(response)

    from engine.phases.defense import start_defense
    await start_defense(bus, game)
