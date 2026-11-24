"""
Test harness for the whisper rich-message code.

Only infrastructure is faked: the pyrogram app (decorators become no-ops), the
Mongo database (mongomock-motor) and the language decorator. The real
whisperdb, whisper_card, rich_api, callbacks and cleanup_task code runs.
"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)  # strings/ loads ./strings/langs relative to the repo root
sys.path.insert(0, ROOT)

for key, value in {
    "BOT_TOKEN": "123456:TESTTOKEN",
    "API_ID": "1",
    "API_HASH": "hash",
    "MONGO_DB_URI": "mongodb://localhost",
    "OWNER_ID": "1000",
    "LOGGER_ID": "-100",
}.items():
    os.environ.setdefault(key, value)


def _pkg(name: str, *path: str) -> types.ModuleType:
    """A package object that does NOT execute its real __init__.py."""
    module = types.ModuleType(name)
    module.__path__ = [os.path.join(ROOT, *path)]
    sys.modules[name] = module
    return module


class _FakeApp:
    def __getattr__(self, name):
        if name.startswith("on_"):
            return lambda *a, **k: (lambda fn: fn)
        raise AttributeError(name)

    async def get_users(self, *_):
        raise RuntimeError("not used")


root = _pkg("NinjaSecret", "NinjaSecret")
root.app = _FakeApp()
_pkg("NinjaSecret.utils", "NinjaSecret", "utils")
_pkg("NinjaSecret.plugins", "NinjaSecret", "plugins")
_pkg("NinjaSecret.plugins.whisper", "NinjaSecret", "plugins", "whisper")
_pkg("NinjaSecret.mongo", "NinjaSecret", "mongo")
_pkg("NinjaSecret.core", "NinjaSecret", "core")
_pkg("NinjaSecret.utils.decorators", "NinjaSecret", "utils", "decorators")

from mongomock_motor import AsyncMongoMockClient  # noqa: E402

_mongo = types.ModuleType("NinjaSecret.core.mongo")
_mongo.mongodb = AsyncMongoMockClient()["ninja_test"]
sys.modules["NinjaSecret.core.mongo"] = _mongo

_misc = types.ModuleType("NinjaSecret.misc")
_misc.SUDOERS = {2000}
sys.modules["NinjaSecret.misc"] = _misc

_lang = types.ModuleType("NinjaSecret.utils.decorators.language")


def languageCB(fn):
    from strings import get_string

    async def wrapper(client, callback_query):
        return await fn(client, callback_query, get_string("en"))

    return wrapper


_lang.languageCB = languageCB
sys.modules["NinjaSecret.utils.decorators.language"] = _lang
