"""The engine in a visitor's browser (EXP-023, PLAN_BEYOND_CI W6).

Pyodide runs this module in a Web Worker. `app` is the server's own compute routers, with
neither the rate limiter, Socket.IO, nor Polity's run explorer; `handle` answers one HTTP
request through it in-process, so a request gets the same validation, worker, status and
JSON as on the server. Where threads do not exist, the workers run inline
(api/engine/utils/runtime.py).
"""

from typing import Any

from fastapi import FastAPI
from starlette.types import Message, Scope

from api.core.errors import unhandled_exception_handler
from api.routes import election, simulations, tech, theory

ROUTERS = (election, simulations, tech, theory)

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
for _module in ROUTERS:
    app.include_router(_module.router)
app.add_exception_handler(Exception, unhandled_exception_handler)


async def handle(method: str, path: str, query: str, body: str) -> tuple[int, str]:
    """One request through `app`, without a socket: its status and its body."""
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": query.encode(),
        "headers": [(b"content-type", b"application/json")],
        "client": ("browser", 0),
        "server": ("browser", 0),
    }
    response: dict[str, Any] = {"status": 500, "body": b""}

    async def receive() -> Message:
        return {"type": "http.request", "body": body.encode(), "more_body": False}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
        elif message["type"] == "http.response.body":
            response["body"] += message.get("body", b"")

    try:
        await app(scope, receive, send)
    except Exception:  # noqa: BLE001
        # Starlette re-raises an unhandled exception after the catch-all handler has
        # sent its 500; the response above is the one a client over HTTP would get.
        pass
    return response["status"], response["body"].decode()
