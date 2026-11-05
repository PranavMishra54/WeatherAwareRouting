from datetime import datetime, timedelta, timezone

from .checkpoints import haversine_miles, interpolate_path
from .weather import fetch_hourly


def _rounded(point):
    return round(point[0], 2), round(point[1], 2)


def sample_corridor(
    paths: list[list[tuple[float, float]]],
    spacing_miles: float = 20,
    max_points: int = 120,
) -> list[tuple[float, float]]:
    if spacing_miles <= 0:
        raise ValueError("spacing_miles must be greater than zero")
    if max_points < 2:
        raise ValueError("max_points must be at least 2")

    route_data = []
    for path in paths:
        if len(path) < 2:
            continue
        cumulative_miles = [0.0]
        for start, end in zip(path, path[1:]):
            cumulative_miles.append(
                cumulative_miles[-1] + haversine_miles(start, end)
            )
        route_data.append((path, cumulative_miles))

    if not route_data:
        return []

    spacing = spacing_miles
    while True:
        points = []
        seen = set()
        for path, cumulative_miles in route_data:
            total_miles = cumulative_miles[-1]
            targets = [0.0]
            target = spacing
            while target < total_miles:
                targets.append(target)
                target += spacing
            if total_miles > 0:
                targets.append(total_miles)
            else:
                targets.append(0.0)
            for target in targets:
                point = _rounded(
                    interpolate_path(path, cumulative_miles, target)
                )
                if point not in seen:
                    points.append(point)
                    seen.add(point)
        if len(points) <= max_points:
            return points
        spacing *= 2


def weather_intensity(wind_mph, rain_in_hr, snow_in_hr) -> float:
    intensity = max(
        wind_mph / 55,
        rain_in_hr / 1.0,
        snow_in_hr / 3.0,
    )
    return round(max(0.0, min(1.0, intensity)), 2)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_heatmap(
    paths: list[list[tuple[float, float]]],
    departure_time: datetime,
    hours: int = 48,
) -> dict:
    start = _as_utc(departure_time).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    points = sample_corridor(paths)
    if not points:
        return {
            "hours": list(range(hours + 1)),
            "frames": [[] for _ in range(hours + 1)],
            "start_time": start.isoformat().replace("+00:00", "Z"),
        }

    forecasts = fetch_hourly(points, start, end)
    if len(forecasts) != len(points):
        raise ValueError("Weather results did not match corridor points")

    frames = []
    for hour in range(hours + 1):
        frame_time = start + timedelta(hours=hour)
        all_values = []
        for (lat, lon), hourly_values in zip(points, forecasts):
            weather = next(
                (value for value in hourly_values if _as_utc(value.time) == frame_time),
                None,
            )
            intensity = (
                weather_intensity(
                    weather.wind_mph,
                    weather.rain_in_hr,
                    weather.snow_in_hr,
                )
                if weather is not None
                else 0.0
            )
            all_values.append([round(lat, 3), round(lon, 3), intensity])

        frame = [point for point in all_values if point[2] >= 0.03]
        if not frame and all_values:
            frame = [max(all_values, key=lambda point: point[2])]
        frames.append(frame)

    return {
        "hours": list(range(hours + 1)),
        "frames": frames,
        "start_time": start.isoformat().replace("+00:00", "Z"),
    }
