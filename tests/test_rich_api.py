"""Raw Bot API client: payload shapes, error mapping and token hygiene."""
import json

import httpx
import pytest

from NinjaSecret.utils import rich_api
from NinjaSecret.utils.rich_api import RichApiError, MessageNotModified

TOKEN = "123456:TESTTOKEN"


def install(handler):
    seen = []

    def wrapped(request: httpx.Request):
        seen.append((request.url.path, json.loads(request.content)))
        return handler(request)

    rich_api.set_client(httpx.AsyncClient(transport=httpx.MockTransport(wrapped)))
    return seen


@pytest.fixture(autouse=True)
def _reset():
    yield
    rich_api.set_client(None)


async def test_send_rich_message_payload():
    seen = install(lambda r: httpx.Response(200, json={"ok": True, "result": {"message_id": 7}}))
    res = await rich_api.send_rich_message(-100, {"html": "<aside>x</aside>"}, message_thread_id=3)
    assert res == {"message_id": 7}
    path, body = seen[0]
    assert path == f"/bot{TOKEN}/sendRichMessage"
    assert body == {"chat_id": -100, "rich_message": {"html": "<aside>x</aside>"}, "message_thread_id": 3}


async def test_edit_inline_and_chat_payloads():
    seen = install(lambda r: httpx.Response(200, json={"ok": True, "result": True}))
    await rich_api.edit_rich_message({"html": "a"}, inline_message_id="abc")
    await rich_api.edit_rich_message({"html": "a"}, chat_id=5, message_id=9)
    assert seen[0][1] == {"inline_message_id": "abc", "rich_message": {"html": "a"}}
    assert seen[1][1] == {"chat_id": 5, "message_id": 9, "rich_message": {"html": "a"}}
    assert seen[0][0].endswith("/editMessageText")


async def test_edit_requires_a_target():
    install(lambda r: httpx.Response(200, json={"ok": True, "result": True}))
    with pytest.raises(ValueError):
        await rich_api.edit_rich_message({"html": "a"})


async def test_answer_inline_query_payload():
    seen = install(lambda r: httpx.Response(200, json={"ok": True, "result": True}))
    await rich_api.answer_inline_query("q1", [{"type": "article"}], cache_time=1, is_personal=True)
    assert seen[0][1] == {"inline_query_id": "q1", "results": [{"type": "article"}],
                          "cache_time": 1, "is_personal": True}


async def test_message_not_modified_is_its_own_error():
    install(lambda r: httpx.Response(400, json={
        "ok": False, "error_code": 400,
        "description": "Bad Request: message is not modified: specified new message content..."}))
    with pytest.raises(MessageNotModified) as exc:
        await rich_api.edit_rich_message({"html": "a"}, inline_message_id="abc")
    assert isinstance(exc.value, RichApiError) and not exc.value.transient


async def test_other_400_is_permanent_error():
    install(lambda r: httpx.Response(400, json={"ok": False, "error_code": 400,
                                                "description": "Bad Request: can't parse"}))
    with pytest.raises(RichApiError) as exc:
        await rich_api.send_rich_message(1, {"html": "x"})
    assert not isinstance(exc.value, MessageNotModified) and not exc.value.transient


async def test_flood_wait_retries_once_then_succeeds(monkeypatch):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(rich_api.asyncio, "sleep", fake_sleep)
    answers = iter([
        httpx.Response(429, json={"ok": False, "error_code": 429, "description": "Too Many Requests",
                                  "parameters": {"retry_after": 2}}),
        httpx.Response(200, json={"ok": True, "result": 1}),
    ])
    seen = install(lambda r: next(answers))
    assert await rich_api.call("x", {}) == 1
    assert len(seen) == 2 and sleeps and sleeps[0] >= 2


async def test_long_flood_wait_is_surfaced_as_transient():
    install(lambda r: httpx.Response(429, json={"ok": False, "error_code": 429, "description": "Too Many Requests",
                                                "parameters": {"retry_after": 120}}))
    with pytest.raises(RichApiError) as exc:
        await rich_api.call("x", {})
    assert exc.value.transient and exc.value.retry_after == 120


async def test_network_error_is_transient_and_hides_token():
    def boom(request):
        raise httpx.ConnectError(f"failed for {request.url}")

    install(boom)
    with pytest.raises(RichApiError) as exc:
        await rich_api.call("x", {})
    assert exc.value.transient and TOKEN not in str(exc.value)


async def test_non_json_response_is_an_error():
    install(lambda r: httpx.Response(502, text="<html>bad gateway</html>"))
    with pytest.raises(RichApiError) as exc:
        await rich_api.call("x", {})
    assert exc.value.transient
