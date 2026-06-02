from datetime import datetime, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock

from vkbottle.api import API

from config.settings import USERNAME_TTL_SECONDS

from utils.user_cache import UserNameCache

from tests.conftest import capture_logger_output


class TestUserNameCache:
    @pytest.fixture
    def api_mock(self):
        api = MagicMock(spec=API)
        api.users = MagicMock()
        api.users.get = AsyncMock()
        return api

    @pytest.fixture
    def cache(self):
        return UserNameCache(ttl_seconds=60)

    @pytest.mark.asyncio
    async def test_get_user_name_from_cache(self, cache, api_mock):
        user_id = 12345
        expected_name = "@test_user"

        cache.cache[user_id] = (expected_name, datetime.now())

        result = await cache.get_user_name(api_mock, user_id)

        assert result == expected_name
        api_mock.users.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_name_cache_expired(self, cache, api_mock):
        user_id = 12345
        old_name = "@old_user"
        new_name = "@new_user"

        expired_time = datetime.now() - timedelta(seconds=120)
        cache.cache[user_id] = (old_name, expired_time)

        mock_user = MagicMock()
        mock_user.screen_name = "new_user"
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        api_mock.users.get.return_value = [mock_user]

        result = await cache.get_user_name(api_mock, user_id)

        assert result == new_name
        api_mock.users.get.assert_called_once_with(user_ids=[user_id])

    @pytest.mark.asyncio
    async def test_get_user_name_with_screen_name(self, cache, api_mock):
        user_id = 12345

        mock_user = MagicMock()
        mock_user.screen_name = "durov"
        mock_user.first_name = "Pavel"
        mock_user.last_name = "Durov"
        api_mock.users.get.return_value = [mock_user]

        result = await cache.get_user_name(api_mock, user_id)

        assert result == "@durov"
        assert cache.cache[user_id][0] == "@durov"

    @pytest.mark.asyncio
    async def test_get_user_name_without_screen_name(self, cache, api_mock):
        user_id = 12345

        mock_user = MagicMock()
        mock_user.screen_name = None
        mock_user.first_name = "Pavel"
        mock_user.last_name = "Durov"
        api_mock.users.get.return_value = [mock_user]

        result = await cache.get_user_name(api_mock, user_id)

        assert result == "Pavel Durov"
        assert cache.cache[user_id][0] == "Pavel Durov"

    @pytest.mark.asyncio
    async def test_get_user_name_empty_response(self, cache, api_mock):
        user_id = 12345

        api_mock.users.get.return_value = []

        result = await cache.get_user_name(api_mock, user_id)

        assert result == str(user_id)
        assert cache.cache[user_id][0] == str(user_id)

    @pytest.mark.asyncio
    async def test_get_user_name_api_error(self, cache, api_mock):
        user_id = 12345

        api_mock.users.get.side_effect = Exception("Network error")

        with capture_logger_output() as log_content:
            result = await cache.get_user_name(api_mock, user_id)

            assert result == str(user_id)
            assert (
                "Failed to get user name for 12345: Network error"
                in log_content.getvalue()
            )

    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        custom_cache = UserNameCache(ttl_seconds=30)
        assert custom_cache.ttl == timedelta(seconds=30)

    @pytest.mark.asyncio
    async def test_cache_multiple_users(self, cache, api_mock):
        user_ids = [1, 2, 3]
        expected_names = ["@user1", "@user2", "@user3"]

        async def mock_get(user_ids=None, **kwargs):
            return [
                MagicMock(screen_name=f"user{uid}", first_name="", last_name="")
                for uid in user_ids
            ]

        api_mock.users.get.side_effect = mock_get

        for uid, name in zip(user_ids, expected_names):
            result = await cache.get_user_name(api_mock, uid)
            assert result == f"@{name[1:]}"

        api_mock.users.get.reset_mock()
        for uid in user_ids:
            await cache.get_user_name(api_mock, uid)

        api_mock.users.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_update_on_expiry(self, cache, api_mock):
        user_id = 12345
        initial_name = "@user1"
        updated_name = "@user2"

        cache.cache[user_id] = (initial_name, datetime.now() - timedelta(seconds=70))

        mock_user = MagicMock()
        mock_user.screen_name = "user2"
        api_mock.users.get.return_value = [mock_user]

        result = await cache.get_user_name(api_mock, user_id)

        assert result == updated_name
        assert cache.cache[user_id][0] == updated_name

    @pytest.mark.asyncio
    async def test_timestamp_update(self, cache, api_mock):
        user_id = 12345

        mock_user = MagicMock()
        mock_user.screen_name = "test"
        api_mock.users.get.return_value = [mock_user]

        before = datetime.now()
        await cache.get_user_name(api_mock, user_id)
        after = datetime.now()

        cached_name, cached_time = cache.cache[user_id]

        assert cached_name == "@test"
        assert before <= cached_time <= after

    @pytest.mark.asyncio
    async def test_empty_screen_name_string(self, cache, api_mock):
        user_id = 12345

        mock_user = MagicMock()
        mock_user.screen_name = ""
        mock_user.first_name = "John"
        mock_user.last_name = "Smith"
        api_mock.users.get.return_value = [mock_user]

        result = await cache.get_user_name(api_mock, user_id)

        assert result == "John Smith"

    @pytest.mark.asyncio
    async def test_concurrent_access_simulation(self, cache, api_mock):
        user_id = 12345

        mock_user = MagicMock()
        mock_user.screen_name = "concurrent"
        api_mock.users.get.return_value = [mock_user]

        import asyncio

        tasks = [cache.get_user_name(api_mock, user_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(r == "@concurrent" for r in results)
        assert api_mock.users.get.call_count >= 1

    @pytest.mark.asyncio
    async def test_user_id_as_fallback(self, cache, api_mock):
        user_id = 99999

        api_mock.users.get.return_value = []

        result = await cache.get_user_name(api_mock, user_id)

        assert result == "99999"
        assert cache.cache[user_id][0] == "99999"

    def test_initialization_with_default_ttl(self):
        cache = UserNameCache()
        assert cache.ttl == timedelta(seconds=USERNAME_TTL_SECONDS)

    def test_initialization_with_custom_ttl(self):
        cache = UserNameCache(ttl_seconds=120)
        assert cache.ttl == timedelta(seconds=120)
