# -*- coding: utf-8 -*-
"""Isolated worker. This file intentionally remains Python 2.7 compatible."""

from __future__ import print_function

import base64
import hashlib
import imp
import json
import math
import os
import sys
import traceback


try:
    text_type = unicode
    integer_types = (int, long)
    binary_types = (str, buffer, bytearray)
except NameError:
    text_type = str
    integer_types = (int,)
    binary_types = (bytes, bytearray, memoryview)


def _byte_envelope(raw):
    raw = bytes(raw) if sys.version_info[0] >= 3 else str(raw)
    encoded = base64.b64encode(raw)
    if not isinstance(encoded, text_type):
        encoded = encoded.decode("ascii")
    return {
        "$type": "bytes",
        "encoding": "base64",
        "length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": encoded,
    }


def _text_or_bytes(value):
    raw = bytes(value) if sys.version_info[0] >= 3 else str(value)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return _byte_envelope(raw)


def normalize(value, depth=0, seen=None):
    if seen is None:
        seen = set()
    if depth > 100:
        raise ValueError("worker normalization exceeded 100 levels")
    if value is None or isinstance(value, (bool, float) + integer_types):
        return value
    if isinstance(value, text_type):
        return value
    if isinstance(value, binary_types):
        return _text_or_bytes(value)

    object_id = id(value)
    if object_id in seen:
        return {"$type": "cycle", "repr": repr(value)}
    seen.add(object_id)
    try:
        if isinstance(value, dict):
            iterator = value.iteritems() if hasattr(value, "iteritems") else value.items()
            result = {}
            for key, item in iterator:
                normalized_key = normalize(key, depth + 1, seen)
                if not isinstance(normalized_key, text_type):
                    normalized_key = text_type(normalized_key)
                result[normalized_key] = normalize(item, depth + 1, seen)
            return result
        if isinstance(value, (list, tuple, set, frozenset)):
            return [normalize(item, depth + 1, seen) for item in value]
        if hasattr(value, "_asdict"):
            return normalize(value._asdict(), depth + 1, seen)
        if hasattr(value, "items"):
            try:
                return normalize(dict(value.items()), depth + 1, seen)
            except Exception:
                pass
        attributes = {}
        for name in dir(value):
            if name.startswith("_"):
                continue
            try:
                item = getattr(value, name)
            except Exception:
                continue
            if callable(item):
                continue
            attributes[name] = normalize(item, depth + 1, seen)
        if attributes:
            return attributes
        return text_type(value)
    finally:
        seen.discard(object_id)


def load_fsd(request):
    module_name = request["moduleName"]
    module = imp.load_dynamic(module_name, request["loaderPath"])
    return normalize(module.load(request["dataPath"]))


def planet_coefficients(request):
    module = imp.load_dynamic("_eveplanetresources", request["dllPath"])
    builder = module.SHBuilder()
    builder.GenerateLookUpTables(2048)
    raw = base64.b64decode(request["bufferBase64"])
    harmonic = builder.CreateSHFromBuffer(raw, int(request["numBands"]))
    count = harmonic.GetNumCoefficients()
    return [harmonic.GetCoefficient(index) for index in range(count)]


def main(request_path, response_path):
    try:
        with open(request_path, "rb") as stream:
            request = json.load(stream)
        if request.get("schemaVersion") != 1:
            raise ValueError("unsupported worker schema version")
        action = request.get("action")
        if action == "load_fsd":
            data = load_fsd(request)
        elif action == "planet_coefficients":
            data = planet_coefficients(request)
        else:
            raise ValueError("unknown worker action: %r" % (action,))
        response = {"ok": True, "data": data}
    except Exception:
        response = {"ok": False, "error": traceback.format_exc()}
    with open(response_path, "wb") as stream:
        payload = json.dumps(response, ensure_ascii=True, separators=(",", ":"))
        if not isinstance(payload, bytes):
            payload = payload.encode("utf-8")
        stream.write(payload)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: py2_worker.py REQUEST.json RESPONSE.json")
    main(sys.argv[1], sys.argv[2])
