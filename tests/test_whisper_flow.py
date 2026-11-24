"""
End-to-end whisper flows: real handler + real whisperdb on mongomock.
Only the Telegram edit call is recorded instead of sent.
"""
import asyncio
import calendar
import re
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import NinjaSecret.plugins.whisper.callbacks as cb
import NinjaSecret.plugins.whisper.cleanup_task as ct
import NinjaSecret.mongo.whisperdb as db
from NinjaSecret.core.mongo import mongodb
from NinjaSecret.utils.rich_api import RichApiError, MessageNotModified
from NinjaSecret.utils.whisper_utils import create_whisper_inline_result

SENDER, ALICE, BOB, STRANGER, OWNER, SUDO = 10, 11, 12, 13, 1000, 2000


class FakeCQ:
    def __init__(self, whisper_id, uid, username=None, first="User", inline_id="INL1", fail_answer=False):
        self.matches = [re.match(r"whisper_view_(.+)", f"whisper_view_{whisper_id}")]
        self.from_user = SimpleNamespace(id=uid, username=username, first_name=first, last_name=None)
        self.inline_message_id = inline_id
        self.message = None
        self.answers = []
        self.fail_answer = fail_answer

    async def answer(self, text=None, show_alert=False, **kw):
        if self.fail_answer:
            raise RuntimeError("QUERY_ID_INVALID")
        self.answers.append(text)


@pytest.fixture(autouse=True)
async def clean_db():
    for name in await mongodb.list_collection_names():
        await mongodb[name].drop()
    yield


@pytest.fixture
def edits(monkeypatch):
    log = []

    async def fake_edit(card, **target):
        log.append((card["html"], target))

    monkeypatch.setattr(cb, "edit_rich_message", fake_edit)
    return log


def body(html):
    m = re.search(r"<aside>(.*?)</aside>", html)
    return m.group(1) if m else html


async def make_whisper(wid="w1", targets=("alice",), modifiers=None, content="the secret", inline="INL1", **extra):
    all_targets, token = [], []
    for t in targets:
        if t == "@all":
            all_targets.append((None, None, "@all", "Everyone"))
        else:
            uid = {"alice": ALICE, "bob": BOB}[t]
            all_targets.append((uid, t, f"@{t}", t.title()))
        token.append("@all" if t == "@all" else f"@{t}")
    data = {
        "whisper_id": wid, "content": content, "sender_id": SENDER,
        "target_id": all_targets[0][0], "target_username": all_targets[0][1],
        "original_target_token": ",".join(token), "all_targets": all_targets,
        "target_mentions": "x", "inline_message_id": inline, **extra,
    }
    if modifiers:
        data["modifiers"] = modifiers
    await db.store_whisper(data)
    return wid


async def tap(wid, uid, username=None, first="User", **kw):
    cq = FakeCQ(wid, uid, username, first, **kw)
    await cb.handle_whisper_view(None, cq)
    return cq


# ------------------------------------------------------------------ single

async def test_single_receiver_eye_appears_only_after_target_reads(edits):
    wid = await make_whisper()
    cq = await tap(wid, ALICE, "alice", "Alice")
    assert cq.answers == ["the secret"]
    assert len(edits) == 1
    html, target = edits[0]
    assert target == {"inline_message_id": "INL1"}
    assert "<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite>" in html and "Read:" not in html
    assert "tg-button" in html  # button stays so the secret can be opened again


async def test_second_tap_by_same_target_does_not_edit(edits):
    wid = await make_whisper()
    await tap(wid, ALICE, "alice")
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers == ["the secret"]  # still opens
    assert len(edits) == 1  # no duplicate edit -> no "message is not modified"


async def test_sender_and_stranger_never_flip_the_eye(edits):
    wid = await make_whisper()
    assert (await tap(wid, SENDER)).answers == ["the secret"]
    stranger = await tap(wid, STRANGER)
    assert stranger.answers and stranger.answers[0] != "the secret"
    owner, sudo = await tap(wid, OWNER), await tap(wid, SUDO)
    assert owner.answers == sudo.answers == ["the secret"]
    assert edits == []
    assert (await db.get_whisper(wid))["readers"] == []


