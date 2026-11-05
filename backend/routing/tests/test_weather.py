from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from routing.services.weather import (
    WeatherError,
    fetch_hourly,
    weather_at_checkpoints,
)


class WeatherServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.start = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def tearDown(self):
        cache.clear()

    @staticmethod
    def hourly_payload(times, winds=None, rain=None, showers=None, snow=None):
        count = len(times)
        return {
            "hourly": {
                "time": times,
                "wind_speed_10m": winds if winds is not None else [5] * count,
                "rain": rain if rain is not None else [0] * count,
                "showers": showers if showers is not None else [0] * count,
                "snowfall": snow if snow is not None else [0] * count,
            }
        }

    @patch("routing.services.weather.requests.get")
    def test_parses_single_location_response_and_combines_precipitation(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = self.hourly_payload(
            ["2026-11-03T10:00", "2026-11-03T11:00"],
            winds=[12, 14],
            rain=[0.1, None],
            showers=[0.2, 0.3],
            snow=[0.4, None],
        )

        forecasts = fetch_hourly([(41.88, -87.63)], self.start, self.end)

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0][0].time, datetime(2026, 11, 3, 10, tzinfo=timezone.utc))
        self.assertEqual(forecasts[0][0].wind_mph, 12)
        self.assertAlmostEqual(forecasts[0][0].rain_in_hr, 0.3)
        self.assertAlmostEqual(forecasts[0][0].snow_in_hr, 0.4)
        self.assertEqual(forecasts[0][1].rain_in_hr, 0.3)
        self.assertEqual(forecasts[0][1].snow_in_hr, 0)
        self.assertEqual(get.call_count, 1)

    @patch("routing.services.weather.requests.get")
    def test_parses_multi_location_response_shape(self, get):
        payload = self.hourly_payload(["2026-11-03T10:00"])
        get.return_value.status_code = 200
        get.return_value.json.return_value = [payload, payload]

        forecasts = fetch_hourly(
            [(41.88, -87.63), (32.78, -96.80)], self.start, self.end
        )

        self.assertEqual(len(forecasts), 2)
        self.assertEqual(forecasts[0], forecasts[1])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(
            get.call_args.kwargs["params"]["latitude"], "41.88,32.78"
        )

    @patch("routing.services.weather.requests.get")
    def test_selects_nearest_hour_for_checkpoint_eta(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = self.hourly_payload(
            [
                "2026-11-03T10:00",
                "2026-11-03T11:00",
                "2026-11-03T12:00",
            ],
            winds=[10, 20, 30],
        )
        checkpoint = SimpleNamespace(
            lat=41.88,
            lon=-87.63,
            eta=datetime(2026, 11, 3, 10, 40, tzinfo=timezone.utc),
        )

        weather = weather_at_checkpoints([checkpoint])

        self.assertEqual(len(weather), 1)
        self.assertEqual(weather[0].wind_mph, 20)
        self.assertEqual(weather[0].forecast_time, datetime(2026, 11, 3, 11, tzinfo=timezone.utc))

    @patch("routing.services.weather.requests.get")
    def test_splits_requests_at_fifty_unique_points(self, get):
        def response_for_chunk(_url, params, timeout):
            point_count = len(params["latitude"].split(","))
            return SimpleNamespace(
                status_code=200,
                json=lambda: [
                    self.hourly_payload(["2026-11-03T10:00"])
                    for _ in range(point_count)
                ],
            )

        get.side_effect = response_for_chunk
        points = [(float(index), float(index)) for index in range(51)]

        forecasts = fetch_hourly(points, self.start, self.end)

        self.assertEqual(len(forecasts), 51)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            [
                len(call.kwargs["params"]["latitude"].split(","))
                for call in get.call_args_list
            ],
            [50, 1],
        )
        self.assertTrue(all(call.kwargs["timeout"] == 20 for call in get.call_args_list))

    @patch("routing.services.weather.requests.get")
    def test_deduplicates_coordinates_after_rounding(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = self.hourly_payload(
            ["2026-11-03T10:00"]
        )

        forecasts = fetch_hourly(
            [(41.881, -87.631), (41.884, -87.634)], self.start, self.end
        )

        self.assertEqual(forecasts[0], forecasts[1])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["latitude"], "41.88")
        self.assertEqual(get.call_args.kwargs["params"]["longitude"], "-87.63")

    @patch("routing.services.weather.requests.get")
    def test_retries_server_error_once_then_raises(self, get):
        get.return_value.status_code = 500

        with self.assertRaisesRegex(WeatherError, "HTTP 500"):
            fetch_hourly([(41.88, -87.63)], self.start, self.end)

        self.assertEqual(get.call_count, 2)

    @patch("routing.services.weather.requests.get")
    def test_retries_network_error_once(self, get):
        get.side_effect = [
            requests.ConnectionError("offline"),
            SimpleNamespace(
                status_code=200,
                json=lambda: self.hourly_payload(["2026-11-03T10:00"]),
            ),
        ]

        forecasts = fetch_hourly([(41.88, -87.63)], self.start, self.end)

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(get.call_count, 2)

    @patch("routing.services.weather.requests.get")
    def test_rejects_eta_beyond_forecast_limit(self, get):
        checkpoint = SimpleNamespace(
            lat=41.88,
            lon=-87.63,
            eta=datetime.now(timezone.utc) + timedelta(days=16),
        )

        with self.assertRaisesRegex(WeatherError, "15 days"):
            weather_at_checkpoints([checkpoint])

        get.assert_not_called()

    @patch("routing.services.weather.requests.get")
    def test_rejects_eta_before_yesterday(self, get):
        checkpoint = SimpleNamespace(
            lat=41.88,
            lon=-87.63,
            eta=datetime.now(timezone.utc) - timedelta(days=2),
        )

        with self.assertRaisesRegex(WeatherError, "yesterday"):
            weather_at_checkpoints([checkpoint])

        get.assert_not_called()

    @patch("routing.services.weather.requests.get")
    def test_fetch_results_are_cached(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = self.hourly_payload(
            ["2026-11-03T10:00"]
        )

        first = fetch_hourly([(41.88, -87.63)], self.start, self.end)
        second = fetch_hourly([(41.88, -87.63)], self.start, self.end)

        self.assertEqual(first, second)
        self.assertEqual(get.call_count, 1)
