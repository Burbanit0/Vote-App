"""The catch-all error response, shared by the server (api/main.py) and the in-browser app
(api/browser.py)."""

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from api.engine.utils.logger import get_logger

# Most domain workers already catch their own exceptions and return a (body, 500) tuple,
# which never reaches this handler. It is the backstop for anything that still escapes
# uncaught (a route or middleware bug, not a worker's own try/except), so a genuinely
# unhandled exception is logged with a traceback instead of surfacing only as a bare 500.
_unhandled_log = get_logger("api.unhandled")


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    _unhandled_log.error(
        "http.unhandled_exception",
        method=request.method,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
