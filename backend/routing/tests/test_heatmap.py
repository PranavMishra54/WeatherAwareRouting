from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from routing.services.heatmap import (
    build_heatmap,
    sample_corridor,
    weather_intensity,
)
from routing.services.weather import HourlyWeather


class WeatherIntensityTests(SimpleTestCase):
    def test_scales_and_clamps_weather_values(self):
        cases = [
            ((55, 0, 0), 1.0),
            ((27.5, 0, 0), 0.5),
            ((0, 0.5, 0), 0.5),
            ((0, 0, 3), 1.0),
            ((0, 0, 0), 0.0),
            ((100, 2, 4), 1.0),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                self.assertEqual(weather_intensity(*values), expected)


class CorridorSamplingTests(SimpleTestCase):
    def test_overlapping_paths_deduplicate_and_preserve_endpoints(self):
        chicago_to_dallas = [(41.8781, -87.6298), (32.7767, -96.7970)]
        overlapping_route = [
            chicago_to_dallas[0],
            (37.0, -92.0),
            chicago_to_dallas[1],
        ]

        points = sample_corridor(
            [chicago_to_dallas, overlapping_route],
            spacing_miles=5,
            max_points=8,
        )

        self.assertLessEqual(len(points), 8)
        self.assertEqual(points[0], (round(chicago_to_dallas[0][0], 2), round(chicago_to_dallas[0][1], 2)))
        self.assertIn(
            (round(chicago_to_dallas[-1][0], 2), round(chicago_to_dallas[-1][1], 2)),
            points,
        )
        self.assertEqual(len(points), len(set(points)))


class HeatmapBuildTests(SimpleTestCase):
    def setUp(self):
        self.departure = datetime(2026, 11, 3, 8, 43, tzinfo=timezone.utc)
        self.path = [(41.88, -87.63), (41.88, -87.0)]

    @patch("routing.services.heatmap.fetch_hourly")
    def test_builds_hourly_frames_drops_low_values_and_never_empties_frame(self, fetch):
        def fake_fetch(points, start, end):
            self.assertEqual(start, datetime(2026, 11, 3, 8, tzinfo=timezone.utc))
            self.assertEqual(end, datetime(2026, 11, 5, 8, tzinfo=timezone.utc))
            values = []
            for hour in range(49):
                values.append(
                    HourlyWeather(
                        time=start + timedelta(hours=hour),
                        wind_mph=55 if hour == 12 else 0,
                        rain_in_hr=0,
                        snow_in_hr=0,
                    )
                )
            quiet_values = [
                HourlyWeather(
                    time=start + timedelta(hours=hour),
                    wind_mph=0,
                    rain_in_hr=0,
                    snow_in_hr=0,
                )
                for hour in range(49)
            ]
            return [values] + [quiet_values for _ in points[1:]]

        fetch.side_effect = fake_fetch
        result = build_heatmap([self.path], self.departure)

        self.assertEqual(result["hours"], list(range(49)))
        self.assertEqual(len(result["frames"]), 49)
        self.assertEqual(
            result["start_time"],
            "2026-11-03T08:00:00Z",
        )
        self.assertEqual(result["frames"][0], [[41.88, -87.63, 0.0]])
        self.assertEqual(result["frames"][12][0], [41.88, -87.63, 1.0])
        self.assertTrue(all(result["frames"]))
        fetch.assert_called_once()

    @patch("routing.services.heatmap.fetch_hourly")
    def test_missing_hour_is_zero_and_strongest_point_is_kept(self, fetch):
        fetch.return_value = [
            [
                HourlyWeather(self.departure.replace(minute=0), 0, 0, 0),
            ]
            for _ in sample_corridor([self.path])
        ]

        result = build_heatmap([self.path], self.departure, hours=1)

        self.assertEqual(len(result["frames"]), 2)
        self.assertEqual(len(result["frames"][1]), 1)
        self.assertEqual(result["frames"][1][0][2], 0.0)
