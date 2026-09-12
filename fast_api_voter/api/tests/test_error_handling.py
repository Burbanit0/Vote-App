"""Tests for api.engine.utils.error_handling — the shared safe_call /
log_and_error_response helpers introduced to centralise the "compute with
fallback" and "handler wrapping" except-Exception shapes (CODE_AUDIT.md §7
item 5)."""
import logging

import pytest

from api.engine.utils.error_handling import log_and_error_response, safe_call
from api.engine.utils.logger import get_logger


@pytest.fixture
def log():
    """The structlog logger real call sites use (`get_logger(__name__)`) —
    needed so tests exercising `**log_kwargs` forwarding match reality; a
    couple of tests below use a plain stdlib logger instead, matching
    api/engine/utils/cache.py's own (deliberately different) convention."""
    return get_logger("test_error_handling")


@pytest.fixture
def stdlib_log():
    return logging.getLogger("test_error_handling_stdlib")


class TestSafeCall:
    def test_returns_fn_result_on_success(self, log):
        assert safe_call(lambda: 42, lambda: -1, log=log, event="x") == 42

    def test_fallback_not_evaluated_on_success(self, log):
        """The fallback must be lazy — several real call sites' fallback is
        itself a non-trivial engine call that should only run on failure."""
        calls = []

        def _fallback():
            calls.append("called")
            return -1

        result = safe_call(lambda: 42, _fallback, log=log, event="x")
        assert result == 42
        assert calls == []

    def test_returns_fallback_and_logs_on_exception(self, log, caplog):
        def _boom():
            raise RuntimeError("boom")

        with caplog.at_level("WARNING"):
            result = safe_call(_boom, lambda: -1, log=log, event="thing.failed")

        assert result == -1
        assert "thing.failed" in caplog.text

    def test_default_level_is_warning(self, log, caplog):
        def _boom():
            raise RuntimeError("boom")

        with caplog.at_level("INFO"):
            safe_call(_boom, lambda: None, log=log, event="thing.failed")

        assert caplog.records[-1].levelname == "WARNING"

    def test_level_is_overridable(self, log, caplog):
        def _boom():
            raise RuntimeError("boom")

        with caplog.at_level("INFO"):
            safe_call(_boom, lambda: None, log=log, event="thing.failed", level="error")

        assert caplog.records[-1].levelname == "ERROR"

    def test_forwards_structured_kwargs_to_the_log_call(self, log, caplog):
        def _boom():
            raise RuntimeError("boom")

        with caplog.at_level("WARNING"):
            safe_call(_boom, lambda: None, log=log, event="thing.failed", method="irv", voter_idx=3)

        assert "method=irv" in caplog.text or "'method': 'irv'" in caplog.text
        assert "voter_idx=3" in caplog.text or "'voter_idx': 3" in caplog.text

    def test_logs_with_exc_info(self, log, caplog):
        # structlog's `format_exc_info` processor renders the traceback into
        # the event text itself rather than leaving it on LogRecord.exc_info
        # (unlike a plain stdlib logger) — assert on the rendered text, which
        # is exactly what every real caplog-based test in this repo does.
        def _boom():
            raise RuntimeError("boom, distinctively")

        with caplog.at_level("WARNING"):
            safe_call(_boom, lambda: None, log=log, event="thing.failed")

        assert "boom, distinctively" in caplog.text
        assert "Traceback" in caplog.text

    def test_only_exception_subclasses_are_caught(self, log):
        def _system_exit():
            raise SystemExit(1)

        with pytest.raises(SystemExit):
            safe_call(_system_exit, lambda: None, log=log, event="thing.failed")

    def test_works_with_a_plain_stdlib_logger_too(self, stdlib_log, caplog):
        """api/engine/utils/cache.py logs via `logging.getLogger(__name__)`,
        not the structlog `get_logger` — safe_call must not assume kwargs
        support beyond what a given call site actually passes."""
        def _boom():
            raise RuntimeError("boom")

        with caplog.at_level("WARNING"):
            result = safe_call(_boom, lambda: None, log=stdlib_log, event="cache.thing_failed")

        assert result is None
        assert "cache.thing_failed" in caplog.text


class TestLogAndErrorResponse:
    def test_returns_body_and_default_status(self, log):
        body, status = log_and_error_response(log, "thing.failed", {"error": "bad"})
        assert body == {"error": "bad"}
        assert status == 500

    def test_status_is_overridable(self, log):
        _, status = log_and_error_response(log, "thing.failed", {"error": "bad"}, status=404)
        assert status == 404

    def test_logs_the_event_at_default_level(self, log, caplog):
        with caplog.at_level("WARNING"):
            log_and_error_response(log, "thing.failed", {"error": "bad"})
        assert "thing.failed" in caplog.text
        assert caplog.records[-1].levelname == "ERROR"  # default level

    def test_captures_the_active_exception_traceback(self, log, caplog):
        """Real call sites invoke this from inside `except Exception as exc:`
        — exc_info=True must pick up that in-flight exception."""
        with caplog.at_level("ERROR"):
            try:
                raise RuntimeError("boom, distinctively")
            except RuntimeError:
                log_and_error_response(log, "thing.failed", {"error": "bad"})
        assert "boom, distinctively" in caplog.text
        assert "Traceback" in caplog.text

    def test_level_is_overridable(self, log, caplog):
        with caplog.at_level("INFO"):
            log_and_error_response(log, "thing.failed", {"error": "bad"}, level="warning")
        assert caplog.records[-1].levelname == "WARNING"

    def test_preserves_a_richer_body_verbatim(self, log):
        body, status = log_and_error_response(
            log, "thing.failed",
            {"success": False, "error": "bad", "message": "human readable"},
        )
        assert body == {"success": False, "error": "bad", "message": "human readable"}
        assert status == 500

    def test_forwards_structured_kwargs_to_the_log_call(self, log, caplog):
        with caplog.at_level("WARNING"):
            log_and_error_response(log, "thing.failed", {"error": "bad"}, value=7)
        assert "value=7" in caplog.text or "'value': 7" in caplog.text
