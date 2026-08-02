"""Read EVE ``code.ccp`` archives without importing their bytecode."""

from __future__ import annotations

import hashlib
import io
import zlib
import zipfile
from dataclasses import dataclass


PYTHON_27_MAGIC = b"\x03\xf3\r\n"


@dataclass(frozen=True)
class PyjInfo:
    name: str
    compressed_size: int
    pyc_size: int
    magic: bytes
    sha256: str

    @property
    def is_python27(self):
        return self.magic == PYTHON_27_MAGIC


class CodeCcpReader:
    """Inspect zlib-compressed ``.pyj`` entries inside ``code.ccp``."""

    def __init__(self, archive_path):
        self.archive_path = str(archive_path)

    def names(self):
        with zipfile.ZipFile(self.archive_path) as archive:
            return tuple(archive.namelist())

    def read_pyc(self, entry_name):
        with zipfile.ZipFile(self.archive_path) as archive:
            compressed = archive.read(entry_name)
        return zlib.decompress(compressed)

    def inspect(self, entry_name):
        with zipfile.ZipFile(self.archive_path) as archive:
            compressed = archive.read(entry_name)
        pyc = zlib.decompress(compressed)
        return PyjInfo(
            name=entry_name,
            compressed_size=len(compressed),
            pyc_size=len(pyc),
            magic=pyc[:4],
            sha256=hashlib.sha256(pyc).hexdigest(),
        )

    def inspect_first(self, candidates=("fsd/schemas/binaryLoader.pyj", "__init__.pyj")):
        names = set(self.names())
        for candidate in candidates:
            if candidate in names:
                return self.inspect(candidate)
        for name in sorted(names):
            if name.endswith(".pyj"):
                return self.inspect(name)
        return None

    def is_pyj_archive(self):
        try:
            return any(name.endswith(".pyj") for name in self.names())
        except (OSError, zipfile.BadZipFile, zlib.error):
            return False
