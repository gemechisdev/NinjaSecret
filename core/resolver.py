"""Target resolution logic for whispers."""
from typing import Optional, Tuple, Union
from pyrogram import Client

class TargetResolver:
    def __init__(self, bot_client: Client, user_client: Optional[Client] = None, db=None):
        self.bot = bot_client
        self.user_client = user_client
        self.db = db

    async def resolve(self, token: str) -> Tuple[Optional[int], Optional[str], str]:
        """
        Resolve a target token which can be:
        - @username
        - numeric user id
        Returns (target_id, normalized_username, display_label)
        """
        original = token
        username = None
        target_id: Optional[int] = None

        if token.startswith("@"):
            raw = token[1:]
            username = raw.lower()
        elif token.isdigit() and 5 <= len(token) <= 15:
            # Numeric user id
            try:
                target_id = int(token)
            except ValueError:
                pass

        # Try resolution with known mappings if username
        if username and not target_id and self.db:
            try:
                mapped = await self.db.resolve_username(username)
                if mapped:
                    target_id = mapped
            except Exception as e:
                print(f"Error resolving username {username} from DB: {e}")

        # Active network resolution if user_client exists
        if (username or target_id) and self.user_client:
            try:
                user_ref = username if username else target_id
                tg_user = await self.user_client.get_users(user_ref)
                target_id = tg_user.id
                if tg_user.username and self.db:
                    username = tg_user.username.lower()
                    try:
                        await self.db.link_username_to_user(username, tg_user.id)
                    except Exception as e:
                        print(f"Error linking username {username} to user {tg_user.id}: {e}")
                display = tg_user.first_name + (f" {tg_user.last_name}" if tg_user.last_name else "")
                return target_id, username, display
            except Exception:
                pass  # Silent fallback

        # Try bot client fallback
        if (username or target_id) and self.bot:
            try:
                user_ref = username if username else target_id
                tg_user = await self.bot.get_users(user_ref)
                target_id = tg_user.id
                if tg_user.username and self.db:
                    username = tg_user.username.lower()
                    try:
                        await self.db.link_username_to_user(username, tg_user.id)
                    except Exception as e:
                        print(f"Error linking username {username} to user {tg_user.id}: {e}")
                display = tg_user.first_name + (f" {tg_user.last_name}" if tg_user.last_name else "")
                return target_id, username, display
            except Exception:
                pass

        # Fallback displays
        if username:
            return target_id, username, f"@{username}"
        if target_id:
            return target_id, None, f"User {target_id}"
        return None, None, original
