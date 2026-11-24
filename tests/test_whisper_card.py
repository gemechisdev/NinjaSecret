"""Card builder: layouts, label priority, escaping and edge cases."""
import re
from datetime import datetime

import pytest

from NinjaSecret.utils.whisper_card import (
    whisper_card, burned_card, deleted_card, expired_card, mentions_text,
    modifiers_from_settings, card_from_whisper, card_targets, is_everyone,
    burned_card_from_whisper, to_unix, LABELS, BUTTON,
)

ME = (6153949909, "☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖")
SONAN = (987654321, "SONAN")


def aside(card):
    return re.search(r"<aside>(.*?)</aside>", card["html"]).group(1)


def test_single_unread_matches_spec_exactly():
    html = whisper_card("test001", [ME], button_style="danger")["html"]
    assert html == (
        '<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌'
        '<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside>'
        '<tg-button-row align="center"><tg-button type="callback_data" style="danger" '
        'data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>'
    )


def test_single_read_adds_eye_to_label_only():
    unread = whisper_card("x", [ME])["html"]
    read = whisper_card("x", [ME], read=1)["html"]
    assert "👁" not in unread
    assert "<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite>" in read
    assert "Read:" not in read and "<br>" not in aside({"html": read})


def test_no_dangling_br_when_line2_is_empty():
    for mods in ({"vip"}, {"cute"}, {"delete"}, {"burn"}, set()):
        assert "<br>" not in whisper_card("x", [ME], modifiers=mods)["html"]


def test_multi_keeps_counter_and_no_eye_in_label():
    card = whisper_card("x", [ME, SONAN])
    assert "<br>👁Read: 0/2<cite>" in card["html"]
    card = whisper_card("x", [ME, SONAN], read=1)
    assert "👁Read: 1/2" in card["html"] and "𝚢𝚘𝚞! 👁" not in card["html"]
    assert "💌 " in aside(card) and " &amp; " in aside(card)


def test_everyone_layout():
    html = whisper_card("x", None, read=3)["html"]
    assert "💌 Everyone 💌<br>👁Read: 3<cite>" in html
    assert "/" not in aside({"html": html}).split("<br>")[1].split("<cite>")[0]


def test_counter_never_exceeds_total():
    assert "Read: 2/2" in whisper_card("x", [ME, SONAN], read=9)["html"]


def test_timer_single_has_expiry_only():
    card = whisper_card("x", [ME], modifiers={"timer"}, expires_at=1795473000)
    body = aside(card)
    assert '<br>⏰ <tg-time unix="1795473000" format="r">soon</tg-time><cite>⏰ 𝚃𝚒𝚖𝚎𝚍' in body
    assert "Read" not in body


def test_timer_multi_joins_with_dot():
    body = aside(whisper_card("x", [ME, SONAN], modifiers={"timer"}, expires_at=5))
    assert '</tg-time> · 👁Read: 0/2' in body


def test_datetime_expiry_is_converted_as_utc():
    dt = datetime(2026, 1, 1, 0, 0, 0)  # naive UTC, as stored in MongoDB
    assert to_unix(dt) == 1767225600
    assert 'unix="1767225600"' in whisper_card("x", [ME], modifiers={"timer"}, expires_at=dt)["html"]


def test_label_priority():
    pick = lambda m: re.search(r"<cite>(.*?)( 👁)?</cite>", whisper_card("x", [ME], modifiers=m)["html"]).group(1)
    assert pick({"burn", "delete", "reveal", "timer", "vip", "cute"}) == LABELS["burn"]
    assert pick({"delete", "reveal", "timer", "vip"}) == LABELS["delete"]
    assert pick({"reveal", "timer", "vip"}) == LABELS["reveal"]
    assert pick({"timer", "vip", "cute"}) == LABELS["timer"]
    assert pick({"vip", "cute"}) == LABELS["vip"]
    assert pick({"cute"}) == LABELS["cute"]
    assert pick(set()) == LABELS["classic"]


def test_reveal_single_after_read():
    body = aside(whisper_card("x", [ME], modifiers={"reveal"}, read=1, readers=[ME]))
    assert body.count("<br>") == 1
    assert "👀 <a href=\"tg://user?id=6153949909\">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> read it<cite>👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite>" in body


