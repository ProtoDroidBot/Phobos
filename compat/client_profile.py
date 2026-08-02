"""Detect the runtime and capabilities of an EVE client installation."""

from __future__ import annotations

import configparser
import os
from dataclasses import asdict, dataclass

from .code_ccp import CodeCcpReader


@dataclass(frozen=True)
class ClientProfile:
    eve_path: str
    server_alias: str
    build: int | None
    version: str | None
    runtime: str
    code_ccp_path: str | None
    code_magic: str | None
    has_python27: bool
    has_blue: bool
    has_planetresources_dll: bool

    @property
    def is_legacy_py27(self):
        return self.runtime == "legacy_py27"

    def as_dict(self):
        return asdict(self)


def _read_start_ini(eve_path, server_alias):
    candidates = (
        os.path.join(eve_path, server_alias, "start.ini"),
        os.path.join(eve_path, server_alias, "EVE.app", "Contents", "Resources", "build", "start.ini"),
    )
    for path in candidates:
        if not os.path.isfile(path):
            continue
        parser = configparser.ConfigParser()
        parser.read(path)
        build = parser.getint("main", "build", fallback=None)
        version = parser.get("main", "version", fallback=None)
        return build, version
    return None, None


def detect_client_profile(eve_path, server_alias="tq", runtime_override="auto"):
    eve_path = os.path.abspath(os.path.expanduser(eve_path))
    server_root = os.path.join(eve_path, server_alias)
    bin64 = os.path.join(server_root, "bin64")
    code_ccp = os.path.join(server_root, "code.ccp")
    build, version = _read_start_ini(eve_path, server_alias)

    code_magic = None
    if os.path.isfile(code_ccp):
        try:
            info = CodeCcpReader(code_ccp).inspect_first()
        except Exception:
            info = None
        if info is not None:
            code_magic = info.magic.hex()

    has_python27 = os.path.isfile(os.path.join(bin64, "python27.dll"))
    has_blue = os.path.isfile(os.path.join(bin64, "blue.dll"))
    has_planetresources_dll = os.path.isfile(os.path.join(bin64, "_eveplanetresources.dll"))

    if runtime_override != "auto":
        runtime = runtime_override
    elif has_python27 or code_magic == "03f30d0a":
        runtime = "legacy_py27"
    else:
        runtime = "python3"

    return ClientProfile(
        eve_path=eve_path,
        server_alias=server_alias,
        build=build,
        version=version,
        runtime=runtime,
        code_ccp_path=code_ccp if os.path.isfile(code_ccp) else None,
        code_magic=code_magic,
        has_python27=has_python27,
        has_blue=has_blue,
        has_planetresources_dll=has_planetresources_dll,
    )
