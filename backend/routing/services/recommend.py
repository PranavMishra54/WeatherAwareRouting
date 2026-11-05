def _value(value, key):
    if isinstance(value, dict):
        return value[key]
    return getattr(value, key)


def _summary(route):
    return _value(route, "summary")


def _metric(route, name):
    return _value(_summary(route), name)


def _format_number(value):
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _route_id(route, fallback):
    if isinstance(route, dict):
        return route.get("id", fallback)
    return getattr(route, "id", fallback)


def _duration_seconds(route):
    return _value(route, "duration_seconds")


def rank_routes(analyzed_routes):
    routes = list(analyzed_routes)
    return [
        route
        for _, route in sorted(
            enumerate(routes),
            key=lambda indexed: (
                _metric(indexed[1], "no_travel_miles"),
                _metric(indexed[1], "severe_miles"),
                _metric(indexed[1], "high_miles"),
                _metric(indexed[1], "avg_risk"),
                _duration_seconds(indexed[1]),
                _route_id(indexed[1], indexed[0]),
            ),
        )
    ]


def build_reason(best, others):
    others = list(others)
    if not others:
        return "Only one route available."

    criteria = [
        ("no_travel_miles", "Fewest no-travel miles"),
        ("severe_miles", "Fewest severe miles"),
        ("high_miles", "Fewest high-risk miles"),
        ("avg_risk", "Lowest average risk"),
    ]
    best_no_travel = _metric(best, "no_travel_miles")
    if best_no_travel > 0 and all(
        _metric(route, "no_travel_miles") > 0 for route in others
    ):
        return (
            "All routes cross no-travel conditions; this one has the fewest "
            "no-travel miles."
        )

    for metric, label in criteria:
        best_value = _metric(best, metric)
        if any(_metric(route, metric) != best_value for route in others):
            comparisons = " and ".join(
                _format_number(_metric(route, metric)) for route in others
            )
            return f"{label}: {_format_number(best_value)} vs {comparisons} on the other routes."

    if any(_duration_seconds(route) != _duration_seconds(best) for route in others):
        return "Same weather risk on all routes; this is the fastest."
    return "Weather risk and travel time are the same on all routes."


def compare_reason(route, best):
    differences = []
    for metric, label in (
        ("no_travel_miles", "no-travel miles"),
        ("severe_miles", "severe miles"),
        ("high_miles", "high-risk miles"),
    ):
        delta = _metric(route, metric) - _metric(best, metric)
        if delta > 0:
            differences.append(f"+{_format_number(delta)} {label}")

    avg_delta = _metric(route, "avg_risk") - _metric(best, "avg_risk")
    if avg_delta > 0:
        differences.append(f"+{_format_number(avg_delta)} average risk")

    duration_delta = _duration_seconds(route) - _duration_seconds(best)
    if duration_delta > 0:
        differences.append(f"+{duration_delta / 3600:.1f} h")

    if not differences:
        return "Same risk and travel time as the recommended route."
    return f"{', '.join(differences)} vs recommended."