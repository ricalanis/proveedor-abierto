"""Bonus video moment (c): a live-view URL that dies with its session.

Runs ON the control-plane VM, against the browser-agent controller's MCP endpoint (loopback). It opens one scratch
session (read-only navigation of example.com, no model calls, never part of a case run), prints the session's
live-view URL, keeps the session open for --hold seconds while you film the stream, then closes it. After the close
the same URL returns NetBird's 404: the per-session `netbird expose` process is gone, so the public URL no longer
exists.

    ssh root@<control NetBird IP> /opt/ontofill/engine/services/browser-agent/.venv/bin/python - --hold 60 \
        < docs/demo/liveview_moment.py

The URL carries a per-session view token; it stops working at close, so showing it on screen is harmless.
"""

import argparse
import json
import time
import urllib.error
import urllib.request

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP = "http://127.0.0.1:8701/mcp"
PAGES = ["https://example.com/", "https://www.iana.org/help/example-domains", "https://example.com/"]


def data(res) -> dict:
    sc = getattr(res, "structuredContent", None) or getattr(res, "structured_content", None)
    if isinstance(sc, dict) and sc:
        return sc.get("result", sc)
    for c in res.content:
        if getattr(c, "text", None):
            try:
                return json.loads(c.text)
            except ValueError:
                return {"text": c.text[:300]}
    return {}


def status_of(url: str) -> int | str:
    try:
        return urllib.request.urlopen(url, timeout=10).status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError as exc:
        return type(exc).__name__


def say(msg: str) -> None:
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


async def main(hold: float) -> None:
    async with streamable_http_client(MCP) as st, ClientSession(st[0], st[1]) as s:
        await s.initialize()
        opened = data(
            await s.call_tool(
                "session.open",
                {
                    "tdd": {"run_id": "scratch-video-liveview", "start_url": PAGES[0]},
                    "allowed_domains": ["example.com", "www.iana.org"],
                    "limits": {
                        "max_steps": 20,
                        "budget_usd": 0.05,
                        "ttl_s": int(hold) + 120,
                        "timeout_s": int(hold) + 60,
                    },
                },
            )
        )
        sid = opened["session_id"]
        say(f"session open: {sid}")
        say(
            f"LIVE VIEW URL: {opened.get('live_view_url') or '(none: ' + json.dumps(opened.get('live_view')) + ')'}"
        )
        t0, i = time.monotonic(), 0
        while time.monotonic() - t0 < hold:
            await anyio.sleep(8)
            i += 1
            r = data(
                await s.call_tool(
                    "session.act",
                    {
                        "session_id": sid,
                        "action": {"tool": "navigate", "args": {"url": PAGES[i % len(PAGES)]}}
                        if i % 2
                        else {"tool": "scroll", "args": {}},
                    },
                )
            )
            say(f"step {i}: {r.get('status')} {r.get('url') or ''}")
        closed = data(await s.call_tool("session.close", {"session_id": sid}))
        teardown = ((closed.get("cell") or {}).get("teardown") or {}).get("state")
        say(f"session closed: token_revoked={closed.get('token_revoked')} cell teardown={teardown}")
        say("reload the live-view URL now: NetBird answers 404, the service no longer exists")
        url = opened.get("live_view_url")
        if url:  # show the 404 in the terminal too, so the take has both the browser and the proof
            for _ in range(15):
                code = await anyio.to_thread.run_sync(status_of, url)
                say(f"GET live-view URL -> {code}")
                if code == 404:
                    break
                await anyio.sleep(4)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=float, default=60, help="seconds to keep the session open (default 60)")
    anyio.run(main, ap.parse_args().hold)
