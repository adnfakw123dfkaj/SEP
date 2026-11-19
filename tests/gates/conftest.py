"""Tests for the blocking-gate checks in ``scripts/gates``.

Each gate is a pure function checked directly here with synthetic inputs, so the
"block/pass" behaviour is verified offline without GitHub or a network.
"""

import sys
from pathlib import Path

_GATES = Path(__file__).resolve().parents[2] / "scripts" / "gates"
if str(_GATES) not in sys.path:
    sys.path.insert(0, str(_GATES))
