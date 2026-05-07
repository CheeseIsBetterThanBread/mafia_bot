from connection.events import *


class TestQueryBase:
    def test_query_initialization(self):
        query = QueryBase(
            cmd="/start",
            admin_ids=[123, 456],
            chat_id=-100123456,
            user_id=789
        )

        assert query.cmd == "/start"
        assert query.admin_ids == [123, 456]
        assert query.chat_id == -100123456
        assert query.user_id == 789

    def test_query_get_log_string(self):
        query = QueryBase(
            cmd="/test",
            admin_ids=[1, 2],
            chat_id=-100999,
            user_id=888
        )

        log_string = query.get_log_string()
        expected = "[/test]: -100999 - 888"
        assert log_string == expected

    def test_query_with_empty_admin_ids(self):
        query = QueryBase(
            cmd="/command",
            admin_ids=[],
            chat_id=-100111,
            user_id=222
        )

        log_string = query.get_log_string()
        assert "/command" in log_string
        assert "-100111" in log_string
        assert "222" in log_string

    def test_get_log_string_inheritance(self):
        class QueryDerived(QueryBase):
            pass

        query = QueryDerived(
            cmd="/callback_test",
            admin_ids=[100],
            chat_id=-200,
            user_id=300
        )

        log_string = query.get_log_string()
        expected = '[/callback_test]: -200 - 300'
        assert log_string == expected


class TestQueryWithCallback:
    def test_callback_initialization(self):
        def mock_callback():
            return "called"

        query = QueryWithCallback(
            cmd="/join",
            admin_ids=[1],
            chat_id=-100,
            user_id=2,
            callback=mock_callback
        )

        assert query.cmd == "/join"
        assert query.callback == mock_callback
        assert callable(query.callback)

    def test_callback_inheritance(self):
        query = QueryWithCallback(
            cmd="/test",
            admin_ids=[],
            chat_id=-1,
            user_id=1,
            callback=lambda: None
        )

        assert isinstance(query, QueryBase)
        assert isinstance(query, QueryWithCallback)


class TestQueryWithTarget:
    def test_target_initialization(self):
        query = QueryWithTarget(
            cmd="/vote",
            admin_ids=[1, 2],
            chat_id=-100,
            user_id=3,
            callback=lambda: None,
            target_id=42
        )

        assert query.target_id == 42
        assert query.cmd == "/vote"

    def test_target_get_log_string(self):
        query = QueryWithTarget(
            cmd="/nominate",
            admin_ids=[10],
            chat_id=-500,
            user_id=20,
            callback=lambda: None,
            target_id=30
        )

        log_string = query.get_log_string()
        expected = "[/nominate]: -500 - 20 - 30"
        assert log_string == expected

    def test_target_inheritance_chain(self):
        query = QueryWithTarget(
            cmd="/target",
            admin_ids=[],
            chat_id=-1,
            user_id=2,
            callback=lambda: None,
            target_id=3
        )

        assert isinstance(query, QueryBase)
        assert isinstance(query, QueryWithCallback)
        assert isinstance(query, QueryWithTarget)


class TestResponseBase:
    def test_response_initialization(self):
        response = ResponseBase(
            chat_id=-100123,
            text="Hello, world!",
            parse_mode="HTML"
        )

        assert response.chat_id == -100123
        assert response.text == "Hello, world!"
        assert response.parse_mode == "HTML"

    def test_response_default_parse_mode(self):
        response = ResponseBase(
            chat_id=-100,
            text="Message without parse mode"
        )

        assert response.parse_mode is None

    def test_response_get_log_string(self):
        response = ResponseBase(
            chat_id=-777,
            text="First line\nSecond line\nThird line",
            parse_mode="Markdown"
        )

        log_string = response.get_log_string()
        assert "[Response]" in log_string
        assert "-777" in log_string
        assert "Markdown" in log_string
        assert "First line" in log_string
        assert "Second line" not in log_string

    def test_response_get_log_string_default_parse_mode(self):
        response = ResponseBase(
            chat_id=-1,
            text="Simple message"
        )

        log_string = response.get_log_string()
        assert "default" in log_string
        assert "Simple message" in log_string

    def test_response_with_long_text(self):
        long_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        response = ResponseBase(chat_id=-100, text=long_text)

        log_string = response.get_log_string()
        assert "Line 1" in log_string
        assert "Line 2" not in log_string


