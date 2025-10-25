from NinjaSecret.core.bot import Hotty
from NinjaSecret.core.dir import dirr
# from NinjaSecret.core.git import git
from NinjaSecret.core.userbot import Userbot
from NinjaSecret.misc import dbb, heroku

from .logging import LOGGER

dirr()
# git()  # Commented out to avoid Git authentication errors
dbb()
heroku()

app = Hotty()
userbot = Userbot()  # Stub userbot for compatibility
