"""
Ninja Secret🥷 Rich Message API client

Pyrogram has no support for Telegram Rich Messages (Bot API 10.1+), so whisper
cards are sent / edited / offered inline through the plain HTTPS Bot API.

Methods wrapped here:
  - sendRichMessage        -> send_rich_message()
  - editMessageText        -> edit_rich_message()   (with `rich_message`)
  - answerInlineQuery      -> answer_inline_query() (results carry `rich_message`)

Design notes:
  * The bot token is never logged and is scrubbed from every error message.
  * Every failure is raised as RichApiError. `MessageNotModified` is its own
    subclass because it is expected and must be ignored by callers.
  * `RichApiError.transient` tells callers whether retrying later makes sense.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

import config
from NinjaSecret.logging import LOGGER

logger = LOGGER(__name__)

API_BASE = (getattr(config, "BOT_API_BASE", None) or "https://api.telegram.org").rstrip("/")
REQUEST_TIMEOUT = 15.0
MAX_AUTO_RETRY_AFTER = 5  # seconds; a longer flood wait is surfaced to the caller

_client: Optional[httpx.AsyncClient] = None


class RichApiError(Exception):
    """Bot API call failed."""

    def __init__(self, code: int, description: str, retry_after: Optional[int] = None):
        super().__init__(f"[{code}] {description}")
        self.code = code
        self.description = description
        self.retry_after = retry_after

    @property
    def transient(self) -> bool:
        """True when the same request may succeed later (network, flood, 5xx)."""
        return self.code in (0, 429) or self.code >= 500


class MessageNotModified(RichApiError):
    """Telegram rejected an edit because the content is identical. Safe to ignore."""


def _redact(text: str) -> str:
    token = getattr(config, "BOT_TOKEN", "") or ""
    return text.replace(token, "<token>") if token else text


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    return _client


def set_client(client: Optional[httpx.AsyncClient]) -> None:
    """Replace the shared HTTP client (used by tests)."""
    global _client
    _client = client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def call(method: str, payload: Dict[str, Any], _retried: bool = False) -> Any:
    """POST `payload` as JSON to Bot API `method` and return `result`."""
    url = f"{API_BASE}/bot{config.BOT_TOKEN}/{method}"
    try:
        response = await _get_client().post(url, json=payload)
    except httpx.HTTPError as exc:
        raise RichApiError(0, _redact(f"network error: {type(exc).__name__}: {exc}")) from None

    try:
        data = response.json()
    except ValueError:
        raise RichApiError(response.status_code, "invalid JSON response from Bot API") from None

    if data.get("ok"):
        return data.get("result")

    code = int(data.get("error_code") or response.status_code or 0)
    description = _redact(str(data.get("description") or "unknown error"))
    retry_after = (data.get("parameters") or {}).get("retry_after")

    if code == 429 and retry_after and retry_after <= MAX_AUTO_RETRY_AFTER and not _retried:
        await asyncio.sleep(retry_after + 0.2)
        return await call(method, payload, _retried=True)

    if code == 400 and "message is not modified" in description.lower():
        raise MessageNotModified(code, description)
    raise RichApiError(code, description, retry_after)


async def send_rich_message(chat_id: int, rich_message: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    """sendRichMessage. `extra` may hold message_thread_id, reply_parameters, etc."""
    payload = {"chat_id": chat_id, "rich_message": rich_message}
    payload.update(extra)
    return await call("sendRichMessage", payload)


async def edit_rich_message(
    rich_message: Dict[str, Any],
    *,
    inline_message_id: Optional[str] = None,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
) -> Any:
    """
    editMessageText with a `rich_message`.

    Pass either `inline_message_id` (inline-posted whispers) or both
    `chat_id` and `message_id`.
    """
    if inline_message_id:
        payload: Dict[str, Any] = {"inline_message_id": inline_message_id}
    elif chat_id is not None and message_id is not None:
        payload = {"chat_id": chat_id, "message_id": message_id}
    else:
        raise ValueError("edit_rich_message needs inline_message_id or chat_id + message_id")
    payload["rich_message"] = rich_message
    return await call("editMessageText", payload)


async def answer_inline_query(
    inline_query_id: str,
    results: List[Dict[str, Any]],
    *,
    cache_time: int = 1,
    is_personal: bool = True,
) -> Any:
    """answerInlineQuery with raw result dicts (see whisper_utils.create_whisper_inline_result)."""
    payload = {
        "inline_query_id": inline_query_id,
        "results": results,
        "cache_time": cache_time,
        "is_personal": is_personal,
    }
    return await call("answerInlineQuery", payload)


def dumps_size(rich_message: Dict[str, Any]) -> int:
    """UTF-8 size of a rich message payload, handy for diagnostics."""
    return len(json.dumps(rich_message, ensure_ascii=False).encode("utf-8"))
