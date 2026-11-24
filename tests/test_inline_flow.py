"""Inline query -> raw rich result -> chosen result -> stored whisper."""
import json
import re
from types import SimpleNamespace

import pytest

import NinjaSecret.plugins.whisper.inline_handler as ih
import NinjaSecret.mongo.whisperdb as db
from NinjaSecret.core.mongo import mongodb


class FakeQuery:
    def __init__(self, text, uid=10):
        self.id = "Q1"
        self.query = text
        self.from_user = SimpleNamespace(id=uid)
        self.pyrogram_answers = []

    async def answer(self, results, **kw):
        self.pyrogram_answers.append(results)


@pytest.fixture(autouse=True)
async def clean():
    ih.pending_whispers.clear()
    for name in await mongodb.list_collection_names():
        await mongodb[name].drop()
    yield


@pytest.fixture
def raw(monkeypatch):
    calls = []

    async def fake(query_id, results, **kw):
        calls.append((query_id, results, kw))

    monkeypatch.setattr(ih, "answer_inline_query", fake)

    async def resolve(token, client, *a, **k):
        return 11, "alice", "Alice"

    monkeypatch.setattr(ih, "resolve_target", resolve)
    return calls


def card(call):
    return call[1][0]["input_message_content"]["rich_message"]["html"]


async def test_single_target_result_is_raw_rich_and_unread(raw):
    q = FakeQuery("hello there @alice")
    await ih.handle_inline_query(None, q)
    (qid, results, kw), = raw
    assert qid == "Q1" and kw == {"cache_time": 1, "is_personal": True} and not q.pyrogram_answers
    json.dumps(results)  # must be plain JSON, no pyrogram objects
    res = results[0]
    assert res["type"] == "article" and "reply_markup" not in res["input_message_content"]
    html = card(raw[0])
    assert "𝚢𝚘𝚞! 👁" not in html and "Read:" not in html and "<br>" not in html
    assert 'data="whisper_view_%s"' % res["id"] in html


async def test_at_all_no_longer_crashes(raw):
    q = FakeQuery("pizza time @all")
    await ih.handle_inline_query(None, q)
    assert not q.pyrogram_answers, "an error article means the handler crashed"
    assert "💌 Everyone 💌<br>👁Read: 0<cite>" in card(raw[0])


async def test_two_targets_show_counter(raw, monkeypatch):
    people = {"@alice": (11, "alice", "Alice"), "@bob": (12, "bob", "Bob")}

    async def resolve(token, client, *a, **k):
        return people[token]

    monkeypatch.setattr(ih, "resolve_target", resolve)
    await ih.handle_inline_query(None, FakeQuery("news @alice,@bob"))
    assert "👁Read: 0/2" in card(raw[0])


async def test_timed_whisper_card_and_database_use_the_same_expiry(raw):
    await ih.handle_inline_query(None, FakeQuery("meet at 5 @alice !t:3600"))
    res = raw[0][1][0]
    wid = res["id"]
    cached = ih.pending_whispers[wid]["expires_at"]
    unix = int(re.search(r'unix="(\d+)"', card(raw[0])).group(1))
    import calendar
    assert unix == calendar.timegm(cached.utctimetuple())

    await ih.handle_chosen_inline_result(None, SimpleNamespace(
        result_id=wid, from_user=SimpleNamespace(id=10, username="s"), inline_message_id="INL7", query="x"))
    stored = await db.get_whisper(wid)
    assert abs((stored["settings"]["expires_at"] - cached).total_seconds()) < 0.001
    assert stored["rich"] is True and stored["readers"] == [] and stored["inline_message_id"] == "INL7"


async def test_chosen_result_without_inline_id_still_stores(raw):
    await ih.handle_inline_query(None, FakeQuery("hi @alice"))
    wid = raw[0][1][0]["id"]
    await ih.handle_chosen_inline_result(None, SimpleNamespace(
        result_id=wid, from_user=SimpleNamespace(id=10, username="s"), inline_message_id=None, query="x"))
    assert (await db.get_whisper(wid)) is not None


async def test_recent_targets_branch_returns_raw_results(raw, monkeypatch):
    async def recents(uid):
        return [{"user_id": 11, "username": "alice", "first_name": "Alice", "original_token": "@alice"}]

    monkeypatch.setattr(ih, "get_recent_targets", recents)
    q = FakeQuery("just a message")
    await ih.handle_inline_query(None, q)
    assert raw and not q.pyrogram_answers
    json.dumps(raw[0][1])
    assert "Alice" in raw[0][1][0]["title"]
    assert raw[0][1][0]["id"] in ih.pending_whispers


async def test_help_and_error_articles_still_use_pyrogram(raw):
    q = FakeQuery("")
    await ih.handle_inline_query(None, q)
    assert q.pyrogram_answers and not raw


async def test_rich_api_failure_falls_back_to_error_article(monkeypatch):
    from NinjaSecret.utils.rich_api import RichApiError

    async def fail(*a, **k):
        raise RichApiError(400, "Bad Request: rich_message is invalid")

    async def resolve(token, client, *a, **k):
        return 11, "alice", "Alice"

    monkeypatch.setattr(ih, "answer_inline_query", fail)
    monkeypatch.setattr(ih, "resolve_target", resolve)
    q = FakeQuery("hi @alice")
    await ih.handle_inline_query(None, q)
    assert q.pyrogram_answers  # user gets an error result instead of silence
