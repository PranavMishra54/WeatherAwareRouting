import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from types import SimpleNamespace

from .checkpoints import build_checkpoints
from .geo import simplify_path
from .heatmap import build_heatmap
from .recommend import build_reason, compare_reason, rank_routes
from .risk import assess_checkpoint, summarize_route
from .routing import geocode, get_routes
from .weather import WeatherError, weather_at_checkpoints


logger = logging.getLogger(__name__)


def _log_stage(stage, started):
    logger.info(
        "analyze_trip stage=%s duration_seconds=%.3f",
        stage,
        time.perf_counter() - started,
    )


def _timed_stage(stage, function, *args):
    started = time.perf_counter()
    try:
        return function(*args)
    finally:
        _log_stage(stage, started)


def _iso_utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _summary_data(summary):
    return {
        "no_travel_miles": summary.no_travel_miles,
        "severe_miles": summary.severe_miles,
        "high_miles": summary.high_miles,
        "moderate_miles": summary.moderate_miles,
        "low_miles": summary.low_miles,
        "avg_risk": summary.avg_risk,
        "max_risk": summary.max_risk.label,
    }


def analyze_trip(
    origin_text,
    destination_text,
    departure_time,
    load_weight_lb,
    interval_miles,
):
    started = time.perf_counter()
    origin = geocode(origin_text)
    destination = geocode(destination_text)
    routes = get_routes(origin, destination, count=3)
    _log_stage("routes", started)

    started = time.perf_counter()
    checkpoints_by_route = [
        build_checkpoints(
            route.path,
            route.duration_seconds,
            departure_time,
            interval_miles,
        )
        for route in routes
    ]
    _log_stage("checkpoints", started)

    all_checkpoints = [
        checkpoint
        for checkpoints in checkpoints_by_route
        for checkpoint in checkpoints
    ]
    full_paths = [route.path for route in routes]
    with ThreadPoolExecutor(max_workers=2) as executor:
        weather_future = executor.submit(
            _timed_stage, "weather", weather_at_checkpoints, all_checkpoints
        )
        heatmap_future = executor.submit(
            _timed_stage, "heatmap", build_heatmap, full_paths, departure_time
        )
        weather_points = weather_future.result()
        try:
            heatmap = heatmap_future.result()
        except WeatherError as error:
            logger.warning("Heatmap forecast unavailable: %s", error)
            heatmap = {"hours": [], "frames": [], "start_time": None}
        except Exception:
            logger.exception("Heatmap generation failed")
            heatmap = {"hours": [], "frames": [], "start_time": None}
    if len(weather_points) != len(all_checkpoints):
        raise ValueError("Weather results did not match the route checkpoints")

    started = time.perf_counter()
    analyzed_routes = []
    weather_offset = 0
    for route, checkpoints in zip(routes, checkpoints_by_route):
        weather_for_route = weather_points[
            weather_offset : weather_offset + len(checkpoints)
        ]
        weather_offset += len(checkpoints)
        assessments = [
            assess_checkpoint(
                weather.wind_mph,
                weather.rain_in_hr,
                weather.snow_in_hr,
                load_weight_lb,
            )
            for weather in weather_for_route
        ]
        risk_checkpoints = [
            SimpleNamespace(
                level=assessment.level,
                segment_miles=checkpoint.segment_miles,
            )
            for checkpoint, assessment in zip(checkpoints, assessments)
        ]
        summary = summarize_route(risk_checkpoints)
        analyzed_routes.append(
            {
                "id": route.id,
                "duration_seconds": route.duration_seconds,
                "route": route,
                "checkpoints": checkpoints,
                "weather": weather_for_route,
                "assessments": assessments,
                "summary": summary,
            }
        )

    ranked = rank_routes(analyzed_routes)
    recommended = ranked[0]
    recommended["recommendation_reason"] = build_reason(recommended, ranked[1:])
    for analyzed in ranked[1:]:
        analyzed["recommendation_reason"] = compare_reason(analyzed, recommended)
    _log_stage("risk", started)

    output_routes = []
    for analyzed in sorted(analyzed_routes, key=lambda route: route["id"]):
        route = analyzed["route"]
        output_routes.append(
            {
                "id": route.id,
                "distance_miles": round(route.distance_miles, 1),
                "duration_hours": round(route.duration_seconds / 3600, 2),
                "arrival_time": _iso_utc(
                    analyzed["checkpoints"][-1].eta
                ),
                "path": [
                    [lat, lon]
                    for lat, lon in simplify_path(route.path)
                ],
                "summary": _summary_data(analyzed["summary"]),
                "recommendation_reason": analyzed["recommendation_reason"],
                "checkpoints": [
                    {
                        "mile": checkpoint.mile,
                        "lat": checkpoint.lat,
                        "lon": checkpoint.lon,
                        "eta": _iso_utc(checkpoint.eta),
                        "forecast_time": _iso_utc(weather.forecast_time),
                        "wind_mph": weather.wind_mph,
                        "rain_in_hr": weather.rain_in_hr,
                        "snow_in_hr": weather.snow_in_hr,
                        "risk": assessment.level.label,
                        "reasons": assessment.reasons,
                    }
                    for checkpoint, weather, assessment in zip(
                        analyzed["checkpoints"],
                        analyzed["weather"],
                        analyzed["assessments"],
                    )
                ],
            }
        )

    return {
        "recommended_route_id": recommended["id"],
        "routes": output_routes,
        "heatmap": heatmap,
    }
