from datetime import datetime, timezone
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

from django.test import SimpleTestCase

from routing.services.routing import Route
from routing.services.weather import WeatherError, WeatherPoint


class AnalyzeViewTests(SimpleTestCase):
    def setUp(self):
        self.departure_time = datetime(2026, 11, 3, 8, tzinfo=timezone.utc)
        self.path_a = [(41.8781, -87.6298), (32.7767, -96.7970)]
        self.path_b = [(41.8781, -87.6298), (34.0, -94.0), (32.7767, -96.7970)]
        self.routes = [
            Route(0, 800, 36000, self.path_a),
            Route(1, 820, 39000, self.path_b),
        ]

    def _post(self, **overrides):
        payload = {
            "origin": "Chicago, IL",
            "destination": "Dallas, TX",
            "departure_time": self.departure_time.isoformat(),
            "load_weight_lb": 42000,
            "interval_miles": 25,
        }
        payload.update(overrides)
        return self.client.post("/api/analyze/", data=payload, content_type="application/json")

    def _patch_services(self, wind_mph=20):
        @contextmanager
        def patched():
            with ExitStack() as stack:
                geocode = stack.enter_context(
                    patch(
                        "routing.services.analyze.geocode",
                        side_effect=[(41.8, -87.6), (32.7, -96.8)],
                    )
                )
                get_routes = stack.enter_context(
                    patch("routing.services.analyze.get_routes", return_value=self.routes)
                )
                weather = stack.enter_context(
                    patch(
                        "routing.services.analyze.weather_at_checkpoints",
                        side_effect=lambda checkpoints: [
                            WeatherPoint(wind_mph, 0, 0, checkpoint.eta)
                            for checkpoint in checkpoints
                        ],
                    )
                )
                heatmap = stack.enter_context(
                    patch(
                        "routing.services.analyze.build_heatmap",
                        return_value={
                            "hours": [0],
                            "frames": [[]],
                            "start_time": "2026-11-03T08:00:00Z",
                        },
                    )
                )
                yield geocode, get_routes, weather, heatmap

        return patched()

    def test_valid_request_returns_expected_shape_and_recommended_route(self):
        with self._patch_services() as (geocode, get_routes, weather, heatmap):
            response = self._post()

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(set(data), {"recommended_route_id", "routes", "heatmap"})
        self.assertIn(data["recommended_route_id"], [route["id"] for route in data["routes"]])
        self.assertEqual([route["id"] for route in data["routes"]], [0, 1])
        self.assertEqual(set(data["heatmap"]), {"hours", "frames", "start_time"})
        self.assertEqual(data["heatmap"]["hours"], [0])
        self.assertEqual(len(data["routes"]), 2)
        route = data["routes"][0]
        self.assertEqual(
            set(route),
            {
                "id",
                "distance_miles",
                "duration_hours",
                "arrival_time",
                "path",
                "summary",
                "recommendation_reason",
                "checkpoints",
            },
        )
        self.assertEqual(
            set(route["summary"]),
            {
                "no_travel_miles",
                "severe_miles",
                "high_miles",
                "moderate_miles",
                "low_miles",
                "avg_risk",
                "max_risk",
            },
        )
        self.assertTrue(route["arrival_time"].endswith("Z"))
        self.assertEqual(
            set(route["checkpoints"][0]),
            {
                "mile",
                "lat",
                "lon",
                "eta",
                "forecast_time",
                "wind_mph",
                "rain_in_hr",
                "snow_in_hr",
                "risk",
                "reasons",
            },
        )
        self.assertEqual(route["checkpoints"][0]["forecast_time"], route["checkpoints"][0]["eta"])
        geocode.assert_any_call("Chicago, IL")
        geocode.assert_any_call("Dallas, TX")
        get_routes.assert_called_once_with((41.8, -87.6), (32.7, -96.8), count=3)
        weather.assert_called_once()
        heatmap.assert_called_once()

    def test_heavy_load_and_41_mph_wind_raise_checkpoint_risk_to_severe(self):
        with self._patch_services(wind_mph=41):
            response = self._post(load_weight_lb=45000)

        self.assertEqual(response.status_code, 200, response.content)
        for route in response.json()["routes"]:
            self.assertTrue(route["checkpoints"])
            self.assertTrue(all(point["risk"] == "severe" for point in route["checkpoints"]))
            self.assertTrue(
                all(
                    any("raised to severe" in reason for reason in point["reasons"])
                    for point in route["checkpoints"]
                )
            )

    def test_interval_50_produces_fewer_checkpoints_than_interval_10(self):
        with self._patch_services():
            response_10 = self._post(interval_miles=10)
        with self._patch_services():
            response_50 = self._post(interval_miles=50)

        self.assertEqual(response_10.status_code, 200)
        self.assertEqual(response_50.status_code, 200)
        counts_10 = [len(route["checkpoints"]) for route in response_10.json()["routes"]]
        counts_50 = [len(route["checkpoints"]) for route in response_50.json()["routes"]]
        self.assertTrue(all(fewer < more for fewer, more in zip(counts_50, counts_10)))

    def test_invalid_load_weight_returns_400(self):
        response = self._post(load_weight_lb=0)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertIn("fields", response.json())

    def test_same_origin_and_destination_returns_400(self):
        response = self._post(destination="chicago, il")

        self.assertEqual(response.status_code, 400)
        self.assertIn("different", response.json()["error"])
        self.assertIn("fields", response.json())

    @patch("routing.services.analyze.geocode", side_effect=[(41.8, -87.6), (32.7, -96.8)])
    @patch("routing.services.analyze.get_routes", return_value=[])
    @patch(
        "routing.services.analyze.weather_at_checkpoints",
        side_effect=WeatherError("Forecast unavailable"),
    )
    def test_weather_error_returns_502(self, weather, get_routes, geocode):
        response = self._post()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"error": "Forecast unavailable"})

    @patch("routing.services.analyze.geocode", side_effect=[(41.8, -87.6), (32.7, -96.8)])
    @patch("routing.services.analyze.get_routes")
    @patch(
        "routing.services.analyze.weather_at_checkpoints",
        side_effect=lambda checkpoints: [
            WeatherPoint(20, 0, 0, checkpoint.eta) for checkpoint in checkpoints
        ],
    )
    @patch(
        "routing.services.analyze.build_heatmap",
        side_effect=WeatherError("Heatmap unavailable"),
    )
    def test_heatmap_weather_error_does_not_fail_analysis(
        self, heatmap, weather, get_routes, geocode
    ):
        get_routes.return_value = self.routes

        response = self._post()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json()["heatmap"],
            {"hours": [], "frames": [], "start_time": None},
        )
