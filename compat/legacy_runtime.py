"""Prepare an importable Python 2.7 bytecode tree from ``code.ccp``."""

from __future__ import annotations

import json
import os
import zlib
import zipfile

from .code_ccp import PYTHON_27_MAGIC


class LegacyRuntimeError(RuntimeError):
    pass


def _archive_identity(path):
    stat = os.stat(path)
    return {"path": os.path.abspath(path), "size": stat.st_size, "mtimeNs": stat.st_mtime_ns}


def prepare_legacy_runtime(code_ccp_path, build, cache_root=None):
    """Extract zlib-compressed ``.pyj`` entries as Python 2.7 ``.pyc`` files."""
    if cache_root is None:
        cache_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, ".phobos-runtime", str(build or "unknown"))
        )
    marker_path = os.path.join(cache_root, "_code_ccp_manifest.json")
    identity = _archive_identity(code_ccp_path)
    try:
        with open(marker_path, "r", encoding="utf-8") as stream:
            previous = json.load(stream)
    except (OSError, ValueError):
        previous = None
    if previous == identity and os.path.isfile(os.path.join(cache_root, "__future__.pyc")):
        return cache_root

    os.makedirs(cache_root, exist_ok=True)
    count = 0
    with zipfile.ZipFile(code_ccp_path) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith(".pyj"):
                continue
            relative = entry.filename[:-4] + ".pyc"
            parts = relative.replace("\\", "/").split("/")
            if any(part in ("", ".", "..") for part in parts):
                raise LegacyRuntimeError("unsafe code.ccp entry: {}".format(entry.filename))
            output_path = os.path.join(cache_root, *parts)
            pyc = zlib.decompress(archive.read(entry))
            if pyc[:4] != PYTHON_27_MAGIC:
                raise LegacyRuntimeError(
                    "{} has bytecode magic {}, expected {}".format(
                        entry.filename, pyc[:4].hex(), PYTHON_27_MAGIC.hex()
                    )
                )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            write_file = True
            try:
                if os.path.getsize(output_path) == len(pyc):
                    with open(output_path, "rb") as stream:
                        write_file = stream.read() != pyc
            except OSError:
                pass
            if write_file:
                with open(output_path, "wb") as stream:
                    stream.write(pyc)
            count += 1

    if not count:
        raise LegacyRuntimeError("code.ccp contains no .pyj entries")
    with open(marker_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(identity, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return cache_root