def test_reveal_multi_caps_names():
    many = [(i, f"u{i}") for i in range(1, 7)]
    body = aside(whisper_card("x", many, modifiers={"reveal"}, read=5, readers=many[:5]))
    reveal_part = body.split("<br>")[1].split(" read it")[0]
    assert reveal_part.endswith("+2") and "u4" not in reveal_part
    assert "👁Read: 5/6" in body


def test_duplicate_targets_collapse_to_single():
    card = whisper_card("x", [ME, ME], read=1)
    assert "Read:" not in card["html"] and "𝚢𝚘𝚞! 👁" in card["html"]


def test_names_are_escaped():
    html = whisper_card("x", [(1, 'A<b>&"x')])["html"]
    assert "<b>" not in html and "A&lt;b&gt;&amp;&quot;x" in html


def test_unknown_id_falls_back_to_link_or_plain_text():
    assert 't.me/bob_1' in whisper_card("x", [(None, "Bob", "bob_1")])["html"]
    plain = whisper_card("x", [(None, "Bob")])["html"]
    assert "<a " not in plain.split("</aside>")[0] and "Bob" in plain
    # unsafe usernames never end up inside an href
    assert "t.me" not in whisper_card("x", [(None, "Bob", 'x"><script')])["html"]


def test_empty_targets_rejected():
    with pytest.raises(ValueError):
        whisper_card("x", [])


def test_invalid_button_style_falls_back_to_danger():
    assert 'style="danger"' in whisper_card("x", [ME], button_style="evil\"")["html"]
    assert 'style="success"' in whisper_card("x", [ME], button_style="success")["html"]


def test_env_button_style(monkeypatch):
    monkeypatch.setenv("WHISPER_BUTTON_STYLE", "success")
    assert 'style="success"' in whisper_card("x", [ME])["html"]
    monkeypatch.setenv("WHISPER_BUTTON_STYLE", "nonsense")
    assert 'style="danger"' in whisper_card("x", [ME])["html"]


def test_terminal_cards_match_spec_and_have_no_button():
    assert burned_card(mentions_text([ME, SONAN]))["html"] == (
        '<aside>✅ <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; '
        '<a href="tg://user?id=987654321">SONAN</a> read it<cite>🔥 𝙱𝚞𝚛𝚗𝚎𝚍</cite></aside>'
    )
    assert deleted_card()["html"] == "<aside>💨 Poof! Nothing to see here</aside>"
    assert expired_card()["html"] == "<aside>⏰ Time's up. This secret expired.</aside>"
    for card in (burned_card("x"), deleted_card(), expired_card()):
        assert "tg-button" not in card["html"]


def test_modifier_mapping():
    assert modifiers_from_settings({"burn_after_reading": True, "reveal_on_read": True}) == {"burn"}
    assert modifiers_from_settings({"burn_after_reading": True}) == {"delete"}
    assert modifiers_from_settings({"reveal_on_read": True}) == {"reveal"}
    assert modifiers_from_settings({"style": "vip", "timer": 60}) == {"vip", "timer"}
    assert modifiers_from_settings(None) == set()


def test_card_from_whisper_roundtrip():
    w = {
        "whisper_id": "w1", "original_target_token": "@a,@b",
        "targets": [
            {"type": "user", "resolved_id": 1, "display_name": "A", "username": "aaaa"},
            {"type": "user", "resolved_id": None, "display_name": "@bbbb", "username": "bbbb"},
        ],
        "readers": [{"user_id": 1, "name": "A"}], "settings": {"reveal_on_read": True},
    }
    body = aside(card_from_whisper(w))
    assert "👁Read: 1/2" in body and "👀" in body
    assert 't.me/bbbb' in body  # unresolved target still tappable


def test_everyone_detection():
    assert is_everyone({"original_target_token": "@all"})
    assert is_everyone({"original_target_token": "@bob,@Everyone"})
    assert is_everyone({"targets": [{"type": "all"}]})
    assert not is_everyone({"original_target_token": "@bob"})
    assert card_targets({"original_target_token": "@all"}) is None


def test_legacy_whisper_without_targets_list():
    w = {"whisper_id": "w", "original_target_token": "@bob", "target_username": "bobby",
         "target_id": None, "read_at": datetime.utcnow()}
    html = card_from_whisper(w)["html"]
    assert "𝚢𝚘𝚞! 👁" in html  # legacy read_at counts as one read


def test_burned_card_for_everyone_names_readers():
    w = {"whisper_id": "w", "original_target_token": "@all",
         "readers": [{"user_id": 5, "name": "Zed"}]}
    assert "Zed" in burned_card_from_whisper(w)["html"]
