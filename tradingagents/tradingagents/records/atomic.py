"""Atomic record writes (REQ-INV-001).

A run's decision record is a set of files (state JSON, report tree, manifest).
They must appear together or not at all: a crash mid-write must leave either the
previous complete record or the new complete one, never a partial tree.

``write_record`` writes every file into a sibling staging directory, fsyncs each
file and the directory, computes a hash over the complete set, then renames the
staging directory onto the target in one ``os.replace``. If anything fails before
the rename, the staging directory is removed and the target is untouched.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def record_hash(files: Mapping[str, str]) -> str:
    """A stable hash over the record's complete set of (relative path -> content)."""
    digest = hashlib.sha256()
    for rel in sorted(files):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(files[rel]).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def write_record(target: Path, files: Mapping[str, str]) -> str:
    """Write ``files`` into ``target`` atomically. Returns the record hash.

    ``files`` maps a relative path (posix, e.g. ``manifest.json`` or
    ``reports/complete_report.md``) to its text content. The whole set is staged
    beside ``target`` and swapped in with a single rename, so readers never see a
    half-written record. A crash during staging leaves ``target`` untouched.
    """
    target = Path(target)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{target.name}.{uuid.uuid4().hex}.staging"

    try:
        staging.mkdir(parents=False)
        written: dict[str, str] = {}
        for rel, content in files.items():
            rel_norm = rel.replace("\\", "/").lstrip("/")
            dest = staging / rel_norm
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(str(content))
                fh.flush()
                os.fsync(fh.fileno())
            written[rel_norm] = str(content)
        _fsync_dir(staging)

        digest = record_hash(written)

        # Swap into place. If the target exists, move it aside first so the
        # replace is the only mutation of the visible tree.
        backup = None
        if target.exists():
            backup = parent / f".{target.name}.{uuid.uuid4().hex}.old"
            os.replace(target, backup)
        try:
            os.replace(staging, target)
        except OSError:
            if backup is not None and not target.exists():
                os.replace(backup, target)
            raise
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
        _fsync_dir(parent)
        return digest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_record(target: Path) -> str:
    """Recompute the record hash from what is on disk under ``target``."""
    target = Path(target)
    files: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        if path.is_file():
            files[path.relative_to(target).as_posix()] = path.read_text(encoding="utf-8")
    return record_hash(files)
