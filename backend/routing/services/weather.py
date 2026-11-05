from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from django.core.cache import cache

from .checkpoints import Checkpoint


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 30 * 60
MAX_POINTS_PER_REQUEST = 50
REQUEST_TIMEOUT_SECONDS = 20


class WeatherError(Exception):
    pass


@dataclass
class HourlyWeather:
    time: datetime
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass
class WeatherPoint:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float
    forecast_time: datetime


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _cache_key(
    point: tuple[float, float], start_date: str, end_date: str
) -> str:
    return f"routing:open_meteo:{point[0]:.2f}:{point[1]:.2f}:{start_date}:{end_date}"


def _parse_hourly_response(data: Any) -> list[HourlyWeather]:
    if not isinstance(data, dict):
        raise WeatherError("Open-Meteo returned an invalid response")
    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherError("Open-Meteo response is missing hourly forecast data")

    try:
        times = hourly["time"]
        winds = hourly["wind_speed_10m"]
        rain = hourly["rain"]
        showers = hourly["showers"]
        snowfall = hourly["snowfall"]
        if not all(
            isinstance(values, list)
            for values in (times, winds, rain, showers, snowfall)
        ):
            raise TypeError
        if not (len(times) == len(winds) == len(rain) == len(showers) == len(snowfall)):
            raise ValueError

        result = []
        for timestamp, wind, rain_amount, shower_amount, snow in zip(
            times, winds, rain, showers, snowfall
        ):
            forecast_time = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
            result.append(
                HourlyWeather(
                    time=_as_utc(forecast_time),
                    wind_mph=float(wind or 0),
                    rain_in_hr=float(rain_amount or 0) + float(shower_amount or 0),
                    snow_in_hr=float(snow or 0),
                )
            )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise WeatherError("Open-Meteo returned malformed hourly forecast data") from error

    return result


def _fetch_chunk(
    points: list[tuple[float, float]], start_date: str, end_date: str
) -> list[list[HourlyWeather]]:
    params = {
        "latitude": ",".join(f"{latitude:.2f}" for latitude, _ in points),
        "longitude": ",".join(f"{longitude:.2f}" for _, longitude in points),
        "hourly": "wind_speed_10m,rain,showers,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
        "start_date": start_date,
        "end_date": end_date,
    }

    for attempt in range(2):
        try:
            response = requests.get(
                OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as error:
            if attempt == 0:
                continue
            raise WeatherError(
                f"Open-Meteo request failed after one retry: {error}"
            ) from error

        if response.status_code >= 500:
            if attempt == 0:
                continue
            raise WeatherError(
                f"Open-Meteo returned HTTP {response.status_code} after one retry"
            )
        if response.status_code >= 400:
            raise WeatherError(f"Open-Meteo returned HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as error:
            raise WeatherError("Open-Meteo returned invalid JSON") from error

        if len(points) == 1 and isinstance(data, dict):
            payloads = [data]
        elif isinstance(data, list) and len(data) == len(points):
            payloads = data
        else:
            raise WeatherError("Open-Meteo response did not match requested locations")

        return [_parse_hourly_response(payload) for payload in payloads]

    raise WeatherError("Open-Meteo request failed")


def fetch_hourly(
    points: list[tuple[float, float]], start: datetime, end: datetime
) -> list[list[HourlyWeather]]:
    start_utc = _as_utc(start)
    end_utc = _as_utc(end)
    if end_utc < start_utc:
        raise WeatherError("Forecast end must not be before forecast start")

    start_date = start_utc.date().isoformat()
    end_date = end_utc.date().isoformat()
    rounded_points = [(round(lat, 2), round(lon, 2)) for lat, lon in points]
    unique_points = list(dict.fromkeys(rounded_points))
    cached: dict[tuple[float, float], list[HourlyWeather]] = {}
    missing = []

    for point in unique_points:
        key = _cache_key(point, start_date, end_date)
        result = cache.get(key)
        if result is None:
            missing.append(point)
        else:
            cached[point] = result

    for offset in range(0, len(missing), MAX_POINTS_PER_REQUEST):
        chunk = missing[offset : offset + MAX_POINTS_PER_REQUEST]
        forecasts = _fetch_chunk(chunk, start_date, end_date)
        for point, forecast in zip(chunk, forecasts):
            cached[point] = forecast
            cache.set(
                _cache_key(point, start_date, end_date),
                forecast,
                CACHE_TTL_SECONDS,
            )

    return [cached[point] for point in rounded_points]


def weather_at_checkpoints(checkpoints: list[Checkpoint]) -> list[WeatherPoint]:
    if not checkpoints:
        return []

    etas = [_as_utc(checkpoint.eta) for checkpoint in checkpoints]
    now = datetime.now(timezone.utc)
    today = now.date()
    for eta in etas:
        if eta > now + timedelta(days=15):
            raise WeatherError("Forecast is limited to 15 days ahead")
        if eta.date() < today - timedelta(days=1):
            raise WeatherError("Historical forecast is limited to yesterday")

    start = min(etas).replace(minute=0, second=0, microsecond=0)
    latest = max(etas)
    end = latest.replace(minute=0, second=0, microsecond=0)
    if latest.minute or latest.second or latest.microsecond:
        end += timedelta(hours=1)

    forecasts = fetch_hourly(
        [(checkpoint.lat, checkpoint.lon) for checkpoint in checkpoints],
        start,
        end,
    )
    result = []
    for eta, hourly_values in zip(etas, forecasts):
        if not hourly_values:
            raise WeatherError("Open-Meteo returned no hourly forecast values")
        nearest = min(
            hourly_values,
            key=lambda value: abs((value.time - eta).total_seconds()),
        )
        result.append(
            WeatherPoint(
                wind_mph=nearest.wind_mph,
                rain_in_hr=nearest.rain_in_hr,
                snow_in_hr=nearest.snow_in_hr,
                forecast_time=nearest.time,
            )
        )
    return result