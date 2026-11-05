from types import SimpleNamespace

from django.test import SimpleTestCase

from routing.services.recommend import build_reason, compare_reason, rank_routes


def make_route(route_id, *, no_travel=0, severe=0, high=0, avg=1, duration=3600):
    return {
        "id": route_id,
        "duration_seconds": duration,
        "summary": SimpleNamespace(
            no_travel_miles=no_travel,
            severe_miles=severe,
            high_miles=high,
            avg_risk=avg,
        ),
    }


class RouteRecommendationTests(SimpleTestCase):
    def test_severe_miles_precede_duration(self):
        faster_but_riskier = make_route(1, severe=10, duration=1000)
        slower_but_safer = make_route(2, severe=0, duration=5000)

        self.assertEqual(
            rank_routes([faster_but_riskier, slower_but_safer]),
            [slower_but_safer, faster_but_riskier],
        )

    def test_high_miles_decide_after_equal_severe_miles(self):
        more_high = make_route(1, severe=5, high=12, duration=1000)
        less_high = make_route(2, severe=5, high=2, duration=5000)

        self.assertEqual(rank_routes([more_high, less_high]), [less_high, more_high])

    def test_average_risk_decides_after_equal_mile_totals(self):
        higher_avg = make_route(1, severe=5, high=2, avg=3.0, duration=1000)
        lower_avg = make_route(2, severe=5, high=2, avg=2.0, duration=5000)

        self.assertEqual(
            rank_routes([higher_avg, lower_avg]), [lower_avg, higher_avg]
        )

    def test_duration_decides_after_equal_weather_risk(self):
        slower = make_route(2, duration=5000)
        faster = make_route(1, duration=1000)

        self.assertEqual(rank_routes([slower, faster]), [faster, slower])

    def test_no_travel_miles_are_the_first_sort_criterion(self):
        no_travel = make_route(1, no_travel=1, severe=0)
        safe = make_route(2, no_travel=0, severe=20)

        self.assertEqual(rank_routes([no_travel, safe]), [safe, no_travel])

    def test_route_id_breaks_exact_ties_and_sort_is_stable(self):
        later_id = make_route(8)
        earlier_id = make_route(2)

        self.assertEqual(rank_routes([later_id, earlier_id]), [earlier_id, later_id])

    def test_reason_names_first_differing_weather_criterion(self):
        best = make_route(1, severe=0, high=10, avg=2)
        other_a = make_route(2, severe=45, high=0, avg=1)
        other_b = make_route(3, severe=120, high=0, avg=1)

        self.assertEqual(
            build_reason(best, [other_a, other_b]),
            "Fewest severe miles: 0 vs 45 and 120 on the other routes.",
        )

    def test_reason_uses_high_miles_when_severe_miles_tie(self):
        best = make_route(1, severe=4, high=1)
        other = make_route(2, severe=4, high=8)

        self.assertEqual(
            build_reason(best, [other]),
            "Fewest high-risk miles: 1 vs 8 on the other routes.",
        )

    def test_reason_uses_no_travel_miles_before_other_criteria(self):
        best = make_route(1, no_travel=0, severe=20)
        other = make_route(2, no_travel=5, severe=0)

        self.assertEqual(
            build_reason(best, [other]),
            "Fewest no-travel miles: 0 vs 5 on the other routes.",
        )

    def test_reason_uses_average_risk_when_mile_totals_tie(self):
        best = make_route(1, severe=4, high=1, avg=1.5)
        other = make_route(2, severe=4, high=1, avg=2.2)

        self.assertEqual(
            build_reason(best, [other]),
            "Lowest average risk: 1.5 vs 2.2 on the other routes.",
        )

    def test_same_risk_reason_when_fastest(self):
        best = make_route(1, duration=1000)
        other = make_route(2, duration=2000)

        self.assertEqual(
            build_reason(best, [other]),
            "Same weather risk on all routes; this is the fastest.",
        )

    def test_all_routes_with_no_travel_conditions_use_special_reason(self):
        best = make_route(1, no_travel=2)
        other = make_route(2, no_travel=5)

        self.assertEqual(
            build_reason(best, [other]),
            "All routes cross no-travel conditions; this one has the fewest no-travel miles.",
        )

    def test_only_one_route_reason(self):
        self.assertEqual(build_reason(make_route(1), []), "Only one route available.")

    def test_compare_reason_summarizes_risk_and_time_differences(self):
        best = make_route(1, severe=2, duration=3600)
        other = make_route(2, severe=47, duration=7920)

        self.assertEqual(
            compare_reason(other, best),
            "+45 severe miles, +1.2 h vs recommended.",
        )
