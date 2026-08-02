#!/usr/bin/env python3
"""Reconstruct EVE planet-resource spherical harmonics as grids and heatmaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compat.spherical_harmonics import (  # noqa: E402
    decode_template_coefficients,
    equirectangular_coordinates,
    infer_num_bands,
    surface_grid,
    theta_basis,
)


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "3396210-001"
    / "resource_pickle"
    / "app__res_planetResources.json"
)


def _numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "planet heatmaps require NumPy; install requirements-heatmap.txt"
        ) from exc
    return np


def _pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "planet heatmaps require Pillow; install requirements-heatmap.txt"
        ) from exc
    return Image, ImageDraw, ImageFont


def parse_template_selection(selection: str, count: int) -> list[int]:
    """Parse ``all`` or a comma-separated index/range selection."""
    if selection.strip().lower() == "all":
        return list(range(count))
    selected: set[int] = set()
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError("template range end cannot precede its start")
            selected.update(range(start, end + 1))
        else:
            selected.add(int(part))
    if not selected:
        raise ValueError("template selection is empty")
    invalid = [index for index in selected if index < 0 or index >= count]
    if invalid:
        raise ValueError(
            "template indices outside 0..{}: {}".format(count - 1, invalid)
        )
    return sorted(selected)


def _colorize(values, minimum: float, maximum: float):
    """Map a numeric grid to an inferno-like, color-vision-safe RGB image."""
    np = _numpy()
    Image, _, _ = _pillow()
    stops = np.asarray(
        [
            (0, 0, 4),
            (40, 11, 84),
            (101, 21, 110),
            (159, 42, 99),
            (212, 72, 66),
            (245, 125, 21),
            (250, 193, 39),
            (252, 255, 164),
        ],
        dtype=np.float64,
    )
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        raise ValueError("heatmap scale contains a non-finite value")
    if maximum <= minimum:
        normalized = np.zeros_like(values, dtype=np.float64)
    else:
        normalized = np.clip((values - minimum) / (maximum - minimum), 0.0, 1.0)
    position = normalized * (len(stops) - 1)
    lower = np.floor(position).astype(np.intp)
    upper = np.minimum(lower + 1, len(stops) - 1)
    fraction = (position - lower)[..., None]
    rgb = stops[lower] * (1.0 - fraction) + stops[upper] * fraction
    return Image.fromarray(np.rint(rgb).astype(np.uint8), mode="RGB")


def _font(ImageFont, size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow before 10.1
        return ImageFont.load_default()


def _centered_text(draw, center_x: int, y: int, text: str, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((center_x - (box[2] - box[0]) / 2, y), text, font=font, fill=fill)


def render_labeled_heatmap(
    values,
    minimum: float,
    maximum: float,
    *,
    template_index: int,
    num_bands: int,
    clamped: bool,
):
    """Create a labeled north-up equirectangular heatmap."""
    Image, ImageDraw, ImageFont = _pillow()
    heatmap = _colorize(values, minimum, maximum)
    width, height = heatmap.size
    left, top, right, bottom = 68, 42, 126, 58
    canvas = Image.new("RGB", (left + width + right, top + height + bottom), "#10131a")
    canvas.paste(heatmap, (left, top))
    draw = ImageDraw.Draw(canvas)
    label_font = _font(ImageFont, 14)
    title_font = _font(ImageFont, 16)
    text = "#e8edf5"
    muted = "#aeb8c8"
    border = "#64748b"

    title = "Planet depletion template {:02d} - {} real SH bands".format(
        template_index, num_bands
    )
    if clamped:
        title += " - display clamped at zero"
    _centered_text(draw, left + width // 2, 12, title, title_font, text)
    draw.rectangle((left - 1, top - 1, left + width, top + height), outline=border)

    for fraction, longitude in zip(
        (0.0, 0.25, 0.5, 0.75, 1.0), (-180, -90, 0, 90, 180)
    ):
        x = left + round(fraction * width)
        draw.line((x, top + height, x, top + height + 5), fill=border)
        _centered_text(draw, x, top + height + 9, "{} deg".format(longitude), label_font, muted)
    for fraction, latitude in zip(
        (0.0, 0.25, 0.5, 0.75, 1.0), (90, 45, 0, -45, -90)
    ):
        y = top + round(fraction * height)
        draw.line((left - 5, y, left, y), fill=border)
        label = "{} deg".format(latitude)
        box = draw.textbbox((0, 0), label, font=label_font)
        draw.text(
            (left - 10 - (box[2] - box[0]), y - (box[3] - box[1]) / 2),
            label,
            font=label_font,
            fill=muted,
        )

    bar_x = left + width + 30
    gradient_values = _numpy().linspace(maximum, minimum, height)[:, None]
    color_bar = _colorize(gradient_values, minimum, maximum).resize((20, height))
    canvas.paste(color_bar, (bar_x, top))
    draw.rectangle((bar_x - 1, top - 1, bar_x + 20, top + height), outline=border)
    number_format = "{:.6g}"
    draw.text((bar_x + 28, top - 7), number_format.format(maximum), font=label_font, fill=text)
    draw.text(
        (bar_x + 28, top + height - 10),
        number_format.format(minimum),
        font=label_font,
        fill=text,
    )
    draw.text((bar_x - 2, top + height + 15), "value", font=label_font, fill=muted)
    return canvas, heatmap


def make_contact_sheet(items: Iterable[tuple[int, object]], columns: int = 7):
    """Lay out raw per-template heatmaps in a labeled overview image."""
    Image, ImageDraw, ImageFont = _pillow()
    items = list(items)
    tile_width, tile_height, label_height = 180, 90, 25
    rows = math.ceil(len(items) / columns)
    sheet = Image.new(
        "RGB",
        (columns * tile_width, rows * (tile_height + label_height)),
        "#10131a",
    )
    draw = ImageDraw.Draw(sheet)
    font = _font(ImageFont, 14)
    for position, (template_index, image) in enumerate(items):
        column = position % columns
        row = position // columns
        x = column * tile_width
        y = row * (tile_height + label_height)
        thumbnail = image.resize((tile_width, tile_height), Image.Resampling.BILINEAR)
        sheet.paste(thumbnail, (x, y))
        draw.rectangle((x, y, x + tile_width - 1, y + tile_height - 1), outline="#64748b")
        _centered_text(
            draw,
            x + tile_width // 2,
            y + tile_height + 5,
            "template {:02d}".format(template_index),
            font,
            "#e8edf5",
        )
    return sheet


def _stats(values, latitude):
    np = _numpy()
    weights = np.cos(latitude)
    return {
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
        "areaWeightedMean": float(np.average(np.mean(values, axis=1), weights=weights)),
        "percentile01": float(np.percentile(values, 1)),
        "median": float(np.median(values)),
        "percentile99": float(np.percentile(values, 99)),
        "negativeCellCount": int(np.count_nonzero(values < 0.0)),
    }


def reconstruct(
    input_path: Path,
    output_dir: Path,
    *,
    selection: str,
    width: int,
    height: int,
    allow_negative: bool,
    global_scale: bool,
    write_grids: bool,
):
    """Decode the selected templates, save grids, heatmaps, and a manifest."""
    np = _numpy()
    with input_path.open("r", encoding="utf-8") as stream:
        source = json.load(stream)
    templates = source.get("depletionTemplates")
    if not isinstance(templates, list) or not templates:
        raise ValueError("input JSON has no non-empty depletionTemplates array")
    indices = parse_template_selection(selection, len(templates))

    first_coefficients = decode_template_coefficients(templates[indices[0]])
    num_bands = infer_num_bands(len(first_coefficients))
    longitude, latitude, theta = equirectangular_coordinates(width, height)
    basis = theta_basis(num_bands, theta)

    output_dir.mkdir(parents=True, exist_ok=True)
    grids: dict[int, object] = {}
    coefficients_by_index = {indices[0]: first_coefficients}
    template_records = []
    for template_index in indices:
        template = templates[template_index]
        coefficients = coefficients_by_index.get(template_index)
        if coefficients is None:
            coefficients = decode_template_coefficients(template)
        if infer_num_bands(len(coefficients)) != num_bands:
            raise ValueError("all selected templates must have the same band count")
        _, _, values = surface_grid(
            coefficients,
            width,
            height,
            precomputed_theta_basis=basis,
        )
        grid = values.astype(np.float32)
        grids[template_index] = grid
        template_records.append(
            {
                "index": template_index,
                "numBands": num_bands,
                "coefficientCount": len(coefficients),
                "bufferSha256": template.get("bufferSha256"),
                "rawGridStats": _stats(grid, latitude),
            }
        )

    display_grids = {
        index: (grid if allow_negative else np.maximum(grid, 0.0))
        for index, grid in grids.items()
    }
    if global_scale:
        display_minimum = min(float(np.min(grid)) for grid in display_grids.values())
        display_maximum = max(float(np.max(grid)) for grid in display_grids.values())
    else:
        display_minimum = display_maximum = None

    contact_items = []
    for record in template_records:
        template_index = record["index"]
        display = display_grids[template_index]
        minimum = (
            display_minimum if global_scale else float(np.min(display))
        )
        maximum = (
            display_maximum if global_scale else float(np.max(display))
        )
        labeled, raw_heatmap = render_labeled_heatmap(
            display,
            minimum,
            maximum,
            template_index=template_index,
            num_bands=num_bands,
            clamped=not allow_negative,
        )
        filename = "template_{:02d}_heatmap.png".format(template_index)
        labeled.save(output_dir / filename, format="PNG", compress_level=6)
        record["heatmap"] = filename
        record["displayScale"] = {"minimum": minimum, "maximum": maximum}
        contact_items.append((template_index, raw_heatmap))

    contact_name = "planet_resource_templates.png"
    make_contact_sheet(contact_items).save(
        output_dir / contact_name, format="PNG", compress_level=6
    )

    grid_name = None
    if write_grids:
        grid_name = "surface_grids.npz"
        arrays = {
            "longitudeDegrees": np.degrees(longitude).astype(np.float32),
            "latitudeDegrees": np.degrees(latitude).astype(np.float32),
        }
        arrays.update(
            {
                "template_{:02d}".format(index): grid
                for index, grid in grids.items()
            }
        )
        np.savez_compressed(output_dir / grid_name, **arrays)

    source_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    manifest = {
        "source": os.fspath(input_path.resolve()),
        "sourceSha256": source_digest,
        "decoder": {
            "coefficientSource": "bufferBase64 decoded as little-endian float32",
            "coefficientOrdering": "index = l * (l + 1) + m",
            "basis": "orthonormal real spherical harmonics",
            "normalization": "sqrt((2l+1)/(4pi) * (l-|m|)!/(l+|m|)!) and sqrt(2) when m != 0",
            "associatedLegendrePhase": "Condon-Shortley (-1)^m",
            "negativeOrderAzimuth": "sin(abs(m) * phi)",
            "positiveOrderAzimuth": "cos(m * phi)",
            "angles": "phi=longitude, theta=colatitude",
            "nativeReference": "_eveplanetresources.dll SHBuilder.SHBasisFunc",
            "evaluation": "analytic; does not reproduce the native 2048-step lookup-table quantization",
        },
        "surfaceGrid": {
            "projection": "equirectangular",
            "shape": [height, width],
            "rowOrder": "north to south",
            "longitudeRangeDegrees": [-180.0, 180.0],
            "latitudeRangeDegrees": [90.0, -90.0],
            "sampling": "pixel centers; the antimeridian and poles are not duplicated",
            "valueEncoding": "float32",
            "archive": grid_name,
        },
        "heatmaps": {
            "negativeValues": "preserved" if allow_negative else "clamped to zero",
            "scale": "global" if global_scale else "per-template",
            "colorMap": "inferno-like",
            "contactSheet": contact_name,
        },
        "depletionStdDevMin": source.get("depletionStdDevMin"),
        "depletionStdDevMax": source.get("depletionStdDevMax"),
        "depletionStdDevStepSize": source.get("depletionStdDevStepSize"),
        "templates": template_records,
    }
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest_path, contact_name, grid_name, len(indices)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Decode planetResources bufferBase64 coefficients into spherical "
            "surface grids and equirectangular heatmaps."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help="planetResources JSON (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output directory (default: <input folder>/planetResources_heatmaps)",
    )
    parser.add_argument(
        "--templates",
        default="all",
        help="all, an index, or comma-separated indices/ranges such as 0,10-14,55",
    )
    parser.add_argument("--width", type=int, default=720, help="grid width (default: 720)")
    parser.add_argument("--height", type=int, default=360, help="grid height (default: 360)")
    parser.add_argument(
        "--allow-negative",
        action="store_true",
        help="show negative truncation/ringing instead of client-style zero clamping",
    )
    parser.add_argument(
        "--global-scale",
        action="store_true",
        help="use one color scale for all selected templates",
    )
    parser.add_argument(
        "--no-grids",
        action="store_true",
        help="do not save the compressed surface_grids.npz archive",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = args.input.resolve()
    if not input_path.is_file():
        parser.error("input file does not exist: {}".format(input_path))
    output_dir = (
        args.output.resolve()
        if args.output
        else input_path.parent / "planetResources_heatmaps"
    )
    try:
        manifest_path, contact_name, grid_name, count = reconstruct(
            input_path,
            output_dir,
            selection=args.templates,
            width=args.width,
            height=args.height,
            allow_negative=args.allow_negative,
            global_scale=args.global_scale,
            write_grids=not args.no_grids,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, "error: {}\n".format(exc))
    print("Decoded {} template(s) into {}".format(count, output_dir))
    print("Manifest: {}".format(manifest_path))
    print("Contact sheet: {}".format(output_dir / contact_name))
    if grid_name:
        print("Surface grids: {}".format(output_dir / grid_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
