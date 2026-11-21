"""Redirected CLI output must not fail on characters the locale cannot encode."""

import io

import pytest

from cli.encoding import ensure_utf8_output

pytestmark = pytest.mark.unit


def test_ensure_utf8_output_reconfigures_a_legacy_redirected_stream():
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="gbk")

    ensure_utf8_output([stream])
    stream.write("check: \u2713")
    stream.flush()

    assert raw.getvalue().decode("utf-8") == "check: \u2713"
