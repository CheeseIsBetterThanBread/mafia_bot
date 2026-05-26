from connection.event_bus import EventBus
from connection.events import QueryBase

from engine.dispatcher import EventDispatcher
from engine.game_state import Game


class GameEngine:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.games = {}  # chat_id -> Game
        self.dispatcher = EventDispatcher(self)
        self.game_counter = 0

    def get_game(self, chat_id):
        return self.games.get(chat_id)

    def create_game(self, chat_id):
        self.game_counter += 1
        game = Game(chat_id, self.game_counter)
        self.games[chat_id] = game

    def register(self):
        @self.bus.on(QueryBase)
        async def dispatch(query):
            """
            Главная точка входа всех событий
            """
            await self.dispatcher.handle(query)
