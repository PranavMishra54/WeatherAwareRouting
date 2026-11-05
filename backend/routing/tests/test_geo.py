import math

from django.test import SimpleTestCase

from routing.services.geo import simplify_path


class PathSimplificationTests(SimpleTestCase):
    def test_simplification_keeps_endpoints_and_respects_point_limit(self):
        path = [
            (41.0 + index / 10000, -88.0 + math.sin(index / 10) / 100)
            for index in range(2500)
        ]

        simplified = simplify_path(path)

        self.assertEqual(simplified[0], path[0])
        self.assertEqual(simplified[-1], path[-1])
        self.assertLessEqual(len(simplified), 600)

    def test_short_paths_are_unchanged(self):
        path = [(41.0, -88.0), (40.0, -87.0)]

        self.assertEqual(simplify_path(path), path)