async def test_self_whisper_counts_as_read(edits):
    wid = await make_whisper(targets=("alice",))
    await db.whisperdb.update_one({"whisper_id": wid}, {"$set": {"sender_id": ALICE}})
    await tap(wid, ALICE, "alice")
    assert len(edits) == 1 and "👁</cite>" in edits[0][0]


async def test_edit_failure_never_blocks_the_secret(monkeypatch):
    async def boom(card, **t):
        raise RichApiError(500, "Internal Server Error")

    monkeypatch.setattr(cb, "edit_rich_message", boom)
    wid = await make_whisper()
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers == ["the secret"]
    assert len((await db.get_whisper(wid))["readers"]) == 1


async def test_message_not_modified_is_swallowed(monkeypatch):
    async def same(card, **t):
        raise MessageNotModified(400, "message is not modified")

    monkeypatch.setattr(cb, "edit_rich_message", same)
    wid = await make_whisper()
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers == ["the secret"]


async def test_failed_popup_does_not_mark_read(edits):
    wid = await make_whisper()
    cq = FakeCQ(wid, ALICE, "alice", fail_answer=True)
    with pytest.raises(RuntimeError):  # error popup also fails here; nothing is recorded
        await cb.handle_whisper_view(None, cq)
    assert (await db.get_whisper(wid))["readers"] == [] and edits == []


async def test_inline_message_id_is_attached_from_callback_when_missing(edits):
    wid = await make_whisper(inline=None)
    await tap(wid, SENDER, inline_id="LATE9")
    assert (await db.get_whisper(wid))["inline_message_id"] == "LATE9"


async def test_unresolved_username_target_is_linked_on_first_read(edits):
    await db.store_whisper({
        "whisper_id": "w9", "content": "s", "sender_id": SENDER, "target_id": None,
        "target_username": "carol", "original_target_token": "@carol",
        "all_targets": [(None, "carol", "@carol", "@carol")], "target_mentions": "x",
        "inline_message_id": "INL1",
    })
    await tap("w9", 77, "Carol", "Carol")
    doc = await db.get_whisper("w9")
    assert doc["targets"][0]["resolved_id"] == 77 and doc["target_id"] == 77
    assert 'tg://user?id=77' in edits[0][0]


async def test_legacy_whisper_is_not_edited(edits):
    wid = await make_whisper()
    await db.whisperdb.update_one({"whisper_id": wid}, {"$unset": {"rich": ""}})
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers == ["the secret"] and edits == []


# ------------------------------------------------------------------ multi / modifiers

async def test_two_targets_counter_progress(edits):
    wid = await make_whisper(targets=("alice", "bob"))
    await tap(wid, ALICE, "alice", "Alice")
    assert "👁Read: 1/2" in edits[-1][0]
    await tap(wid, BOB, "bob", "Bob")
    assert "👁Read: 2/2" in edits[-1][0] and "𝚢𝚘𝚞! 👁" not in edits[-1][0]
    assert len(edits) == 2


async def test_burn_waits_for_all_targets_then_burns_once(edits):
    wid = await make_whisper(targets=("alice", "bob"), modifiers={"burn_after_reading": True, "reveal_on_read": True})
    await tap(wid, ALICE, "alice", "Alice")
    assert "Read: 1/2" in edits[-1][0] and (await db.get_whisper(wid))["status"] != "burned"
    await tap(wid, BOB, "bob", "Bob")
    html = edits[-1][0]
    assert "✅" in html and "read it" in html and "🔥 𝙱𝚞𝚛𝚗𝚎𝚍" in html and "tg-button" not in html
    assert (await db.get_whisper(wid))["status"] == "burned"
    late = await tap(wid, ALICE, "alice")
    assert "🔥" in late.answers[0] and len(edits) == 2


