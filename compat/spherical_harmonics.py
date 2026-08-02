"""Real spherical-harmonic decoding for EVE planet resource buffers.

The basis convention in this module mirrors ``_eveplanetresources.dll`` from
client build 3396210:

* coefficient index: ``l * (l + 1) + m``;
* Schmidt-style real basis (``sqrt(2)`` for non-zero ``m``);
* Condon-Shortley phase in the associated Legendre polynomials;
* negative ``m`` uses ``sin(abs(m) * phi)``;
* positive ``m`` uses ``cos(m * phi)``.

``phi`` is longitude in radians and ``theta`` is colatitude in radians.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import math
import struct
from typing import Any, Mapping, Sequence


def coefficient_index(degree: int, order: int) -> int:
    """Return EVE's flat coefficient index for spherical harmonic ``(l, m)``."""
    if degree < 0 or abs(order) > degree:
        raise ValueError("expected degree >= 0 and -degree <= order <= degree")
    return degree * (degree + 1) + order


def coefficient_degree_order(index: int) -> tuple[int, int]:
    """Return ``(l, m)`` for an EVE flat coefficient index."""
    if index < 0:
        raise ValueError("coefficient index cannot be negative")
    degree = math.isqrt(index)
    return degree, index - degree * (degree + 1)


def infer_num_bands(coefficient_count: int) -> int:
    """Validate a square coefficient array and return its band count."""
    if coefficient_count <= 0:
        raise ValueError("a spherical harmonic needs at least one coefficient")
    bands = math.isqrt(coefficient_count)
    if bands * bands != coefficient_count:
        raise ValueError(
            "coefficient count {} is not a square B*B array".format(coefficient_count)
        )
    return bands


def normalization(degree: int, order: int) -> float:
    """Return the real-basis normalization used by the EVE DLL."""
    absolute_order = abs(order)
    if degree < 0 or absolute_order > degree:
        raise ValueError("expected degree >= 0 and -degree <= order <= degree")
    log_ratio = math.lgamma(degree - absolute_order + 1) - math.lgamma(
        degree + absolute_order + 1
    )
    value = math.sqrt((2 * degree + 1) * math.exp(log_ratio) / (4 * math.pi))
    if absolute_order:
        value *= math.sqrt(2.0)
    return value


def associated_legendre(degree: int, order: int, x: float) -> float:
    """Evaluate ``P_l^m(x)`` including the Condon-Shortley phase."""
    if degree < 0 or order < 0 or order > degree:
        raise ValueError("expected degree >= order >= 0")
    if not -1.0 <= x <= 1.0:
        if math.isclose(abs(x), 1.0, rel_tol=0.0, abs_tol=1e-15):
            x = math.copysign(1.0, x)
        else:
            raise ValueError("associated Legendre input must be in [-1, 1]")

    pmm = 1.0
    if order:
        root = math.sqrt(max(0.0, (1.0 - x) * (1.0 + x)))
        factor = 1.0
        for _ in range(order):
            pmm *= -factor * root
            factor += 2.0
    if degree == order:
        return pmm

    pmmp1 = x * (2 * order + 1) * pmm
    if degree == order + 1:
        return pmmp1

    previous = pmm
    current = pmmp1
    for current_degree in range(order + 2, degree + 1):
        following = (
            (2 * current_degree - 1) * x * current
            - (current_degree + order - 1) * previous
        ) / (current_degree - order)
        previous, current = current, following
    return current


def real_sh_basis(index: int, phi: float, theta: float) -> float:
    """Evaluate one EVE real spherical-harmonic basis function."""
    degree, order = coefficient_degree_order(index)
    absolute_order = abs(order)
    value = normalization(degree, order) * associated_legendre(
        degree, absolute_order, math.cos(theta)
    )
    if order < 0:
        return value * math.sin(absolute_order * phi)
    if order > 0:
        return value * math.cos(order * phi)
    return value


def evaluate(coefficients: Sequence[float], phi: float, theta: float) -> float:
    """Evaluate an EVE coefficient array at ``(phi, theta)``."""
    infer_num_bands(len(coefficients))
    return math.fsum(
        float(coefficient) * real_sh_basis(index, phi, theta)
        for index, coefficient in enumerate(coefficients)
    )


def decode_template_coefficients(template: Mapping[str, Any]) -> list[float]:
    """Decode and validate the little-endian float32 ``bufferBase64`` field."""
    encoded = template.get("bufferBase64")
    if not isinstance(encoded, str):
        raise ValueError("template is missing a string bufferBase64 field")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("template bufferBase64 is not valid base64") from exc
    if not raw or len(raw) % 4:
        raise ValueError("template buffer is not a non-empty float32 array")

    expected_length = template.get("bufferLength")
    if expected_length is not None and int(expected_length) != len(raw):
        raise ValueError(
            "template buffer length {} does not match declared {}".format(
                len(raw), expected_length
            )
        )
    expected_digest = template.get("bufferSha256")
    digest = hashlib.sha256(raw).hexdigest()
    if expected_digest is not None and str(expected_digest).lower() != digest:
        raise ValueError("template buffer SHA-256 does not match bufferSha256")

    count = len(raw) // 4
    bands = infer_num_bands(count)
    expected_count = template.get("coefficientCount")
    if expected_count is not None and int(expected_count) != count:
        raise ValueError("decoded coefficient count does not match coefficientCount")
    expected_bands = template.get("numBands")
    if expected_bands is not None and int(expected_bands) != bands:
        raise ValueError("decoded band count does not match numBands")
    encoding = template.get("coefficientEncoding")
    if encoding is not None and encoding != "float32-le":
        raise ValueError("unsupported coefficient encoding {!r}".format(encoding))

    coefficients = list(struct.unpack("<{}f".format(count), raw))
    if not all(math.isfinite(value) for value in coefficients):
        raise ValueError("template contains a non-finite coefficient")

    json_coefficients = template.get("coefficients")
    if json_coefficients is not None:
        if len(json_coefficients) != count:
            raise ValueError("coefficients array does not match decoded buffer length")
        if any(
            float(from_json) != from_buffer
            for from_json, from_buffer in zip(json_coefficients, coefficients)
        ):
            raise ValueError("coefficients array does not match bufferBase64")
    return coefficients