class TestResponseWithAlert:
    def test_alert_initialization(self):
        def mock_callback():
            return "alert"

        response = ResponseWithAlert(
            callback=mock_callback,
            valid=True,
            chat_id=-100,
            text="Alert message",
            parse_mode="HTML"
        )

        assert response.callback == mock_callback
        assert response.is_valid is True
        assert response.chat_id == -100
        assert response.text == "Alert message"

    def test_alert_inheritance(self):
        response = ResponseWithAlert(
            callback=lambda: None,
            valid=False,
            chat_id=-1,
            text="Test"
        )

        assert isinstance(response, ResponseBase)
        assert isinstance(response, ResponseWithAlert)

    def test_get_log_string_uses_parent(self):
        response = ResponseWithAlert(
            callback=lambda: None,
            valid=True,
            chat_id=-500,
            text="Alert text\nSecond line"
        )

        log_string = response.get_log_string()
        assert "[Response]" in log_string
        assert "-500" in log_string
        assert "Alert text" in log_string


class TestResponseWithOptions:
    def test_options_initialization(self):
        candidates = ["option1", "option2", "option3"]
        response = ResponseWithOptions(
            candidates=candidates,
            chat_id=-100,
            text="Choose an option:",
            parse_mode="Markdown"
        )

        assert response.candidates == candidates
        assert response.text == "Choose an option:"
        assert response.parse_mode == "Markdown"

    def test_options_empty_candidates(self):
        response = ResponseWithOptions(
            candidates=[],
            chat_id=-1,
            text="No options"
        )

        assert response.candidates == []

    def test_options_inheritance(self):
        response = ResponseWithOptions(
            candidates=[1, 2, 3],
            chat_id=-10,
            text="Test"
        )

        assert isinstance(response, ResponseBase)
        assert isinstance(response, ResponseWithOptions)


class TestStartGameQuery:
    def test_start_game_initialization(self):
        query = StartGameQuery(
            cmd="/start_game",
            admin_ids=[100, 200],
            chat_id=-100123,
            user_id=300,
            chat_type="group"
        )

        assert query.cmd == "/start_game"
        assert query.chat_type == "group"
        assert isinstance(query, QueryBase)

    def test_start_game_get_log_string(self):
        query = StartGameQuery(
            cmd="/start_game",
            admin_ids=[1],
            chat_id=-500,
            user_id=2,
            chat_type="supergroup"
        )

        log_string = query.get_log_string()

        assert "[/start_game]" in log_string
        assert "-500 - 2" in log_string
        assert "supergroup" not in log_string


class TestJoinQuery:
    def test_join_initialization(self):
        query = JoinQuery(
            cmd="/join_game",
            admin_ids=[1, 2],
            chat_id=-100,
            user_id=3,
            callback=lambda: None,
            username="player123"
        )

        assert query.username == "player123"
        assert query.cmd == "/join_game"

    def test_join_get_log_string(self):
        query = JoinQuery(
            cmd="/join",
            admin_ids=[10, 20, 30],
            chat_id=-777,
            user_id=888,
            callback=lambda: None,
            username="cool_player"
        )

        log_string = query.get_log_string()
        expected = "[/join]: -777 - 888 - cool_player - 3"
        assert log_string == expected

    def test_join_log_includes_admin_count(self):
        query1 = JoinQuery(
            cmd="/join", admin_ids=[1], chat_id=-1, user_id=1,
            callback=lambda: None, username="user1"
        )

        query2 = JoinQuery(
            cmd="/join", admin_ids=[1, 2, 3, 4], chat_id=-1, user_id=1,
            callback=lambda: None, username="user2"
        )

        log1 = query1.get_log_string()
        log2 = query2.get_log_string()

        assert " - 1" in log1
        assert " - 4" in log2


