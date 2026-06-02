class Event:
    def get_log_string(self): ...


# Базовые классы
class QueryBase(Event):
    def __init__(self, cmd, admin_ids, chat_id, user_id):
        self.cmd = cmd
        self.admin_ids = admin_ids
        self.chat_id = chat_id
        self.user_id = user_id

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, user_id=self.user_id
        )


class QueryWithCallback(QueryBase):
    def __init__(self, cmd, admin_ids, chat_id, user_id, callback):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.callback = callback


class QueryWithTarget(QueryWithCallback):
    def __init__(self, cmd, admin_ids, chat_id, user_id, callback, target_id):
        super().__init__(cmd, admin_ids, chat_id, user_id, callback)
        self.target_id = target_id

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {target_id}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            target_id=self.target_id,
        )


class ResponseBase(Event):
    def __init__(self, chat_id, text, parse_mode=None, valid=False):
        self.chat_id = chat_id
        self.text = text
        self.parse_mode = parse_mode
        self.is_valid = valid

    def get_log_string(self):
        template_string = "[{response_type}]: {chat_id} - {parse_mode} - {text_head}"
        return template_string.format(
            response_type=self.response_type,
            chat_id=self.chat_id,
            parse_mode=self.parse_mode if self.parse_mode else "default",
            text_head=self.text.split("\n")[0],
        )

    @property
    def response_type(self):
        return "ResponseBase"


class ResponseWithAlert(ResponseBase):
    def __init__(self, callback, valid, chat_id, text, parse_mode=None):
        super().__init__(chat_id, text, parse_mode, valid)
        self.callback = callback

    @property
    def response_type(self):
        return "ResponseWithAlert"


class ResponseWithOptions(ResponseBase):
    def __init__(self, candidates, chat_id, text, parse_mode=None, valid=False, cmd=None):
        super().__init__(chat_id, text, parse_mode, valid)
        self.candidates = candidates
        self.cmd = cmd

    @property
    def response_type(self):
        return "ResponseWithOptions"


# Обработка /start_game
class StartGameQuery(QueryBase):
    def __init__(self, cmd, admin_ids, chat_id, user_id, chat_type):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.chat_type = chat_type


# Обработка /join_game
class JoinQuery(QueryWithCallback):
    def __init__(self, cmd, admin_ids, chat_id, user_id, callback, username):
        super().__init__(cmd, admin_ids, chat_id, user_id, callback)
        self.username = username

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {username} - {count}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            username=self.username,
            count=len(self.admin_ids),
        )


# Обработка /run
RunQuery = QueryBase

# Обработка /alive, /description, /roles, /nominated, /voted, /status (wip)
InfoQuery = QueryBase

# Обработка /speech, /end_speech
SpeechRelatedQuery = QueryBase

# Обработка /nominate
PreNominateQuery = QueryBase
NominateQuery = QueryWithTarget

# Обработка /vote
PreVoteQuery = QueryBase
VoteQuery = QueryWithTarget

# Обработка /balance
PreBalanceQuery = QueryBase
BalanceQuery = QueryWithTarget

# Обработка /start_night
StartNightQuery = QueryBase

# Обработка /skip_night
SkipNightQuery = QueryBase


# Обработка ночных событий
class NightActionQuery(QueryWithCallback):
    def __init__(self, cmd, admin_ids, chat_id, user_id, callback, action, target):
        super().__init__(cmd, admin_ids, chat_id, user_id, callback)
        self.action = action
        self.target = target

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {action}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, action=self.action
        )


# Обработка чата мафии
class MafiaChatQuery(QueryBase):
    def __init__(self, cmd, admin_ids, chat_id, user_id, text):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.text = text

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {text_head}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, text_head=self.text.split("\n")[0]
        )
