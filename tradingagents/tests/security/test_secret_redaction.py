"""REQ-INV-004 — No secret leakage (Part 5).

Traceable to test-cases/part5-security-rating.md TC-P5-INV004-01..06. The
central redaction module (``tradingagents.security.redaction``) is tested for
real here, together with the existing ``dataflows.net.get_scrubbed``. Only
*synthetic* keys are used.
"""

import io
import logging

import requests

from tradingagents.security.redaction import (
    REDACTED,
    RedactingFilter,
    contains_secret,
    redact,
    redact_obj,
    redact_text,
    safe_prompt_payload,
    scrub_manifest,
)

# Synthetic keys — not real credentials.
SYNTHETIC_KEYS = [
    "sk-synthetic0123456789abcdefABCDEF",
    "sk-ant-synthetic0123456789abcdef",
    "ghp_synthetic0123456789ABCDEFabcd",
    "AKIAIOSFODNN7EXAMPLE",
]


def test_existing_scrub_redacts_secret(monkeypatch):
    """A vendor HTTP error has its query key replaced with ***."""
    def boom(*args, **kwargs):
        raise requests.ConnectionError("failed for https://x?key=SECRET123")

    monkeypatch.setattr(requests, "get", boom)
    from tradingagents.dataflows.net import get_scrubbed

    try:
        get_scrubbed("https://x", params={}, timeout=1, secret="SECRET123")
    except requests.ConnectionError as exc:
        assert "SECRET123" not in str(exc)
        assert "***" in str(exc)
    else:
        raise AssertionError("expected ConnectionError")


def test_artifacts(monkeypatch):
    """TC-P5-INV004-01: no secrets in logs/reports/manifest."""
    for key in SYNTHETIC_KEYS:
        monkeypatch.setenv("OPENAI_API_KEY", key)

    # Logs: a record carrying a deferred-format argument and an exception.
    logger = logging.getLogger("part5.artifacts")
    logger.setLevel(logging.DEBUG)
    for h in list(logger.handlers):
        logger.removeHandler(h)
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)

    key = SYNTHETIC_KEYS[0]
    logger.info("auth key=%s", key)
    logger.error("Bearer %s", key)
    try:
        raise RuntimeError(f"provider rejected api_key={key}")
    except RuntimeError:
        logger.exception("call failed")

    # Manifest / report sink: a nested dict whose fields carry the key.
    manifest = {
        "run_id": "run-1",
        "events": [{"error": f"bad token {key}"}],
        "model": {"api_key": key},
        "nested": {"deeper": [key, {"blob": f"x{key}y"}]},
    }
    scrubbed = scrub_manifest(manifest)

    # None of the sinks contain the key or any known pattern.
    log_text = buffer.getvalue()
    assert key not in log_text
    assert not contains_secret(log_text)
    serialized = repr(scrubbed)
    assert not any(k in serialized for k in SYNTHETIC_KEYS)
    assert not contains_secret(serialized)


def test_redaction(monkeypatch):
    """TC-P5-INV004-02: synthetic secrets fully redacted in every shape."""
    for key in SYNTHETIC_KEYS:
        monkeypatch.setenv("OPENAI_API_KEY", key)

    # Every synthetic key, in each sink, is fully replaced.
    for key in SYNTHETIC_KEYS:
        assert key not in redact_text(f"prefix {key} suffix")
        assert redact(key) == REDACTED or key not in redact(key)
        # Nested data keeps its shape but loses the secret.
        nested = {"a": [key, {"b": f"{key}"}], "c": (key, 1), "d": {"e": key}}
        out = redact_obj(nested)
        assert key not in repr(out)
        # Re-formatting a log arg that yields the key is redacted too.
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname=__file__, lineno=1,
            msg="key=%s", args=(key,), exc_info=None,
        )
        RedactingFilter().filter(record)
        assert key not in record.getMessage()

    # Exceptions are scrubbed while their type and surrounding text survive.
    key = SYNTHETIC_KEYS[1]
    exc = RuntimeError(f"failed for Authorization: Bearer {key}")
    scrubbed = redact_obj(exc)
    assert isinstance(scrubbed, RuntimeError)
    assert key not in str(scrubbed)
    assert REDACTED in str(scrubbed)
    assert "failed for Authorization" in str(scrubbed)

    # 100% rate: none of the keys survive any sink above.
    sinks = [redact_text(" ".join(SYNTHETIC_KEYS))]
    assert all(not any(k in s for k in SYNTHETIC_KEYS) for s in sinks)


def test_prompt_payload(monkeypatch):
    """TC-P5-INV004-04: no secrets in the model payload."""
    for key in SYNTHETIC_KEYS:
        monkeypatch.setenv("OPENAI_API_KEY", key)

    key = SYNTHETIC_KEYS[0]
    messages = [
        {"role": "system", "content": f"You are an analyst. debug key={key}"},
        {"role": "user", "content": f"news: AAPL up 2%. header Bearer {key}"},
    ]
    payload = safe_prompt_payload(messages)
    serialized = repr(payload)
    assert key not in serialized
    assert not contains_secret(serialized)
    # The legitimate facts survive redaction.
    assert "AAPL up 2%" in serialized
    assert "You are an analyst." in serialized


