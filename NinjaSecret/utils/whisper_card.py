"""
Ninja Secret🥷 Whisper Cards (Telegram Rich Messages)

Pure functions that build the `rich_message` objects for whisper delivery,
read states and terminal states. No Telegram or database access happens here.

Layouts
  * single receiver : no counter. `👁` is appended to the label only after read.
  * several / @all  : `👁Read: N/M` (or `👁Read: N`) on line 2.

See docs/WHISPER_DISPLAY_TEXTS.md for the full spec.
"""

import os
import re
from calendar import timegm
from datetime import datetime
from html import escape
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

LABELS = {
    "classic": "🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "vip":     "👑 𝚅𝙸𝙿 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "cute":    "💕 𝙻𝚘𝚟𝚎 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "reveal":  "👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "delete":  "💨 𝚅𝚊𝚗𝚒𝚜𝚑𝚒𝚗𝚐 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "burn":    "🔥 𝙱𝚞𝚛𝚗 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
    "timer":   "⏰ 𝚃𝚒𝚖𝚎𝚍 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!",
}
PRIORITY = ["burn", "delete", "reveal", "timer", "vip", "cute", "classic"]
BUTTON = "💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐"
EYE = "👁"
MAX_REVEAL_NAMES = 10

BURNED_LABEL = "🔥 𝙱𝚞𝚛𝚗𝚎𝚍"
DELETED_TEXT = "💨 Poof! Nothing to see here"
EXPIRED_TEXT = "⏰ Time's up. This secret expired."

_ALLOWED_STYLES = ("danger", "success")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")


def default_button_style() -> str:
    """`danger` (default) or `success`, via the WHISPER_BUTTON_STYLE env var."""
    style = (os.getenv("WHISPER_BUTTON_STYLE") or "danger").strip().lower()
    return style if style in _ALLOWED_STYLES else "danger"


# A target is (user_id, name) or (user_id, name, username).
Target = Tuple[Any, ...]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def pick_style(modifiers: Iterable[str]) -> str:
    mods = set(modifiers)
    return next((s for s in PRIORITY if s in mods), "classic")


def _mention(uid: Any, name: Optional[str], username: Optional[str] = None) -> str:
    """Tappable mention. Falls back to a t.me link, then plain escaped text."""
    safe = escape(str(name).strip() if name else "User")
    if uid:
        return f'<a href="tg://user?id={int(uid)}">{safe}</a>'
    if username and _USERNAME_RE.match(username.lstrip("@")):
        return f'<a href="https://t.me/{username.lstrip("@")}">{safe}</a>'
    return safe


def _unpack(target: Target) -> Tuple[Any, Optional[str], Optional[str]]:
    uid = target[0]
    name = target[1] if len(target) > 1 else None
    username = target[2] if len(target) > 2 else None
    return uid, name, username


def dedupe_targets(targets: Sequence[Target]) -> List[Target]:
    """Merge duplicates (same user id, else same username, else same name)."""
    seen: Set[Tuple[str, Any]] = set()
    out: List[Target] = []
    for target in targets:
        uid, name, username = _unpack(target)
        if uid:
            key = ("id", int(uid))
        elif username:
            key = ("username", username.lstrip("@").casefold())
        else:
            key = ("name", (name or "").casefold())
        if key not in seen:
            seen.add(key)
            out.append(target)
    return out


def mentions_text(targets: Sequence[Target]) -> str:
    return " &amp; ".join(_mention(*_unpack(t)) for t in targets)


def _readers_text(readers: Sequence[Target]) -> str:
    """'A', 'A & B', 'A & B & C', 'A & B & C +2'."""
    shown = [_mention(*_unpack(r)) for r in readers[:MAX_REVEAL_NAMES]]
    text = " &amp; ".join(shown)
    extra = len(readers) - MAX_REVEAL_NAMES
    return f"{text} +{extra}" if extra > 0 else text


def to_unix(value: Any) -> Optional[int]:
    """Naive-UTC datetime (as stored in MongoDB) or number -> unix seconds."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return int(timegm(value.utctimetuple()))
    return int(value)


def _button_row(whisper_id: str, button_style: str) -> str:
    if button_style not in _ALLOWED_STYLES:
        button_style = "danger"
    return (
        '<tg-button-row align="center">'
        f'<tg-button type="callback_data" style="{button_style}" data="whisper_view_{whisper_id}">{BUTTON}</tg-button>'
        "</tg-button-row>"
    )


# --------------------------------------------------------------------------- #
# Delivery / read-state card
# --------------------------------------------------------------------------- #

def whisper_card(
    whisper_id: str,
    targets: Optional[Sequence[Target]],
    modifiers: Iterable[str] = (),
    expires_at: Any = None,
    read: int = 0,
    readers: Sequence[Target] = (),
    button_style: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build the `rich_message` for a whisper.

    targets    list of (user_id, name[, username]); None means @all / @everyone.
    modifiers  any of: burn, delete, reveal, timer, vip, cute.
    expires_at datetime (naive UTC) or unix seconds; shown only with a timer.
    read       number of valid target reads (always from the database).
    readers    targets who read it (used by `reveal`).
    """
    if button_style is None:
        button_style = default_button_style()  # read at call time so .env loading order never matters
    mods = set(modifiers)
    label = LABELS[pick_style(mods)]
    line2: List[str] = []

    unix = to_unix(expires_at)
    if unix:
        line2.append(f'⏰ <tg-time unix="{unix}" format="r">soon</tg-time>')

    if "reveal" in mods and readers:
        line2.append(f"👀 {_readers_text(list(readers))} read it")

    if targets is None:  # @all / @everyone
        who = "Everyone"
        line2.append(f"{EYE}Read: {max(int(read), 0)}")
    else:
        unique = dedupe_targets(targets)
        if not unique:
            raise ValueError("whisper_card needs at least one target, or targets=None for everyone")
        who = mentions_text(unique)
        if len(unique) == 1:
            if read >= 1:
                label = f"{label} {EYE}"
        else:
            line2.append(f"{EYE}Read: {min(max(int(read), 0), len(unique))}/{len(unique)}")

    body = f"💌 {who} 💌"
    if line2:
        body += "<br>" + " · ".join(line2)  # <br> only when line 2 exists

    html = f"<aside>{body}<cite>{label}</cite></aside>" + _button_row(whisper_id, button_style)
    return {"html": html}


