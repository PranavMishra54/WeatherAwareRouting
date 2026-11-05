from types import SimpleNamespace
from unittest.mock import patch

import polyline
import requests
from django.test import TestCase, override_settings

from routing.services.routing import (
    METERS_PER_MILE,
    RoutingError,
    geocode,
    get_routes,
)


class RoutingServiceTests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(DEBUG=False)
    def test_routes_preview_is_disabled_outside_debug(self):
        response = self.client.get("/api/routes-preview/")

        self.assertEqual(response.status_code, 404)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_geocode_returns_latitude_longitude(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {
            "features": [
                {
                    "geometry": {"coordinates": [-122.4, 37.8]},
                    "relevance": 1,
                    "place_name": "San Francisco, California, United States",
                }
            ]
        }

        self.assertEqual(geocode("San Francisco"), (37.8, -122.4))
        self.assertIn("San%20Francisco.json", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["params"]["fuzzyMatch"], "false")

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_geocode_rejects_missing_result(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {"features": []}

        with self.assertRaisesRegex(RoutingError, "Location not found"):
            geocode("Nowhere")

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_geocode_rejects_low_relevance_match(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {
            "features": [
                {
                    "geometry": {"coordinates": [-73.6, 45.6]},
                    "relevance": 0.57,
                    "place_name": "8842 Place Ray Lawson, Anjou, Quebec, Canada",
                }
            ]
        }

        with self.assertRaisesRegex(RoutingError, "Location not found"):
            geocode("Qzxv Nonexistent Place 8842")

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_geocode_translates_network_errors(self, get):
        get.side_effect = requests.Timeout()

        with self.assertRaisesRegex(RoutingError, "service is unavailable") as error:
            geocode("San Francisco")

        self.assertEqual(error.exception.status_code, 502)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_geocode_rejects_invalid_json(self, get):
        get.return_value.status_code = 200
        get.return_value.json.side_effect = ValueError("invalid JSON")

        with self.assertRaisesRegex(RoutingError, "invalid response") as error:
            geocode("San Francisco")

        self.assertEqual(error.exception.status_code, 502)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_get_routes_converts_distance_and_decodes_geometry(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {
            "routes": [
                {
                    "distance": METERS_PER_MILE,
                    "duration": 3600,
                    "geometry": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
                }
            ]
        }

        routes = get_routes((38.5, -120.2), (40.7, -120.95), count=1)

        self.assertEqual(len(routes), 1)
        self.assertAlmostEqual(routes[0].distance_miles, 1)
        self.assertEqual(routes[0].duration_seconds, 3600)
        self.assertEqual(len(routes[0].path), 3)
        self.assertEqual(get.call_args.kwargs["timeout"], 20)
        self.assertEqual(
            get.call_args.kwargs["params"],
            {
                "alternatives": "true",
                "geometries": "polyline",
                "overview": "full",
                "access_token": "test-token",
            },
        )

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_get_routes_fills_missing_alternatives_with_waypoint_routes(self, get):
        direct_routes = [
            {
                "distance": METERS_PER_MILE * 800,
                "duration": 3600,
                "geometry": polyline.encode([(38.5, -120.2), (40.7, -120.95)]),
            },
            {
                "distance": METERS_PER_MILE * 810,
                "duration": 3700,
                "geometry": polyline.encode(
                    [(38.5, -120.2), (39.0, -121.0), (40.7, -120.95)]
                ),
            },
        ]
        via_route = {
            "distance": METERS_PER_MILE * 820,
            "duration": 3800,
            "geometry": polyline.encode(
                [(38.5, -120.2), (39.5, -119.5), (40.7, -120.95)]
            ),
        }
        get.side_effect = [
            SimpleNamespace(status_code=200, json=lambda: {"routes": direct_routes}),
            SimpleNamespace(status_code=200, json=lambda: {"routes": [via_route]}),
        ]

        routes = get_routes((38.5, -120.2), (40.7, -120.95))

        self.assertEqual(len(routes), 3)
        self.assertEqual([route.id for route in routes], [0, 1, 2])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(len(get.call_args_list[1].args[0].rsplit("/", 1)[1].split(";")), 3)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_get_routes_errors_when_three_distinct_routes_are_unavailable(self, get):
        route = {
            "distance": METERS_PER_MILE,
            "duration": 3600,
            "geometry": polyline.encode([(38.5, -120.2), (40.7, -120.95)]),
        }
        get.return_value.status_code = 200
        get.return_value.json.return_value = {"routes": [route]}

        with self.assertRaisesRegex(RoutingError, "3 are required") as error:
            get_routes((38.5, -120.2), (40.7, -120.95))

        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(get.call_count, 3)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_get_routes_translates_provider_http_errors(self, get):
        get.return_value.status_code = 401

        with self.assertRaisesRegex(RoutingError, "Routing failed \\(401\\)") as error:
            get_routes((38.5, -120.2), (40.7, -120.95))

        self.assertEqual(error.exception.status_code, 502)

    @patch.dict("os.environ", {"MAPBOX_TOKEN": "test-token"})
    @patch("routing.services.routing.requests.get")
    def test_get_routes_rejects_malformed_provider_data(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {"routes": [{}]}

        with self.assertRaisesRegex(RoutingError, "invalid route data") as error:
            get_routes((38.5, -120.2), (40.7, -120.95))

        self.assertEqual(error.exception.status_code, 502)

    @patch("routing.views.geocode")
    @override_settings(DEBUG=True)
    def test_routes_preview_requires_both_locations_without_geocoding(self, geocode_mock):
        response = self.client.get("/api/routes-preview/?origin=Seattle")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "origin and destination are required"})
        geocode_mock.assert_not_called()

    @patch("routing.views.get_routes")
    @patch("routing.views.geocode")
    @override_settings(DEBUG=True)
    def test_routes_preview_returns_summary(self, geocode_mock, routes_mock):
        from routing.services.routing import Route

        geocode_mock.side_effect = [(47.6, -122.3), (45.5, -122.7)]
        routes_mock.return_value = [
            Route(0, 173.24, 5400, [(47.6, -122.3), (45.5, -122.7)])
        ]

        response = self.client.get(
            "/api/routes-preview/?origin=Seattle&destination=Portland"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"id": 0, "distance_miles": 173.2, "duration_hours": 1.5, "points": 2}],
        )

    @patch("routing.views.geocode")
    @override_settings(DEBUG=True)
    def test_routes_preview_returns_provider_error_status(self, geocode_mock):
        geocode_mock.side_effect = RoutingError(
            "Geocoding service is unavailable", status_code=502
        )

        response = self.client.get(
            "/api/routes-preview/?origin=Seattle&destination=Portland"
        )

        self.assertEqual(response.status_code, 502)
