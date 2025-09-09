from ScorpiTune.core.bot import Hotty
from ScorpiTune.core.dir import dirr
# from ScorpiTune.core.git import git
from ScorpiTune.core.userbot import Userbot
from ScorpiTune.misc import dbb, heroku

from .logging import LOGGER

dirr()
# git()  # Commented out to avoid Git authentication errors
dbb()
heroku()

app = Hotty()
userbot = Userbot()
