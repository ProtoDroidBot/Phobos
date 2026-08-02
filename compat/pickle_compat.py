"""Restricted readers for Python 2 era EVE pickle resources."""

from __future__ import annotations

import base64
import collections
import hashlib
import io
import math
import pickle
import struct


class RestrictedLegacyUnpickler(pickle.Unpickler):
    """Allow primitive pickle values and the one schema helper used by EVE."""

    ALLOWED_GLOBALS = {
        ("collections", "OrderedDict"): collections.OrderedDict,
    }

    def find_class(self, module, name):
        try:
            return self.ALLOWED_GLOBALS[(module, name)]
        except KeyError:
            raise pickle.UnpicklingError("forbidden global: {}.{}".format(module, name))


def restricted_loads(raw, encoding="ASCII"):
    return RestrictedLegacyUnpickler(io.BytesIO(raw), encoding=encoding, errors="strict").load()


def load_legacy_pickle(raw, preserve_bytes=False):
    """Load a Python 2 pickle without permitting arbitrary class imports."""
    if preserve_bytes:
        return restricted_loads(raw, encoding="bytes")
    try:
        return restricted_loads(raw, encoding="ASCII")
    except UnicodeDecodeError:
        return restricted_loads(raw, encoding="latin-1")


def _lookup(mapping, name):
    if name in mapping:
        return mapping[name]
    encoded = name.encode("ascii")
    if encoded in mapping:
        return mapping[encoded]
    raise KeyError(name)


def decode_planet_resources(value):
    """Decode build-3396210 spherical-harmonic depletion template buffers."""
    templates = _lookup(value, "depletionTemplates")
    decoded = {
        "depletionStdDevMin": float(_lookup(value, "depletionStdDevMin")),
        "depletionStdDevMax": float(_lookup(value, "depletionStdDevMax")),
        "depletionStdDevStepSize": float(_lookup(value, "depletionStdDevStepSize")),
        "depletionTemplates": [],
    }
    for index, buffer_value in enumerate(templates):
        raw = bytes(buffer_value)
        if len(raw) % 4:
            raise ValueError("planet resource template {} is not a float32 buffer".format(index))
        coefficient_count = len(raw) // 4
        bands = math.isqrt(coefficient_count)
        if bands * bands != coefficient_count:
            raise ValueError(
                "planet resource template {} has {} coefficients, not B*B".format(index, coefficient_count)
            )
        coefficients = list(struct.unpack("<{}f".format(coefficient_count), raw))
        if not all(math.isfinite(item) for item in coefficients):
            raise ValueError("planet resource template {} contains non-finite coefficients".format(index))
        decoded["depletionTemplates"].append(
            {
                "index": index,
                "numBands": bands,
                "coefficientCount": coefficient_count,
                "coefficientEncoding": "float32-le",
                "bufferLength": len(raw),
                "bufferSha256": hashlib.sha256(raw).hexdigest(),
                "bufferBase64": base64.b64encode(raw).decode("ascii"),
                "coefficients": coefficients,
            }
        )
    return decoded


def is_planet_resources_container(container_name):
    normalized = container_name.replace("\\", "/").lower()
    return normalized.endswith("/planetresources") or normalized == "planetresources"