# --------------------------------------------------------------------------- #
# Terminal states (no button)
# --------------------------------------------------------------------------- #

def burned_card(names_html: str) -> Dict[str, str]:
    """`names_html` must already be escaped / built with mentions_text()."""
    return {"html": f"<aside>✅ {names_html} read it<cite>{BURNED_LABEL}</cite></aside>"}


def deleted_card() -> Dict[str, str]:
    return {"html": f"<aside>{DELETED_TEXT}</aside>"}


def expired_card() -> Dict[str, str]:
    return {"html": f"<aside>{EXPIRED_TEXT}</aside>"}


# --------------------------------------------------------------------------- #
# Database document -> card
# --------------------------------------------------------------------------- #

def modifiers_from_settings(settings: Optional[Dict[str, Any]]) -> Set[str]:
    """
    Map stored / parsed whisper settings to card modifiers.

      burn_after_reading + reveal_on_read -> burn   (!burn)
      burn_after_reading only             -> delete (!delete)
      reveal_on_read only                 -> reveal (!reveal)
    """
    settings = settings or {}
    mods: Set[str] = set()
    burn = bool(settings.get("burn_after_reading"))
    reveal = bool(settings.get("reveal_on_read"))
    if burn and reveal:
        mods.add("burn")
    elif burn:
        mods.add("delete")
    elif reveal:
        mods.add("reveal")
    if settings.get("timer") or settings.get("expires_at"):
        mods.add("timer")
    style = settings.get("style") or settings.get("style_name")
    if style in ("vip", "cute"):
        mods.add(style)
    return mods


def is_everyone(whisper: Dict[str, Any]) -> bool:
    token = whisper.get("original_target_token")
    if isinstance(token, str) and any(
        part.strip().lower() in ("@all", "@everyone") for part in token.split(",")
    ):
        return True
    return any(
        isinstance(t, dict) and t.get("type") == "all" for t in (whisper.get("targets") or [])
    )


def card_targets(whisper: Dict[str, Any]) -> Optional[List[Target]]:
    """Targets of a stored whisper as card tuples, or None for everyone."""
    if is_everyone(whisper):
        return None

    out: List[Target] = []
    for t in whisper.get("targets") or []:
        if isinstance(t, dict):
            uid = t.get("resolved_id") or t.get("target_id") or t.get("user_id")
            out.append((uid, t.get("display_name") or t.get("username"), t.get("username")))
    if not out:
        for t in whisper.get("all_targets") or []:
            if isinstance(t, (list, tuple)) and len(t) >= 3:
                uid, username, token = t[0], t[1], t[2]
                name = t[3] if len(t) > 3 else None
                out.append((uid, name or (f"@{username}" if username else token), username))
    if not out:
        uid = whisper.get("target_id")
        username = whisper.get("target_username")
        token = whisper.get("original_target_token") or "User"
        out.append((uid, f"@{username}" if username else token, username))
    return dedupe_targets(out)


def card_readers(whisper: Dict[str, Any]) -> List[Target]:
    return [
        (r.get("user_id"), r.get("name"))
        for r in (whisper.get("readers") or [])
        if isinstance(r, dict)
    ]


def read_count(whisper: Dict[str, Any]) -> int:
    """Number of valid reads. Legacy whispers (read_at only) count as one."""
    count = len(whisper.get("readers") or [])
    if count == 0 and whisper.get("read_at"):
        count = 1
    return count


def card_from_whisper(whisper: Dict[str, Any], button_style: Optional[str] = None) -> Dict[str, str]:
    """Current card for a stored whisper (unread, partially read or fully read)."""
    settings = whisper.get("settings") or {}
    return whisper_card(
        whisper["whisper_id"],
        card_targets(whisper),
        modifiers=modifiers_from_settings(settings),
        expires_at=settings.get("expires_at"),
        read=read_count(whisper),
        readers=card_readers(whisper),
        button_style=button_style,
    )


def burned_card_from_whisper(whisper: Dict[str, Any]) -> Dict[str, str]:
    """`✅ names read it` — all targets, or the actual readers for @all."""
    targets = card_targets(whisper)
    if targets is None:
        readers = card_readers(whisper)
        names = _readers_text(readers) if readers else "Everyone"
    else:
        names = mentions_text(targets)
    return burned_card(names)