def _numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - exercised without optional extra
        raise RuntimeError(
            "surface-grid decoding requires NumPy; install requirements-heatmap.txt"
        ) from exc
    return np


def equirectangular_coordinates(width: int, height: int):
    """Return pixel-center longitude, latitude, and colatitude arrays."""
    if width < 2 or height < 2:
        raise ValueError("surface grid width and height must both be at least 2")
    np = _numpy()
    longitude = -math.pi + (np.arange(width, dtype=np.float64) + 0.5) * (
        2.0 * math.pi / width
    )
    theta = (np.arange(height, dtype=np.float64) + 0.5) * (math.pi / height)
    latitude = math.pi / 2.0 - theta
    return longitude, latitude, theta


def theta_basis(num_bands: int, theta):
    """Build the normalized associated-Legendre part of the EVE basis."""
    if num_bands <= 0:
        raise ValueError("num_bands must be positive")
    np = _numpy()
    theta_values = np.asarray(theta, dtype=np.float64)
    if theta_values.ndim != 1:
        raise ValueError("theta must be a one-dimensional array")
    x = np.cos(theta_values)
    root = np.sqrt(np.maximum(0.0, (1.0 - x) * (1.0 + x)))
    basis = np.empty((num_bands * num_bands, theta_values.size), dtype=np.float64)

    pmm = np.ones_like(x)
    for order in range(num_bands):
        if order:
            pmm = pmm * (-(2 * order - 1) * root)
        previous = pmm
        for degree in range(order, num_bands):
            if degree == order:
                current = pmm
            elif degree == order + 1:
                current = x * (2 * order + 1) * pmm
            else:
                following = (
                    (2 * degree - 1) * x * current
                    - (degree + order - 1) * previous
                ) / (degree - order)
                previous, current = current, following
            normalized = normalization(degree, order) * current
            basis[coefficient_index(degree, -order)] = normalized
            if order:
                basis[coefficient_index(degree, order)] = normalized
    return basis


def surface_grid(
    coefficients: Sequence[float],
    width: int = 720,
    height: int = 360,
    *,
    precomputed_theta_basis=None,
):
    """Reconstruct coefficients on a north-up equirectangular surface grid.

    Returns ``(longitude_radians, latitude_radians, values)``. Grid values are
    raw harmonic values; callers may clamp negative ringing for display.
    """
    np = _numpy()
    coefficient_values = np.asarray(coefficients, dtype=np.float64)
    if coefficient_values.ndim != 1:
        raise ValueError("coefficients must be one-dimensional")
    num_bands = infer_num_bands(coefficient_values.size)
    longitude, latitude, theta = equirectangular_coordinates(width, height)
    basis = (
        theta_basis(num_bands, theta)
        if precomputed_theta_basis is None
        else np.asarray(precomputed_theta_basis, dtype=np.float64)
    )
    if basis.shape != (num_bands * num_bands, height):
        raise ValueError(
            "precomputed theta basis has shape {}, expected {}".format(
                basis.shape, (num_bands * num_bands, height)
            )
        )

    zonal_indices = [coefficient_index(degree, 0) for degree in range(num_bands)]
    values = coefficient_values[zonal_indices] @ basis[zonal_indices]
    values = np.broadcast_to(values[:, None], (height, width)).copy()
    if num_bands == 1:
        return longitude, latitude, values

    orders = np.arange(1, num_bands, dtype=np.float64)
    cos_modes = np.cos(orders[:, None] * longitude[None, :])
    sin_modes = np.sin(orders[:, None] * longitude[None, :])
    cos_amplitudes = np.empty((height, num_bands - 1), dtype=np.float64)
    sin_amplitudes = np.empty_like(cos_amplitudes)
    for order in range(1, num_bands):
        positive = [
            coefficient_index(degree, order)
            for degree in range(order, num_bands)
        ]
        negative = [
            coefficient_index(degree, -order)
            for degree in range(order, num_bands)
        ]
        cos_amplitudes[:, order - 1] = coefficient_values[positive] @ basis[positive]
        sin_amplitudes[:, order - 1] = coefficient_values[negative] @ basis[negative]
    values += cos_amplitudes @ cos_modes + sin_amplitudes @ sin_modes
    return longitude, latitude, values


__all__ = (
    "associated_legendre",
    "coefficient_degree_order",
    "coefficient_index",
    "decode_template_coefficients",
    "equirectangular_coordinates",
    "evaluate",
    "infer_num_bands",
    "normalization",
    "real_sh_basis",
    "surface_grid",
    "theta_basis",
)