async def test_simultaneous_final_readers_burn_exactly_once(edits):
    wid = await make_whisper(targets=("alice", "bob"), modifiers={"burn_after_reading": True, "reveal_on_read": True})
    await asyncio.gather(tap(wid, ALICE, "alice", "Alice"), tap(wid, BOB, "bob", "Bob"))
    burned = [h for h, _ in edits if "𝙱𝚞𝚛𝚗𝚎𝚍" in h]
    assert len(burned) == 1
    assert (await db.get_whisper(wid))["status"] == "burned"
    assert len((await db.get_whisper(wid))["readers"]) == 2


async def test_delete_single_shows_poof_and_no_button(edits):
    wid = await make_whisper(modifiers={"burn_after_reading": True})
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers == ["the secret"]  # the reader still sees the secret once
    assert edits[-1][0] == "<aside>💨 Poof! Nothing to see here</aside>"
    assert (await tap(wid, ALICE, "alice")).answers[0].startswith("🔥")


async def test_reveal_single_shows_reader_and_eye(edits):
    wid = await make_whisper(modifiers={"reveal_on_read": True})
    await tap(wid, ALICE, "alice", "Alice")
    b = body(edits[-1][0])
    assert "👀 <a href=\"tg://user?id=11\">Alice</a> read it" in b and "𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite>" in b
    assert "tg-button" in edits[-1][0]


async def test_reveal_name_is_escaped(edits):
    wid = await make_whisper(modifiers={"reveal_on_read": True})
    await tap(wid, ALICE, "alice", '<b>Al&ice</b>')
    assert "<b>Al" not in edits[-1][0] and "&lt;b&gt;Al&amp;ice&lt;/b&gt;" in edits[-1][0]


# ------------------------------------------------------------------ @all

async def test_everyone_counter_and_sender_not_counted(edits):
    wid = await make_whisper(targets=("@all",))
    await tap(wid, SENDER)
    assert edits == []
    await tap(wid, STRANGER, "x", "Stranger")
    assert "💌 Everyone 💌<br>👁Read: 1<cite>" in edits[-1][0]
    await tap(wid, ALICE, "alice", "Alice")
    assert "👁Read: 2" in edits[-1][0]


async def test_everyone_burn_happens_on_first_read(edits):
    wid = await make_whisper(targets=("@all",), modifiers={"burn_after_reading": True, "reveal_on_read": True})
    await tap(wid, STRANGER, "x", "Stranger")
    assert "𝙱𝚞𝚛𝚗𝚎𝚍" in edits[-1][0] and "Stranger" in edits[-1][0]


# ------------------------------------------------------------------ timer

async def test_timer_card_and_database_share_one_expiry():
    expires = datetime.utcnow() + timedelta(seconds=3600)
    res = create_whisper_inline_result(
        "w5", "s", [{"type": "user", "resolved_id": ALICE, "display_name": "Alice", "username": "alice"}],
        {"timer": 3600}, "en", expires)
    html = res["input_message_content"]["rich_message"]["html"]
    await db.store_whisper({
        "whisper_id": "w5", "content": "s", "sender_id": SENDER, "target_id": ALICE, "target_username": "alice",
        "original_target_token": "@alice", "all_targets": [(ALICE, "alice", "@alice", "Alice")],
        "modifiers": {"timer": 3600}, "expires_at": expires, "inline_message_id": "INL1"})
    stored = (await db.get_whisper("w5"))["settings"]["expires_at"]
    unix = int(re.search(r'unix="(\d+)"', html).group(1))
    # MongoDB keeps milliseconds; the card shows whole seconds. They must agree to the second.
    assert abs((stored - expires).total_seconds()) < 0.001
    assert unix == int(calendar.timegm(stored.utctimetuple()))
    assert "𝚃𝚒𝚖𝚎𝚍" in html and "Read" not in html