class TestNightActionQuery:
    def test_night_action_initialization(self):
        query = NightActionQuery(
            cmd="/night_action",
            admin_ids=[1],
            chat_id=-100,
            user_id=2,
            callback=lambda: None,
            action="kill",
            target="player3"
        )

        assert query.action == "kill"
        assert query.target == "player3"

    def test_night_action_get_log_string(self):
        query = NightActionQuery(
            cmd="/night",
            admin_ids=[10],
            chat_id=-500,
            user_id=20,
            callback=lambda: None,
            action="investigate",
            target="suspect"
        )

        log_string = query.get_log_string()
        expected = "[/night]: -500 - investigate"
        assert log_string == expected
        assert "target" not in log_string

    def test_night_action_different_actions(self):
        actions = ["kill", "heal", "check", "block", "protect"]

        for action in actions:
            query = NightActionQuery(
                cmd="/night", admin_ids=[1], chat_id=-1, user_id=1,
                callback=lambda: None, action=action, target="someone"
            )
            log_string = query.get_log_string()
            assert action in log_string


class TestMafiaChatQuery:
    def test_mafia_chat_initialization(self):
        query = MafiaChatQuery(
            cmd="/mafia_chat",
            admin_ids=[1, 2],
            chat_id=-100,
            user_id=3,
            text="Let's discuss our plan"
        )

        assert query.text == "Let's discuss our plan"

    def test_mafia_chat_get_log_string(self):
        query = MafiaChatQuery(
            cmd="/mafia",
            admin_ids=[10],
            chat_id=-777,
            user_id=888,
            text="First line of message\nSecond line\nThird line"
        )

        log_string = query.get_log_string()
        expected = "[/mafia]: -777 - First line of message"
        assert log_string == expected
        assert "Second line" not in log_string

    def test_mafia_chat_empty_text(self):
        query = MafiaChatQuery(
            cmd="/mafia",
            admin_ids=[1],
            chat_id=-1,
            user_id=1,
            text=""
        )

        log_string = query.get_log_string()
        assert "[/mafia]: -1 - " in log_string


