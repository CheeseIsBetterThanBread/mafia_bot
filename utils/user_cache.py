from datetime import datetime, timedelta
from typing import Dict

from vkbottle.api import API

from config.settings import CACHE_TTL_SECONDS

from utils.logger import LOGGER


class UserNameCache:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.cache: Dict[int, tuple[str, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    async def get_user_name(self, api: API, user_id: int) -> str:
        if user_id in self.cache:
            name, timestamp = self.cache[user_id]
            if datetime.now() - timestamp < self.ttl:
                return name

        try:
            users = await api.users.get(user_ids=[user_id])
            if users:
                user = users[0]
                if hasattr(user, "screen_name") and user.screen_name:
                    name = f"@{user.screen_name}"
                else:
                    name = f"{user.first_name} {user.last_name}"
            else:
                name = str(user_id)

            self.cache[user_id] = (name, datetime.now())
            return name

        except Exception as e:
            LOGGER.error(f"Failed to get user name for {user_id}: {e}")
            return str(user_id)
