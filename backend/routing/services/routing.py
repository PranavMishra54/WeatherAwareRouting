import math
import os
from dataclasses import dataclass
from urllib.parse import quote

import polyline
import requests

MAPBOX_BASE = "https://api.mapbox.com"
GEOCODING_BASE = f"{MAPBOX_BASE}/geocoding/v5/mapbox.places"
DIRECTIONS_BASE = f"{MAPBOX_BASE}/directions/v5/mapbox/driving"
METERS_PER_MILE = 1609.344
TIMEOUT = 10
ROUTING_TIMEOUT = 20
MIN_GEOCODING_RELEVANCE = 0.8


class RoutingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Route:
    id: int
    distance_miles: float
    duration_seconds: float
    path: list[tuple[float, float]]


def _token() -> str:
    token = os.getenv("MAPBOX_TOKEN", "").strip()
    if not token:
        raise RoutingError("MAPBOX_TOKEN is not configured", status_code=503)
    return token


def _get_json(url: str, params: dict, service: str, timeout: int = TIMEOUT) -> dict:
    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise RoutingError(f"{service} service is unavailable", status_code=502) from exc

    if response.status_code != 200:
        raise RoutingError(f"{service} failed ({response.status_code})", status_code=502)

    try:
        data = response.json()
    except ValueError as exc:
        raise RoutingError(f"{service} returned an invalid response", status_code=502) from exc
    if not isinstance(data, dict):
        raise RoutingError(f"{service} returned an invalid response", status_code=502)
    return data


def geocode(address: str) -> tuple[float, float]:
    """Resolve an address to a (latitude, longitude) pair using Mapbox."""
    address = address.strip()
    if not address:
        raise RoutingError("Locations cannot be blank")

    data = _get_json(
        f"{GEOCODING_BASE}/{quote(address, safe='')}.json",
        {"access_token": _token(), "limit": 1, "fuzzyMatch": "false"},
        "Geocoding",
    )
    features = data.get("features")
    if not isinstance(features, list):
        raise RoutingError("Geocoding returned an invalid response", status_code=502)
    if not features:
        raise RoutingError(f"Location not found: {address}")

    try:
        feature = features[0]
        relevance = feature["relevance"]
        coordinates = feature["geometry"]["coordinates"]
        longitude, latitude = coordinates
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise RoutingError("Geocoding returned an invalid response", status_code=502) from exc
    if (
        isinstance(relevance, bool)
        or not isinstance(relevance, (int, float))
        or not math.isfinite(relevance)
    ):
        raise RoutingError("Geocoding returned an invalid response", status_code=502)
    if relevance < MIN_GEOCODING_RELEVANCE:
        raise RoutingError(f"Location not found: {address}")
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise RoutingError("Geocoding returned invalid coordinates", status_code=502)
    return latitude, longitude


def get_routes(
    origin: tuple[float, float],
    destination: tuple[float, float],
    count: int = 3,
) -> list[Route]:
    """Fetch distinct routes, using waypoint corridors if alternatives are scarce."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise RoutingError("Route count must be a positive integer")

    token = _token()
    routes = []
    geometries = set()
    for waypoint in [None, *_waypoint_candidates(origin, destination)]:
        if len(routes) >= count:
            break
        coordinates = [origin, destination] if waypoint is None else [origin, waypoint, destination]
        coords = ";".join(f"{longitude},{latitude}" for latitude, longitude in coordinates)
        params = {
            "alternatives": "true" if waypoint is None else "false",
            "geometries": "polyline",
            "overview": "full",
            "access_token": token,
        }
        data = _get_json(
            f"{DIRECTIONS_BASE}/{coords}",
            params,
            "Routing",
            timeout=ROUTING_TIMEOUT,
        )
        provider_routes = data.get("routes")
        if not isinstance(provider_routes, list):
            raise RoutingError("Routing returned an invalid response", status_code=502)
        try:
            for route in provider_routes:
                distance = route["distance"]
                duration = route["duration"]
                geometry = route["geometry"]
                if (
                    isinstance(distance, bool)
                    or isinstance(duration, bool)
                    or not isinstance(distance, (int, float))
                    or not isinstance(duration, (int, float))
                    or not math.isfinite(distance)
                    or not math.isfinite(duration)
                    or distance < 0
                    or duration < 0
                    or not isinstance(geometry, str)
                ):
                    raise ValueError
                if geometry in geometries:
                    continue
                path = polyline.decode(geometry)
                if len(path) < 2:
                    raise ValueError
                geometries.add(geometry)
                routes.append(
                    Route(
                        id=len(routes),
                        distance_miles=distance / METERS_PER_MILE,
                        duration_seconds=duration,
                        path=path,
                    )
                )
                if len(routes) >= count:
                    break
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise RoutingError("Routing returned invalid route data", status_code=502) from exc
    if not routes:
        raise RoutingError("No routes found")
    if len(routes) < count:
        route_word = "route" if len(routes) == 1 else "routes"
        raise RoutingError(
            f"Routing found only {len(routes)} distinct {route_word}; "
            f"{count} are required",
            status_code=502,
        )
    return routes


def _waypoint_candidates(
    origin: tuple[float, float], destination: tuple[float, float]
) -> list[tuple[float, float]]:
    origin_lat, origin_lon = origin
    destination_lat, destination_lon = destination
    midpoint_lat = (origin_lat + destination_lat) / 2
    midpoint_lon = (origin_lon + destination_lon) / 2
    east_west_miles = (destination_lon - origin_lon) * 69.0 * math.cos(
        math.radians(midpoint_lat)
    )
    north_south_miles = (destination_lat - origin_lat) * 69.0
    distance_miles = math.hypot(east_west_miles, north_south_miles)
    if distance_miles == 0:
        return []
    offset_miles = min(90.0, max(30.0, distance_miles * 0.08))
    perpendicular_lat = -east_west_miles / distance_miles
    perpendicular_lon = north_south_miles / distance_miles
    longitude_scale = 69.0 * math.cos(math.radians(midpoint_lat))
    if abs(longitude_scale) < 1e-6:
        return []
    candidates = []
    for direction in (1, -1):
        candidates.append(
            (
                midpoint_lat + direction * offset_miles * perpendicular_lat / 69.0,
                midpoint_lon + direction * offset_miles * perpendicular_lon / longitude_scale,
            )
        )
    return candidates
