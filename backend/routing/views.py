import logging

from django.conf import settings
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import AnalyzeRequestSerializer
from .services.analyze import analyze_trip
from .services.routing import RoutingError, geocode, get_routes
from .services.weather import WeatherError


logger = logging.getLogger(__name__)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def routes_preview(request):
    if not settings.DEBUG:
        raise Http404

    origin = request.query_params.get("origin")
    destination = request.query_params.get("destination")
    if not origin or not destination:
        return Response({"error": "origin and destination are required"}, status=400)

    try:
        o = geocode(origin)
        d = geocode(destination)
        routes = get_routes(o, d)
    except RoutingError as e:
        return Response({"error": str(e)}, status=e.status_code)

    return Response([
        {
            "id": r.id,
            "distance_miles": round(r.distance_miles, 1),
            "duration_hours": round(r.duration_seconds / 3600, 2),
            "points": len(r.path),
        }
        for r in routes
    ])


def _first_validation_message(errors):
    if isinstance(errors, dict):
        for value in errors.values():
            message = _first_validation_message(value)
            if message:
                return message
    elif isinstance(errors, (list, tuple)):
        for value in errors:
            message = _first_validation_message(value)
            if message:
                return message
    else:
        return str(errors)
    return "Invalid request"


@api_view(["POST"])
def analyze(request):
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                "error": _first_validation_message(serializer.errors),
                "fields": serializer.errors,
            },
            status=400,
        )

    try:
        data = serializer.validated_data
        result = analyze_trip(
            data["origin"],
            data["destination"],
            data["departure_time"],
            data["load_weight_lb"],
            data["interval_miles"],
        )
    except WeatherError as error:
        return Response({"error": str(error)}, status=502)
    except (RoutingError, ValueError) as error:
        return Response({"error": str(error)}, status=400)
    except Exception:
        logger.exception("Unexpected error while analyzing trip")
        return Response({"error": "Something went wrong"}, status=500)

    return Response(result)