async def test_expired_whisper_popup_and_no_edit(edits):
    wid = await make_whisper(modifiers={"timer": 60}, expires_at=datetime.utcnow() - timedelta(seconds=5))
    cq = await tap(wid, ALICE, "alice")
    assert cq.answers[0].startswith("⏰") and edits == []


async def _run_one_expiry_pass(monkeypatch, edit):
    import NinjaSecret.utils.rich_api as api
    monkeypatch.setattr(api, "edit_rich_message", edit)

    async def stop(_seconds):
        if _seconds >= ct.EXPIRY_CHECK_INTERVAL_SECONDS:
            raise asyncio.CancelledError
    monkeypatch.setattr(ct.asyncio, "sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await ct.timer_countdown_update_task()


async def test_expiry_watcher_replaces_card_once(monkeypatch):
    past = datetime.utcnow() - timedelta(seconds=30)
    await make_whisper("e1", modifiers={"timer": 60}, expires_at=past)
    await make_whisper("e2", modifiers={"timer": 60}, expires_at=datetime.utcnow() + timedelta(hours=1))
    await make_whisper("e3", modifiers={"timer": 60}, expires_at=past, inline=None)  # nothing to edit
    await make_whisper("e4", expires_at=past)  # no timer
    calls = []

    async def edit(card, **t):
        calls.append((card["html"], t))

    await _run_one_expiry_pass(monkeypatch, edit)
    assert calls == [("<aside>⏰ Time's up. This secret expired.</aside>", {"inline_message_id": "INL1"})]
    await _run_one_expiry_pass(monkeypatch, edit)  # idempotent
    assert len(calls) == 1


async def test_expiry_watcher_retries_transient_but_not_permanent_failures(monkeypatch):
    past = datetime.utcnow() - timedelta(seconds=30)
    await make_whisper("t1", modifiers={"timer": 60}, expires_at=past, inline="A")
    await make_whisper("t2", modifiers={"timer": 60}, expires_at=past, inline="B")

    async def edit(card, inline_message_id=None, **kw):
        raise RichApiError(429 if inline_message_id == "A" else 400, "x")

    await _run_one_expiry_pass(monkeypatch, edit)
    assert (await db.get_whisper("t1")).get("expiry_edited") is False  # will retry
    assert (await db.get_whisper("t2")).get("expiry_edited") is True  # gave up


async def test_expiry_watcher_skips_burned_and_legacy(monkeypatch):
    past = datetime.utcnow() - timedelta(seconds=30)
    await make_whisper("b1", modifiers={"timer": 60}, expires_at=past)
    await db.claim_burn("b1")
    await make_whisper("l1", modifiers={"timer": 60}, expires_at=past)
    await db.whisperdb.update_one({"whisper_id": "l1"}, {"$unset": {"rich": ""}})
    calls = []

    async def edit(card, **t):
        calls.append(t)

    await _run_one_expiry_pass(monkeypatch, edit)
    assert calls == []


# ------------------------------------------------------------------ database helpers

async def test_add_whisper_reader_is_atomic_and_idempotent():
    wid = await make_whisper(targets=("alice", "bob"))
    results = await asyncio.gather(*[db.add_whisper_reader(wid, ALICE, "Alice") for _ in range(5)])
    assert sum(1 for is_new, _ in results if is_new) == 1
    assert len((await db.get_whisper(wid))["readers"]) == 1


async def test_mark_whisper_read_never_unburns():
    wid = await make_whisper()
    await db.claim_burn(wid)
    await db.mark_whisper_read(wid, ALICE)
    assert (await db.get_whisper(wid))["status"] == "burned"


async def test_claim_burn_only_once():
    wid = await make_whisper()
    assert await db.claim_burn(wid) is True
    assert await db.claim_burn(wid) is False


async def test_cleanup_expired_handles_missing_inline_id():
    await make_whisper("c1", modifiers={"timer": 60}, expires_at=datetime.utcnow() - timedelta(seconds=5), inline=None)
    assert await db.cleanup_expired_whispers() == 1
    assert (await db.get_whisper("c1"))["status"] == "expired"
