from pyrogram import filters
from pyrogram.types import Message

from NinjaSecret import app
from NinjaSecret.misc import SUDOERS
from NinjaSecret.utils.database import add_banned_user, remove_banned_user
from NinjaSecret.utils.decorators.language import language
from NinjaSecret.utils.extraction import extract_user
from config import BANNED_USERS
import contextlib


@app.on_message(filters.command(["block"]) & SUDOERS)
@language
async def useradd(client, message: Message, _):
	# Silently process: no public replies
	try:
		user = await extract_user(message)
	except Exception:
		# If cannot parse a user, just delete the command silently
		with contextlib.suppress(Exception):
			await message.delete()
		return
	if user.id in BANNED_USERS:
		with contextlib.suppress(Exception):
			await message.delete()
		return
	await add_banned_user(user.id)
	BANNED_USERS.add(user.id)
	with contextlib.suppress(Exception):
		await message.delete()


@app.on_message(filters.command(["unblock"]) & SUDOERS)
@language
async def userdel(client, message: Message, _):
	# Silently process: no public replies
	try:
		user = await extract_user(message)
	except Exception:
		with contextlib.suppress(Exception):
			await message.delete()
		return
	if user.id not in BANNED_USERS:
		with contextlib.suppress(Exception):
			await message.delete()
		return
	await remove_banned_user(user.id)
	BANNED_USERS.remove(user.id)
	with contextlib.suppress(Exception):
		await message.delete()


@app.on_message(filters.command(["blocked", "blockedusers", "blusers"]) & SUDOERS)
@language
async def sudoers_list(client, message: Message, _):
	# Keep existing behavior to list, but only for sudo
	if not BANNED_USERS:
		return await message.reply_text(_["block_5"])
	mystic = await message.reply_text(_["block_6"])
	msg = _["block_7"]
	count = 0
	for users in BANNED_USERS:
		try:
			user = await app.get_users(users)
			user = user.first_name if not user.mention else user.mention
			count += 1
		except:
			continue
		msg += f"{count}➤ {user}\n"
	if count == 0:
		return await mystic.edit_text(_["block_5"])
	else:
		return await mystic.edit_text(msg)
