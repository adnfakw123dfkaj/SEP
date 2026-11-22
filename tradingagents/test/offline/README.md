# Offline tests (D8)

Deterministic, network-free tests. This is everything under `../tests/` **except**
tests marked `integration`. The application's `tests/conftest.py` refuses sockets
for non-integration tests, so nothing here reaches the network or a live API.

Run from the `tradingagents/` project directory:

    python -m pytest tests -q -m "not integration"

Equivalent to the default `pytest` invocation (the project's `pyproject.toml`
already sets `-m "not integration"`). CI (`ci.yml` / `gates.yml`) runs this set.
