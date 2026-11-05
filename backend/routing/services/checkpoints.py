from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt


EARTH_RADIUS_MILES = 3958.7613
SUPPORTED_INTERVALS = {10, 25, 50}


@dataclass
class Checkpoint:
    mile: float
    lat: float
    lon: float
    eta: datetime
    segment_miles: float


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)

    lat_delta = lat2 - lat1
    lon_delta = lon2 - lon1
    haversine = (
        sin(lat_delta / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(lon_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * asin(sqrt(min(1.0, haversine)))


def interpolate_path(
    path: list[tuple[float, float]],
    cumulative_miles: list[float],
    target_mile: float,
) -> tuple[float, float]:
    if target_mile <= 0:
        return path[0]
    if target_mile >= cumulative_miles[-1]:
        return path[-1]

    for index in range(1, len(cumulative_miles)):
        end_mile = cumulative_miles[index]
        if target_mile <= end_mile:
            start_mile = cumulative_miles[index - 1]
            segment_length = end_mile - start_mile
            if segment_length == 0:
                continue
            fraction = (target_mile - start_mile) / segment_length
            start_lat, start_lon = path[index - 1]
            end_lat, end_lon = path[index]
            return (
                start_lat + fraction * (end_lat - start_lat),
                start_lon + fraction * (end_lon - start_lon),
            )

    return path[-1]


def build_checkpoints(
    path: list[tuple[float, float]],
    duration_seconds: float,
    departure_time: datetime,
    interval_miles: int,
) -> list[Checkpoint]:
    if interval_miles not in SUPPORTED_INTERVALS:
        raise ValueError("interval_miles must be 10, 25, or 50")
    if len(path) < 2:
        raise ValueError("path must contain at least two points")

    cumulative_miles = [0.0]
    for start, end in zip(path, path[1:]):
        cumulative_miles.append(
            cumulative_miles[-1] + haversine_miles(start, end)
        )
    total_miles = cumulative_miles[-1]

    targets = [0.0]
    target_mile = float(interval_miles)
    while target_mile < total_miles:
        targets.append(target_mile)
        target_mile += interval_miles

    if total_miles > 0:
        targets.append(total_miles)

    points = []
    for target in targets:
        points.append(interpolate_path(path, cumulative_miles, target))

    checkpoints = []
    for index, (mile, (lat, lon)) in enumerate(zip(targets, points)):
        previous_half = (
            (mile - targets[index - 1]) / 2 if index > 0 else 0.0
        )
        next_half = (
            (targets[index + 1] - mile) / 2
            if index + 1 < len(targets)
            else 0.0
        )
        if total_miles > 0:
            eta = departure_time + timedelta(
                seconds=duration_seconds * (mile / total_miles)
            )
        else:
            eta = departure_time
        checkpoints.append(
            Checkpoint(
                mile=mile,
                lat=lat,
                lon=lon,
                eta=eta,
                segment_miles=previous_half + next_half,
            )
        )

    return checkpoints