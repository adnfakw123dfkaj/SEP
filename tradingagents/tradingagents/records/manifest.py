"""Part 3's single run-manifest writer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from tradingagents.contracts import RunManifest
from tradingagents.security import scrub_manifest


def write_run_manifest(directory: str | Path, manifest: RunManifest) -> Path:
    """Redact and write ``manifest`` atomically under ``directory``."""
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"run_manifest_{manifest.date}.json"
    scrubbed = RunManifest.model_validate(
        scrub_manifest(manifest.model_dump(mode="json"))
    )

    fd, temp_name = tempfile.mkstemp(dir=target_dir, prefix=".manifest-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(scrubbed.model_dump_json(indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return path