def test_env_only_key_source(monkeypatch):
    """TC-P5-INV004-06: redaction uses keys from the environment, not a file.

    The real client resolves its key via ``get_api_key_env`` + ``os.environ``;
    this confirms redaction picks up exactly that env-sourced value and that no
    file on disk is consulted to obtain a secret to redact.
    """
    from tradingagents.llm_clients.api_key_env import get_api_key_env

    env_name = get_api_key_env("openai")
    assert env_name == "OPENAI_API_KEY"
    key = "sk-envonly0123456789abcdefXYZ"
    monkeypatch.setenv(env_name, key)

    # The redactor registers the env value and removes it.
    assert key not in redact(f"leak {key}")

    # A same-shaped value read from a file is NOT what the client/redactor
    # sources; redaction still removes it only because of its pattern, not a
    # file read. We assert the client chain reads env, never the file.
    import inspect

    import tradingagents.llm_clients.openai_client as oc

    source = inspect.getsource(oc)
    assert "os.environ.get(api_key_env)" in source


# ---------------------------------------------------------------------------
# Handler-level install (REQ-INV-004): child-logger propagation, direct handler,
# re-install idempotency, and exception/format preservation.
# ---------------------------------------------------------------------------

def _capture(handler: logging.Handler) -> "io.StringIO":
    stream = io.StringIO()
    handler.setStream(stream)  # type: ignore[attr-defined]
    return stream


def _all_handlers() -> list[logging.Handler]:
    hs: list[logging.Handler] = list(logging.getLogger().handlers)
    for lg in logging.Logger.manager.loggerDict.values():
        if isinstance(lg, logging.Logger):
            hs.extend(lg.handlers)
    return hs


class _restore_filters:
    """Context manager: snapshot every handler's filters and restore on exit, so
    install_log_filter() (which walks the global logging tree) cannot pollute
    other tests' handlers."""

    def __enter__(self):
        self._snap = {id(h): (h, list(h.filters)) for h in _all_handlers()}
        return self

    def __exit__(self, *exc):
        from tradingagents.security.redaction import RedactingFilter

        # Remove any redacting filters we may have added, restore originals.
        for handler in _all_handlers():
            for f in list(handler.filters):
                if isinstance(f, RedactingFilter):
                    handler.removeFilter(f)
        for handler, filters in self._snap.values():
            for f in filters:
                if f not in handler.filters:
                    handler.addFilter(f)
        return False


def test_child_logger_propagation_is_redacted(monkeypatch):
    """A non-pattern synthetic key emitted on a child logger never reaches
    output, even though the filter lives on the root handler (propagation)."""
    from tradingagents.security.redaction import install_log_filter, register_secret

    key = "syntheticchildkeyNOTpattern0123456789"
    register_secret(key)  # registered literal: no recognisable pattern

    root = logging.getLogger()
    root_handler = logging.StreamHandler(io.StringIO())
    root_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    root.addHandler(root_handler)
    child = logging.getLogger("tradingagents.part5.child")
    child.setLevel(logging.DEBUG)
    child.propagate = True
    try:
        with _restore_filters():
            installed = install_log_filter()
            assert root_handler in installed
            stream = _capture(root_handler)
            # No filter on the child logger or the root logger — only on the
            # handler. Deferred formatting arg carries the key.
            child.info("token=%s", key)
            text = stream.getvalue()
        assert key not in text, "child-logger key leaked to output"
        assert "INFO:tradingagents.part5.child" in text  # format preserved
    finally:
        root.removeHandler(root_handler)


def test_direct_handler_install_redacts(monkeypatch):
    """register_handler() on a single handler redacts output written directly."""
    from tradingagents.security.redaction import register_handler, register_secret

    key = "synthetichandlerkey0123456789ABCDEF"
    register_secret(key)  # exact literal, no recognisable token pattern
    handler = logging.StreamHandler(io.StringIO())
    handler.setFormatter(logging.Formatter("%(message)s"))
    register_handler(handler)
    logger = logging.getLogger("tradingagents.part5.direct")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    try:
        stream = handler.stream  # type: ignore[attr-defined]
        logger.warning("key is %s", key)
        out = stream.getvalue()
        assert key not in out
    finally:
        logger.removeHandler(handler)


def test_install_is_idempotent_on_handler():
    """Installing twice adds exactly one redacting filter to a handler."""
    from tradingagents.security.redaction import (
        RedactingFilter,
        install_log_filter,
        register_handler,
    )

    handler = logging.StreamHandler(io.StringIO())
    register_handler(handler)
    register_handler(handler)
    n = sum(1 for f in handler.filters if isinstance(f, RedactingFilter))
    assert n == 1

    root = logging.getLogger()
    root.addHandler(handler)
    try:
        with _restore_filters():
            install_log_filter()
            install_log_filter()
            n = sum(1 for f in handler.filters if isinstance(f, RedactingFilter))
            assert n == 1
    finally:
        root.removeHandler(handler)


def test_exception_text_redacted_but_type_kept():
    """A logged exception keeps its type and message but not the key."""
    from tradingagents.security.redaction import register_handler, register_secret

    # Built by concatenation so no literal high-entropy token appears in source.
    key = "synthetic" + "exception" + "key" + "0123456789" + "X"
    register_secret(key)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    # Default formatter: includes the traceback text (exc_info), unlike %message.
    register_handler(handler)
    logger = logging.getLogger("tradingagents.part5.exc")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    try:
        try:
            raise RuntimeError(f"provider auth failed for {key}")
        except RuntimeError:
            logger.exception("call failed")
        err = stream.getvalue()
        assert key not in err
        assert "RuntimeError" in err  # traceback type preserved
        assert "provider auth failed for" in err  # surrounding message kept
    finally:
        logger.removeHandler(handler)
        register_secret(key)
