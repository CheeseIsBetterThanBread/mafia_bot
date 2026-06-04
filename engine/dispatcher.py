import asyncio
from random import shuffle

from config.roles import ROLE_DESCRIPTIONS
from config.role_actions import NightAction
from config.settings import (
    NULL_OPTION,
    NOMINATE_CALLBACK_TEMPLATE,
    VOTE_CALLBACK_TEMPLATE,
    BALANCE_CALLBACK_TEMPLATE,
    WARNING_OFFSET,
)

from connection.events import *
from connection.queries import QueryType

from utils.helpers import alive_sorted

from engine.game_state import Game, GameState
from engine.models import Player
from engine.presets import ROOM_PRESETS

from engine.phases.day import start_day, next_speaker
from engine.phases.defense import next_defense_speaker
from engine.phases.night import start_night, start_night_others
from engine.phases.voting import finish_voting, resolve_balance

from engine.services.night_resolution import resolve_night


class EventDispatcher:
    def __init__(self, engine):
        self.engine = engine
        self.bus = engine.bus

    async def handle(self, query):
        if not issubclass(type(query), QueryBase):
            raise ValueError(f"{type(query)} has to be a subclass of QueryBase")

        match query.cmd:
            case QueryType.START_GAME:
                await self._handle_start_game(query)
            case QueryType.JOIN_GAME:
                await self._handle_join_game(query)
            case QueryType.RUN:
                await self._handle_run(query)
            case QueryType.TERMINATE:
                await self._handle_terminate(query)
            case QueryType.START_NIGHT:
                await self._handle_start_night(query)
            case QueryType.SKIP_NIGHT:
                await self._handle_skip_night(query)
            case QueryType.ALIVE:
                await self._handle_alive(query)
            case QueryType.DESCRIPTION:
                await self._handle_description(query)
            case QueryType.ROLES:
                await self._handle_roles(query)
            case QueryType.NOMINATED:
                await self._handle_nominated(query)
            case QueryType.VOTED:
                await self._handle_voted(query)
            case QueryType.STATUS:
                await self._handle_status(query)
            case QueryType.SPEECH:
                await self._handle_speech(query)
            case QueryType.END_SPEECH:
                await self._handle_end_speech(query)
            case QueryType.MAFIA_CHAT:
                await self._handle_mafia_chat(query)
            case QueryType.PRE_NOMINATE:
                await self._handle_pre_nominate(query)
            case QueryType.NOMINATE:
                await self._handle_nominate(query)
            case QueryType.PRE_VOTE:
                await self._handle_pre_vote(query)
            case QueryType.VOTE:
                await self._handle_vote(query)
            case QueryType.PRE_BALANCE:
                await self._handle_pre_balance(query)
            case QueryType.BALANCE:
                await self._handle_balance(query)
            case QueryType.NIGHT_ACTION:
                await self._handle_night_action(query)
            case _:
                raise ValueError(f"Unknown query type: {query.cmd}")

    async def __not_admin(self, query):
        if query.user_id in query.admin_ids:
            return False

        await self.__send_response_base(
            query.chat_id,
            "⛔️ Эта команда доступна только создателю игры!",
            valid=False,
        )

        return True

    async def __validate_game(self, query: InfoQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state in [GameState.LOBBY, GameState.FINISHED]:
            await self.__send_response_base(
                query.chat_id, "Игра сейчас не идет.", valid=False
            )
            return None

        return game

    async def __send_response(self, response):
        await self.bus.emit(response)

    async def __send_response_base(
        self, chat_id: int, text: str, parse_mode=None, valid=False
    ):
        response = ResponseBase(chat_id, text, parse_mode, valid)
        await self.__send_response(response)

    async def __send_response_with_options(
        self,
        candidates,
        chat_id: int,
        text: str,
        parse_mode=None,
        valid=False,
        cmd=None,
    ):
        response = ResponseWithOptions(
            candidates, chat_id, text, parse_mode, valid, cmd
        )
        await self.__send_response(response)

    # --- GAME ---

    async def _handle_start_game(self, query: StartGameQuery):
        if query.chat_type == "private":
            await self.__send_response_base(
                query.chat_id, "Играть нужно в группе", valid=False
            )
            return
        if await self.__not_admin(query):
            return

        if (
            query.chat_id in self.engine.games
            and self.engine.games[query.chat_id].state != GameState.FINISHED
        ):
            await self.__send_response_base(
                query.chat_id, "Игра в этом чате уже запущена!", valid=False
            )
            return

        self.engine.create_game(query.chat_id)
        options = [("✋ Присоединиться", "join_game")]
        await self.__send_response_with_options(
            options,
            query.chat_id,
            "Регистрация на Мафию открыта! Нажмите кнопку ниже.",
            valid=True,
            cmd=query.cmd,
        )

    async def _handle_join_game(self, query: JoinQuery):
        invalid_response = ResponseWithAlert(query.callback, False, query.chat_id, "")
        valid_response = ResponseWithAlert(
            query.callback, True, query.chat_id, "", regenerate_keyboard=True
        )

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.LOBBY:
            invalid_response.text = "Нет открытого лобби."
            await self.__send_response(invalid_response)
            return

        added = game.add_player(query.user_id, query.username)
        if not added:
            invalid_response.text = "Ты уже зарегистрирован!"
            await self.__send_response(invalid_response)
            return

        valid_response.text = (
            f"Зарегистрировано: {len(game.players)} чел.\n"
            + "\n".join([f"{p.number}. {p.name}" for p in game.players.values()])
        )
        await self.__send_response(valid_response)

    async def _handle_run(self, query: RunQuery):
        if await self.__not_admin(query):
            return

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.LOBBY:
            return

        player_count = len(game.players)
        if player_count not in ROOM_PRESETS:
            await self.__send_response_base(
                query.chat_id,
                f"Для старта нужно другое количество игроков (сейчас {player_count}).",
                valid=False,
            )
            return

        roles = game.set_preset(player_count)
        shuffle(roles)

        game.day_starter_num = ((game.game_number - 1) % player_count) + 1

        for i, player in enumerate(game.players.values()):
            player.role = "Мирный житель" if game.simulation else roles[i]

        mafia_members = [p for p in game.players.values() if p.role in game.mafia_team]
        mafia_text = "\n".join(
            [f"№{p.number} — {p.name} ({p.role})" for p in mafia_members]
        )

        for player in game.players.values():
            msg = f"🔢 Твой игровой номер: {player.number}\n🎭 Твоя роль: {player.role}\n\n📖 Что делает твоя роль:\n{ROLE_DESCRIPTIONS[player.role]}"
            if player.role in game.mafia_team:
                msg += f"\n\n🕴 Твоя команда:\n{mafia_text}\n\n*Ночью вы можете общаться с командой прямо здесь, отправляя сообщения боту!*"

            await self.__send_response_base(
                player.user_id, msg, parse_mode="HTML", valid=True
            )

        await self.__send_response_base(
            query.chat_id,
            f"🎲 Игра началась!\nНабор ролей: {', '.join(game.current_preset)}",
            valid=True,
        )

        unique_roles = set(game.current_preset)
        desc_text = "📖 <b>Справка по ролям на эту игру:</b>\n\n"
        for r in unique_roles:
            desc = ROLE_DESCRIPTIONS.get(r, "Описание отсутствует.")
            desc_text += f"🔹 <b>{r}</b>: {desc}\n\n"

        await self.__send_response_base(
            query.chat_id, desc_text, parse_mode="HTML", valid=True
        )

        await start_day(self.bus, game)

    async def _handle_terminate(self, query: TerminateQuery):
        if await self.__not_admin(query):
            return

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state == GameState.FINISHED:
            return

        game.state = GameState.FINISHED
        await self.__send_response_base(
            query.chat_id, "Игра прервана администратором", valid=True
        )

    # --- NIGHT ENFORCEMENT ---

    async def _handle_start_night(self, query: StartNightQuery):
        if await self.__not_admin(query):
            return

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state in [
            GameState.LOBBY,
            GameState.FINISHED,
            GameState.NIGHT_THIEF,
            GameState.NIGHT,
        ]:
            return

        if game.current_speech_task and not game.current_speech_task.done():
            game.current_speech_task.cancel()

        await self.__send_response_base(
            query.chat_id,
            "🌙 Принудительно наступает Ночь! Город засыпает...",
            valid=True,
        )

        await start_night(self.bus, game)

    async def _handle_skip_night(self, query: SkipNightQuery):
        if await self.__not_admin(query):
            return

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state not in [GameState.NIGHT_THIEF, GameState.NIGHT]:
            return

        if game.state == GameState.NIGHT:
            await resolve_night(self.bus, game)
            return

        await self.__send_response_base(
            query.chat_id, "🤐 Вор никого не заклеил.", valid=True
        )

        thief = next((p for p in game.get_alive_players() if p.role == "Вор"), None)
        if thief:
            thief.last_rek = None
        await start_night_others(self.bus, game)

    # --- INFO ---

    async def _handle_alive(self, query: InfoQuery):
        game: Game = await self.__validate_game(query)
        if game is None:
            return

        alive = alive_sorted(game.get_alive_players())
        text = "👤 Живые игроки за столом:\n" + "\n".join(
            [f"№{p.number} — {p.name}" for p in alive]
        )
        await self.__send_response_base(query.chat_id, text, valid=True)

    async def _handle_description(self, query: InfoQuery):
        game: Game = await self.__validate_game(query)
        if game is None:
            return

        unique_roles = set(game.current_preset)
        desc_text = "📖 <b>Справка по ролям в этой игре:</b>\n\n"
        for r in unique_roles:
            desc = ROLE_DESCRIPTIONS.get(r, "Описание отсутствует.")
            desc_text += f"🔹 <b>{r}</b>: {desc}\n\n"

        await self.__send_response_base(
            query.chat_id, desc_text, parse_mode="HTML", valid=True
        )

    async def _handle_roles(self, query: InfoQuery):
        game: Game = await self.__validate_game(query)
        if game is None:
            return

        await self.__send_response_base(
            query.chat_id,
            f"📜 Набор ролей в этой игре:\n{', '.join(game.current_preset)}",
            valid=True,
        )

    async def _handle_nominated(self, query: InfoQuery):
        game: Game = await self.__validate_game(query)
        if game is None:
            return

        if game and game.nominated:
            await self.__send_response_base(
                query.chat_id,
                "Выставлены: " + ", ".join(map(str, game.nominated)),
                valid=True,
            )
            return

        await self.__send_response_base(
            query.chat_id, "Пока никто не выставлен.", valid=True
        )

    async def _handle_voted(self, query: InfoQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state not in [
            GameState.VOTING,
            GameState.REVOTE,
            GameState.BALANCE,
        ]:
            await self.__send_response_base(
                query.chat_id, "Сейчас не идет голосование.", valid=False
            )
            return

        if not getattr(game, "vote_history", None):
            await self.__send_response_base(
                query.chat_id, "Пока никто не проголосовал.", valid=True
            )
            return

        text = "📊 <b>Текущие результаты:</b>\n\n"

        if game.state in [GameState.VOTING, GameState.REVOTE]:
            for t_num, votes in game.current_votes.items():
                text += f"Против №{t_num}: {votes} голосов\n"
        else:
            text += f"Оправдать: {game.current_votes.get('acquit', 0)}\n"
            text += f"Убить всех: {game.current_votes.get('kill', 0)}\n"
            text += f"Переголосовать: {game.current_votes.get('revote', 0)}\n"

        text += "\n📝 <b>Кто как проголосовал:</b>\n"
        for p_num, v_target in game.vote_history.items():
            if game.state in [GameState.VOTING, GameState.REVOTE]:
                text += f"Игрок №{p_num} ➡️ против №{v_target}\n"
            else:
                text += f"Игрок №{p_num} ➡️ {v_target}\n"

        await self.__send_response_base(
            query.chat_id, text, parse_mode="HTML", valid=True
        )

    async def _handle_status(self, query: InfoQuery):
        game: Game = await self.__validate_game(query)
        if game is None:
            return

        alive = alive_sorted(game.get_alive_players())
        text = (
            "👤 Живые игроки за столом:\nФормат: номер - имя - число сюрикенов\n"
            "\n".join([f"№{p.number} — {p.name} - {p.shurikens}" for p in alive])
        )
        await self.__send_response_base(query.chat_id, text, valid=True)

    # --- DAY / SPEECH ---

    async def _handle_speech(self, query: SpeechRelatedQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game:
            return

        if game.state not in [GameState.DAY, GameState.DEFENSE]:
            return

        player = game.players.get(query.user_id)
        if not player:
            return

        is_defense = False
        if game.state == GameState.DAY:
            if not game.speech_queue or player.user_id != game.speech_queue[0].user_id:
                await self.__send_response_base(
                    query.chat_id, "Сейчас не ваша очередь говорить!", valid=False
                )
                return
            is_defense = False
        elif game.state == GameState.DEFENSE:
            if (
                not game.defense_queue
                or player.user_id != game.defense_queue[0].user_id
            ):
                await self.__send_response_base(
                    query.chat_id, "Сейчас не ваша очередь оправдываться!", valid=False
                )
                return
            is_defense = True

        if game.current_speech_task and not game.current_speech_task.done():
            await self.__send_response_base(
                query.chat_id, "Вы уже выступаете!", valid=False
            )
            return

        speech_time = game.calculate_speech_time()

        if is_defense:
            await self.__send_response_base(
                query.chat_id,
                f"⏱ Игрок №{player.number}, ваши {speech_time} секунд на оправдание пошли!\nЧтобы закончить речь досрочно: /end_speech",
                valid=True,
            )
        else:
            await self.__send_response_base(
                query.chat_id,
                f"⏱ Игрок №{player.number}, ваши {speech_time} секунд пошли!\nВы можете выставлять кандидатов: /nominate \nЧтобы закончить речь досрочно: /end_speech",
                valid=True,
            )

        async def timer_task():
            try:
                await asyncio.sleep(speech_time - WARNING_OFFSET)
                if not (
                    player.is_alive and game.state in [GameState.DAY, GameState.DEFENSE]
                ):
                    return

                await self.__send_response_base(
                    query.chat_id,
                    f"⚠️ Игрок №{player.number}, осталось {WARNING_OFFSET} секунд!",
                    valid=True,
                )

                await asyncio.sleep(WARNING_OFFSET)
                if not (
                    player.is_alive and game.state in [GameState.DAY, GameState.DEFENSE]
                ):
                    return

                await self.__send_response_base(
                    query.chat_id,
                    f"🛑 Игрок №{player.number}, время вышло!",
                    valid=True,
                )

                if is_defense:
                    await next_defense_speaker(self.bus, game)
                else:
                    await next_speaker(self.bus, game)

            except asyncio.CancelledError:
                pass

            finally:
                game.current_speech_task = None

        game.current_speech_task = asyncio.create_task(timer_task())

    async def _handle_end_speech(self, query: SpeechRelatedQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game:
            return

        player = game.players.get(query.user_id)
        if not player:
            return

        if (
            game.state == GameState.DAY
            and game.speech_queue
            and player.user_id == game.speech_queue[0].user_id
        ):
            if game.current_speech_task and not game.current_speech_task.done():
                game.current_speech_task.cancel()

            await self.__send_response_base(
                query.chat_id,
                f"✅ Игрок №{player.number} завершил свою речь.",
                valid=True,
            )
            await next_speaker(self.bus, game)
            return

        if (
            game.state == GameState.DEFENSE
            and game.defense_queue
            and player.user_id == game.defense_queue[0].user_id
        ):
            if game.current_speech_task and not game.current_speech_task.done():
                game.current_speech_task.cancel()

            await self.__send_response_base(
                query.chat_id,
                f"✅ Игрок №{player.number} завершил свою оправдательную речь.",
                valid=True,
            )
            await next_defense_speaker(self.bus, game)

    # --- MAFIA CHAT ---

    async def _handle_mafia_chat(self, query: MafiaChatQuery):
        user_id = query.user_id

        active_game = None
        player = None
        for game in self.engine.games.values():
            if user_id in game.players and game.state in [
                GameState.NIGHT_THIEF,
                GameState.NIGHT,
            ]:
                active_game = game
                player = game.players[user_id]
                break

        if not active_game or not player or not player.is_alive:
            return
        if player.role not in active_game.mafia_team:
            return

        if player.is_glued:
            await self.__send_response_base(
                user_id,
                "🤐 Вы заклеены Вором! Вы не можете говорить в чате мафии этой ночью.",
                valid=False,
            )
            return

        sent_count = 0
        for other_p in active_game.get_alive_players():
            if other_p.role in active_game.mafia_team and other_p.user_id != user_id:
                await self.__send_response_base(
                    other_p.user_id,
                    f"🥷 [Чат мафии] Игрок №{player.number}: {query.text}",
                    valid=True,
                )
                sent_count += 1

        if sent_count == 0:
            await self.__send_response_base(
                user_id,
                "🥷 Вы остались единственным живым мафиози. Вас некому читать.",
                valid=False,
            )

    # --- NOMINATE ---

    async def _handle_pre_nominate(self, query: PreNominateQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.DAY or not game.speech_queue:
            return

        if getattr(game, "day_count", 1) == 1:
            await self.__send_response_base(
                query.chat_id,
                "⚠️ Сегодня первый день (день знакомств). Выставлять кандидатов на голосование запрещено!",
                valid=False,
            )
            return

        player = game.players.get(query.user_id)
        if not player or player.user_id != game.speech_queue[0].user_id:
            await self.__send_response_base(
                query.chat_id, "Сейчас не ваша очередь говорить!", valid=False
            )
            return

        if player.has_nominated:
            await self.__send_response_base(
                query.chat_id,
                "⚠️ Вы уже выставили одного кандидата на этом кругу!",
                valid=False,
            )
            return

        alive_players = game.get_alive_players()
        nominate_options = [
            (
                f"№{t.number} ({t.name})",
                NOMINATE_CALLBACK_TEMPLATE.format(
                    chat_id=query.chat_id, player_number=t.number
                ),
            )
            for t in alive_players
        ]
        nominate_options.append(
            (
                "❌ Отмена",
                NOMINATE_CALLBACK_TEMPLATE.format(
                    chat_id=query.chat_id, player_number=NULL_OPTION
                ),
            )
        )
        await self.__send_response_with_options(
            nominate_options,
            query.chat_id,
            "Кого вы хотите выставить на голосование?",
            valid=True,
            cmd=query.cmd,
        )

    async def _handle_nominate(self, query: NominateQuery):
        invalid_response = ResponseWithAlert(query.callback, False, query.chat_id, "")
        valid_response = ResponseWithAlert(query.callback, True, query.chat_id, "")

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.DAY or not game.speech_queue:
            invalid_response.text = "Действие недоступно."
            await self.__send_response(invalid_response)
            return

        player = game.players.get(query.user_id)

        if not player or player.user_id != game.speech_queue[0].user_id:
            invalid_response.text = "Не лезь, сейчас не твоя очередь!"
            await self.__send_response(invalid_response)
            return

        if player.has_nominated:
            invalid_response.text = "Вы уже выставили кандидата!"
            await self.__send_response(invalid_response)
            return

        if query.target_id == NULL_OPTION:
            valid_response.text = (
                "❌ Вы отменили выставление. Вы можете продолжить свою речь."
            )
            await self.__send_response(valid_response)
            return

        if (
            query.target_id not in game.players_by_number
            or not game.players_by_number[query.target_id].is_alive
        ):
            invalid_response.text = "Этот игрок уже покинул стол!"
            await self.__send_response(invalid_response)
            return

        if query.target_id in game.nominated:
            invalid_response.text = "Этот игрок уже выставлен на голосование!"
            await self.__send_response(invalid_response)
            return

        game.nominated.append(query.target_id)
        player.has_nominated = True

        valid_response.text = f"👉 Игрок №{player.number} выставил Игрока №{query.target_id} на голосование."
        await self.__send_response(valid_response)

    # --- VOTE ---

    async def _handle_pre_vote(self, query: PreVoteQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state not in [GameState.VOTING, GameState.REVOTE]:
            return

        player = game.players.get(query.user_id)
        if (
            not player
            or not game.voting_queue
            or player.user_id != game.voting_queue[0].user_id
        ):
            await self.__send_response_base(
                query.chat_id, "Сейчас не ваша очередь голосовать!", valid=False
            )
            return

        allowed = (
            game.balance_players if game.state == GameState.REVOTE else game.nominated
        )
        vote_options = [
            (
                f"№{num} ({game.players_by_number[num].name})",
                VOTE_CALLBACK_TEMPLATE.format(chat_id=query.chat_id, player_number=num),
            )
            for num in allowed
        ]
        await self.__send_response_with_options(
            vote_options,
            query.chat_id,
            "Против кого вы голосуете?",
            valid=True,
            cmd=query.cmd,
        )

    async def _handle_vote(self, query: VoteQuery):
        invalid_response = ResponseWithAlert(query.callback, False, query.chat_id, "")
        valid_response = ResponseWithAlert(query.callback, True, query.chat_id, "")

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state not in [GameState.VOTING, GameState.REVOTE]:
            invalid_response.text = "Голосование сейчас не идет."
            await self.__send_response(invalid_response)
            return

        player = game.players.get(query.user_id)
        if (
            not player
            or not game.voting_queue
            or player.user_id != game.voting_queue[0].user_id
        ):
            invalid_response.text = "Сейчас не ваша очередь!"
            await self.__send_response(invalid_response)
            return

        allowed = (
            game.balance_players if game.state == GameState.REVOTE else game.nominated
        )
        if query.target_id not in allowed:
            invalid_response.text = "За этого игрока нельзя голосовать!"
            await self.__send_response(invalid_response)
            return

        game.current_votes[query.target_id] += 1
        game.vote_history[player.number] = query.target_id
        game.voting_queue.popleft()

        valid_response.text = (
            f"🗣 Игрок №{player.number} проголосовал против Игрока №{query.target_id}!"
        )
        await self.__send_response(valid_response)

        if not game.voting_queue:
            await finish_voting(self.bus, game)
            return

        await self.__send_response_base(
            query.chat_id,
            f"Следующий голосует Игрок №{game.voting_queue[0].number}. Напишите /vote",
            valid=True,
        )

    # --- BALANCE ---

    async def _handle_pre_balance(self, query: PreBalanceQuery):
        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.BALANCE:
            return

        player = game.players.get(query.user_id)
        if (
            not player
            or not game.voting_queue
            or player.user_id != game.voting_queue[0].user_id
        ):
            await self.__send_response_base(
                query.chat_id, "Сейчас не ваша очередь!", valid=False
            )
            return

        balance_options = []
        balance_options.append(
            (
                "🕊 Оправдать",
                BALANCE_CALLBACK_TEMPLATE.format(chat_id=query.chat_id, number=1),
            )
        )
        balance_options.append(
            (
                "💀 Убить всех",
                BALANCE_CALLBACK_TEMPLATE.format(chat_id=query.chat_id, number=2),
            )
        )
        balance_options.append(
            (
                "🔄 Переголосовать",
                BALANCE_CALLBACK_TEMPLATE.format(chat_id=query.chat_id, number=3),
            )
        )

        await self.__send_response_with_options(
            balance_options,
            query.chat_id,
            "Ваш выбор на балансе?",
            valid=True,
            cmd=query.cmd,
        )

    async def _handle_balance(self, query: BalanceQuery):
        invalid_response = ResponseWithAlert(query.callback, False, query.chat_id, "")
        valid_response = ResponseWithAlert(query.callback, True, query.chat_id, "")

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state != GameState.BALANCE:
            invalid_response.text = "Баланс не идет."
            await self.__send_response(invalid_response)
            return

        player = game.players.get(query.user_id)
        if (
            not player
            or not game.voting_queue
            or player.user_id != game.voting_queue[0].user_id
        ):
            invalid_response.text = "Сейчас не ваша очередь!"
            await self.__send_response(invalid_response)
            return

        options = {1: "acquit", 2: "kill", 3: "revote"}
        names = {1: "Оправдать", 2: "Убить всех", 3: "Переголосовать"}

        game.current_votes[options[query.target_id]] += 1
        game.vote_history[player.number] = names[query.target_id]
        game.voting_queue.popleft()

        valid_response.text = (
            f"🗣 Игрок №{player.number} выбрал: {names[query.target_id]}!"
        )
        await self.__send_response(valid_response)

        if not game.voting_queue:
            await resolve_balance(self.bus, game)
            return

        await self.__send_response_base(
            query.chat_id,
            f"Следующий голосует Игрок №{game.voting_queue[0].number}. Напишите /balance",
            valid=True,
        )

    # --- NIGHT ACTION ---

    async def __repeated_guard(self, query: NightActionQuery, player: Player):
        if query.action not in [
            NightAction.ROB,
            NightAction.HEAL,
            NightAction.TULA,
            NightAction.ALIBI,
            NightAction.MANIAC_HEAL,
        ]:
            return False

        invalid_response = ResponseWithAlert(
            query.callback, False, query.user_id, "Нельзя делать это две ночи подряд"
        )
        if query.action == NightAction.ROB and player.last_rek == query.target:
            await self.__send_response(invalid_response)
            return True
        if (
            query.action in [NightAction.HEAL, NightAction.TULA]
            and player.last_healed == query.target
        ):
            await self.__send_response(invalid_response)
            return True
        if query.action == NightAction.ALIBI and player.last_alibi == query.target:
            await self.__send_response(invalid_response)
            return True
        if query.action == NightAction.MANIAC_HEAL and player.last_man_heal:
            await self.__send_response(invalid_response)
            return True

        return False

    async def __handle_thief(self, query: NightActionQuery, game: Game):
        player: Player = game.players[query.user_id]
        valid_response = ResponseWithAlert(query.callback, True, query.user_id, "")

        game.expected_night_actors[query.user_id].remove(NightAction.ROB)

        if query.target == NULL_OPTION:
            player.last_rek = NULL_OPTION

            valid_response.text = "✅ Вы решили никого не клеить."
            await self.__send_response(valid_response)

            await self.__send_response_base(
                query.chat_id, "🤐 Вор никого не заклеил.", valid=True
            )

            await start_night_others(self.bus, game)
            return

        target = game.players_by_number[query.target]
        target.is_glued = True
        player.last_rek = query.target

        valid_response.text = f"✅ Вы заклеили Игрока №{query.target}."
        await self.__send_response(valid_response)

        await self.__send_response_base(
            query.chat_id,
            f"🤐 Вор заклеил Игрока №{query.target}! Он пропускает день.",
            valid=True,
        )

        await start_night_others(self.bus, game)

    async def __handle_don_check(self, query: NightActionQuery, game: Game):
        t_player = game.players_by_number[query.target]
        ans = (
            f"✅ Игрок №{query.target} — ШЕРИФ!"
            if t_player.role == "Шериф"
            else f"❌ Игрок №{query.target} — НЕ ШЕРИФ."
        )

        await self.__send_response_base(query.user_id, ans, valid=True)

    async def __handle_sheriff_check(self, query: NightActionQuery, game: Game):
        t_player = game.players_by_number[query.target]
        can_be_discovered = (
            t_player.found_mafia and t_player.found_mafia_day < game.day_count
        )
        is_bad_dvul = t_player.role == "Двуликий" and can_be_discovered

        if t_player.role in game.mafia_team or is_bad_dvul:
            ans = f"✅ Игрок №{query.target} — МАФИЯ ({t_player.role})!"
        else:
            ans = f"❌ Игрок №{query.target} — НЕ МАФИЯ."

        await self.__send_response_base(query.user_id, ans, valid=True)

    async def __handle_two_face_check(self, query: NightActionQuery, game: Game):
        player = game.players[query.user_id]
        target = game.players_by_number[query.target]

        if target.role not in game.mafia_team:
            await self.__send_response_base(
                query.user_id,
                f"❌ Игрок №{query.target} не состоит в Мафии.",
                valid=True,
            )
            return

        player.found_mafia = True
        player.found_mafia_day = game.day_count
        maf_list = ", ".join(
            [
                f"№{p.number} ({p.role})"
                for p in game.get_alive_players()
                if p.role in game.mafia_team
            ]
        )

        await self.__send_response_base(
            query.user_id,
            f"🎯 Вы нашли Мафию! Состав: {maf_list}. Со следующей ночи вы убиваете сами.",
            valid=True,
        )
        for maf in game.get_alive_players():
            if maf.role not in game.mafia_team:
                continue

            await self.__send_response_base(
                maf.user_id,
                f"🎭 Двуликий нашел нас! Это Игрок №{player.number}.",
                valid=True,
            )

    def __handle_maniac(self, query: NightActionQuery, game: Game):
        player = game.players[query.user_id]
        player.last_man_heal = query.action == NightAction.MANIAC_HEAL

        if (
            query.action == NightAction.MANIAC_KILL
            and NightAction.MANIAC_HEAL in game.expected_night_actors[player.user_id]
        ):
            game.expected_night_actors[player.user_id].remove(NightAction.MANIAC_HEAL)
        if (
            query.action == NightAction.MANIAC_HEAL
            and NightAction.MANIAC_KILL in game.expected_night_actors[player.user_id]
        ):
            game.expected_night_actors[player.user_id].remove(NightAction.MANIAC_KILL)

    async def _handle_night_action(self, query: NightActionQuery):
        invalid_response = ResponseWithAlert(query.callback, False, query.user_id, "")
        valid_response = ResponseWithAlert(query.callback, True, query.user_id, "")

        act_code = query.action
        target_num = query.target

        game: Game = self.engine.get_game(query.chat_id)
        if not game or game.state not in [GameState.NIGHT_THIEF, GameState.NIGHT]:
            invalid_response.text = "Ночь уже прошла!"
            await self.__send_response(invalid_response)
            return

        user_id = query.user_id
        player = game.players.get(user_id)

        if (
            not player
            or user_id not in game.expected_night_actors
            or act_code not in game.expected_night_actors[user_id]
        ):
            invalid_response.text = "Это действие вам сейчас недоступно."
            await self.__send_response(invalid_response)
            return

        if await self.__repeated_guard(query, player):
            return

        if act_code == NightAction.ROB:
            await self.__handle_thief(query, game)
            return

        game.night_actions[user_id][act_code] = target_num

        match act_code:
            case NightAction.DON_CHECK:
                await self.__handle_don_check(query, game)
            case NightAction.SHERIFF_CHECK:
                await self.__handle_sheriff_check(query, game)
            case NightAction.TWO_FACE_CHECK:
                await self.__handle_two_face_check(query, game)

        if act_code in [NightAction.MANIAC_KILL, NightAction.MANIAC_HEAL]:
            self.__handle_maniac(query, game)

        game.expected_night_actors[user_id].remove(act_code)

        valid_response.text = f"✅ Выбор принят: Игрок №{target_num}"
        await self.__send_response(valid_response)

        all_done = all(len(acts) == 0 for acts in game.expected_night_actors.values())
        if all_done:
            await resolve_night(self.bus, game)
