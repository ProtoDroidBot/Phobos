import base64
import json
import math
import os
import struct
import unittest

from compat.spherical_harmonics import (
    associated_legendre,
    coefficient_degree_order,
    coefficient_index,
    decode_template_coefficients,
    equirectangular_coordinates,
    evaluate,
    normalization,
    real_sh_basis,
    surface_grid,
)
from tools.render_planet_resources import parse_template_selection


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANET_RESOURCES = os.path.join(
    PROJECT_ROOT,
    "3396210-001",
    "resource_pickle",
    "app__res_planetResources.json",
)


class SphericalHarmonicUnitTests(unittest.TestCase):
    def test_index_round_trip(self):
        for index in range(900):
            degree, order = coefficient_degree_order(index)
            self.assertEqual(coefficient_index(degree, order), index)

    def test_dll_basis_normalization_constants(self):
        expected = [
            0.28209479177387814,
            0.48860251190291998,
            0.48860251190291992,
            0.48860251190291998,
            0.18209140509867985,
            0.36418281019735971,
            0.63078313050504009,
            0.36418281019735971,
            0.18209140509867985,
        ]
        for index, expected_value in enumerate(expected):
            degree, order = coefficient_degree_order(index)
            self.assertAlmostEqual(normalization(degree, order), expected_value, places=14)

    def test_condon_shortley_and_real_azimuth_convention(self):
        self.assertAlmostEqual(associated_legendre(1, 1, 0.0), -1.0)
        equator = math.pi / 2.0
        self.assertAlmostEqual(real_sh_basis(1, math.pi / 2.0, equator), -0.48860251190292)
        self.assertAlmostEqual(real_sh_basis(2, 0.0, 0.0), 0.48860251190292)
        self.assertAlmostEqual(real_sh_basis(3, 0.0, equator), -0.48860251190292)

    def test_buffer_base64_is_source_of_truth(self):
        values = (1.25, -2.5, 3.75, 4.0)
        raw = struct.pack("<4f", *values)
        template = {
            "bufferBase64": base64.b64encode(raw).decode("ascii"),
            "bufferLength": len(raw),
            "coefficientCount": 4,
            "coefficientEncoding": "float32-le",
            "numBands": 2,
            "coefficients": list(values),
        }
        self.assertEqual(decode_template_coefficients(template), list(values))
        template["coefficients"][0] = 9.0
        with self.assertRaisesRegex(ValueError, "does not match bufferBase64"):
            decode_template_coefficients(template)

    def test_vector_grid_matches_scalar_evaluator(self):
        coefficients = [
            0.3,
            -0.2,
            0.7,
            0.1,
            -0.4,
            0.6,
            0.8,
            -0.5,
            0.25,
        ]
        width, height = 7, 5
        longitude, _, theta = equirectangular_coordinates(width, height)
        _, _, grid = surface_grid(coefficients, width=width, height=height)
        for row in range(height):
            for column in range(width):
                expected = evaluate(coefficients, longitude[column], theta[row])
                self.assertAlmostEqual(grid[row, column], expected, places=12)

    def test_template_selection(self):
        self.assertEqual(parse_template_selection("0,2-4,2", 6), [0, 2, 3, 4])
        self.assertEqual(parse_template_selection("all", 3), [0, 1, 2])
        with self.assertRaises(ValueError):
            parse_template_selection("7", 3)


@unittest.skipUnless(os.path.isfile(PLANET_RESOURCES), "extracted planetResources JSON is unavailable")
class PlanetResourcesJsonTests(unittest.TestCase):
    def test_all_buffers_decode_to_900_coefficients(self):
        with open(PLANET_RESOURCES, encoding="utf-8") as stream:
            source = json.load(stream)
        self.assertEqual(len(source["depletionTemplates"]), 56)
        for template in source["depletionTemplates"]:
            self.assertEqual(len(decode_template_coefficients(template)), 900)


if __name__ == "__main__":
    unittest.main()