class TestAliasQueries:
    def test_run_query_alias(self):
        query = RunQuery(
            cmd="/run",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)
        assert not isinstance(query, QueryWithCallback)

    def test_info_query_alias(self):
        query = InfoQuery(
            cmd="/status",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_speech_related_query_alias(self):
        query = SpeechRelatedQuery(
            cmd="/speech",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_pre_nominate_query_alias(self):
        query = PreNominateQuery(
            cmd="/pre_nominate",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_pre_vote_query_alias(self):
        query = PreVoteQuery(
            cmd="/pre_vote",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_pre_balance_query_alias(self):
        query = PreBalanceQuery(
            cmd="/pre_balance",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_start_night_query_alias(self):
        query = StartNightQuery(
            cmd="/start_night",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)

    def test_skip_night_query_alias(self):
        query = SkipNightQuery(
            cmd="/skip_night",
            admin_ids=[1],
            chat_id=-100,
            user_id=2
        )

        assert isinstance(query, QueryBase)


class TestInheritanceHierarchy:
    def test_query_hierarchy(self):
        # QueryBase ← QueryWithCallback ← QueryWithTarget
        with_callback = QueryWithCallback("/cmd", [], -1, 1, lambda: None)
        with_target = QueryWithTarget("/cmd", [], -1, 1, lambda: None, 2)

        assert isinstance(with_callback, QueryBase)
        assert isinstance(with_target, QueryWithCallback)
        assert isinstance(with_target, QueryBase)

    def test_response_hierarchy(self):
        with_alert = ResponseWithAlert(lambda: None, True, -1, "text")
        with_options = ResponseWithOptions([], -1, "text")

        assert isinstance(with_alert, ResponseBase)
        assert isinstance(with_options, ResponseBase)
        assert not isinstance(with_alert, ResponseWithOptions)


class TestEdgeCases:
    def test_negative_chat_id(self):
        query = QueryBase(
            cmd="/test",
            admin_ids=[1],
            chat_id=-100123456789,
            user_id=123
        )

        assert query.chat_id == -100123456789
        log = query.get_log_string()
        assert "-100123456789" in log

    def test_large_admin_ids_list(self):
        admin_ids = list(range(1000))
        query = JoinQuery(
            cmd="/join",
            admin_ids=admin_ids,
            chat_id=-1,
            user_id=1,
            callback=lambda: None,
            username="user"
        )

        log = query.get_log_string()
        assert " - 1000" in log

    def test_special_characters_in_text(self):
        special_text = "Special chars: !@#$%^&*()_+{}|:<>?~`"

        response = ResponseBase(
            chat_id=-1,
            text=special_text
        )

        log = response.get_log_string()
        assert special_text.split('\n')[0] in log

    def test_none_values(self):
        query = QueryWithTarget(
            cmd=None,
            admin_ids=None,
            chat_id=None,
            user_id=None,
            callback=None,
            target_id=None
        )

        assert query.cmd is None
        assert query.admin_ids is None

        log = query.get_log_string()
        assert "None" in log or "null" in log.lower()


class TestLogStringFormat:
    def test_all_queries_have_log_method(self):
        query_classes = [
            QueryBase, QueryWithCallback, QueryWithTarget,
            StartGameQuery, JoinQuery, RunQuery, InfoQuery,
            SpeechRelatedQuery, PreNominateQuery, NominateQuery,
            PreVoteQuery, VoteQuery, PreBalanceQuery, BalanceQuery,
            StartNightQuery, SkipNightQuery, NightActionQuery, MafiaChatQuery
        ]
        callback = lambda: None

        for query_class in query_classes:
            if query_class == StartGameQuery:
                obj = query_class("/test", [1], -1, 1, "private")
            elif query_class == QueryWithTarget:
                obj = query_class("/test", [1], -1, 1, callback, 2)
            elif query_class == NominateQuery:
                obj = query_class("/test", [1], -1, 1, callback, 2)
            elif query_class == VoteQuery:
                obj = query_class("/test", [1], -1, 1, callback, 2)
            elif query_class == BalanceQuery:
                obj = query_class("/test", [1], -1, 1, callback, 2)
            elif query_class == JoinQuery:
                obj = query_class("/test", [1], -1, 1, callback, "username")
            elif query_class == QueryWithCallback:
                obj = query_class("/test", [1], -1, 1, callback)
            elif query_class == NightActionQuery:
                obj = query_class("/test", [1], -1, 1, callback, "action", "target")
            elif query_class == MafiaChatQuery:
                obj = query_class("/test", [1], -1, 1, "message")
            else:
                obj = query_class("/test", [1], -1, 1)

            assert hasattr(obj, 'get_log_string')
            assert callable(obj.get_log_string)
            assert isinstance(obj.get_log_string(), str)

    def test_all_responses_have_log_method(self):
        response_classes = [
            ResponseBase, ResponseWithAlert, ResponseWithOptions
        ]

        for response_class in response_classes:
            if response_class == ResponseWithAlert:
                obj = response_class(lambda: None, True, -1, "text")
            elif response_class == ResponseWithOptions:
                obj = response_class([], -1, "text")
            else:
                obj = response_class(-1, "text")

            assert hasattr(obj, 'get_log_string')
            assert callable(obj.get_log_string)
            assert isinstance(obj.get_log_string(), str)
