from types import SimpleNamespace

from django.test import SimpleTestCase

from routing.services.risk import (
    RiskLevel,
    assess_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
    summarize_route,
)


class RiskClassifierTests(SimpleTestCase):
    def test_risk_level_labels(self):
        self.assertEqual(
            [level.label for level in RiskLevel],
            ["low", "moderate", "high", "severe", "no_travel"],
        )

    def test_wind_threshold_boundaries(self):
        cases = [
            (24.9, RiskLevel.LOW),
            (25, RiskLevel.MODERATE),
            (34.9, RiskLevel.MODERATE),
            (35, RiskLevel.HIGH),
            (44.9, RiskLevel.HIGH),
            (45, RiskLevel.SEVERE),
            (54.9, RiskLevel.SEVERE),
            (55, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(mph=value):
                self.assertEqual(classify_wind(value), expected)

    def test_rain_threshold_boundaries(self):
        cases = [
            (0.09, RiskLevel.LOW),
            (0.10, RiskLevel.MODERATE),
            (0.25, RiskLevel.MODERATE),
            (0.26, RiskLevel.HIGH),
            (0.50, RiskLevel.HIGH),
            (0.51, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),
            (1.01, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(in_hr=value):
                self.assertEqual(classify_rain(value), expected)

    def test_snow_threshold_boundaries(self):
        cases = [
            (0.4, RiskLevel.LOW),
            (0.5, RiskLevel.MODERATE),
            (1.0, RiskLevel.MODERATE),
            (1.1, RiskLevel.HIGH),
            (2.0, RiskLevel.HIGH),
            (2.1, RiskLevel.SEVERE),
            (3.0, RiskLevel.SEVERE),
            (3.1, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(in_hr=value):
                self.assertEqual(classify_snow(value), expected)


class CheckpointAssessmentTests(SimpleTestCase):
    def test_worst_of_weather_conditions_determines_risk(self):
        assessment = assess_checkpoint(
            wind_mph=20, rain_in_hr=0.30, snow_in_hr=0.8, load_weight_lb=1000
        )

        self.assertEqual(assessment.level, RiskLevel.HIGH)
        self.assertEqual(
            assessment.reasons,
            ["Rain 0.30 in/hr: high", "Snow 0.80 in/hr: moderate"],
        )

    def test_load_rules_and_strict_weight_boundaries(self):
        cases = [
            (50, 30001, RiskLevel.NO_TRAVEL),
            (50, 30000, RiskLevel.SEVERE),
            (40, 40001, RiskLevel.SEVERE),
            (40, 40000, RiskLevel.HIGH),
            (56, 1000, RiskLevel.NO_TRAVEL),
            (30, 80000, RiskLevel.MODERATE),
        ]
        for wind, load, expected in cases:
            with self.subTest(wind=wind, load=load):
                self.assertEqual(
                    assess_checkpoint(wind, 0, 0, load).level, expected
                )

    def test_load_rule_never_lowers_existing_weather_risk(self):
        heavy_snow = assess_checkpoint(
            wind_mph=40, rain_in_hr=0, snow_in_hr=2.5, load_weight_lb=41000
        )
        extreme_rain = assess_checkpoint(
            wind_mph=20, rain_in_hr=1.1, snow_in_hr=0, load_weight_lb=80000
        )

        self.assertEqual(heavy_snow.level, RiskLevel.SEVERE)
        self.assertEqual(extreme_rain.level, RiskLevel.NO_TRAVEL)

    def test_reasons_include_weather_and_load_details(self):
        assessment = assess_checkpoint(
            wind_mph=41, rain_in_hr=0.30, snow_in_hr=0, load_weight_lb=45000
        )

        self.assertEqual(assessment.level, RiskLevel.SEVERE)
        self.assertEqual(
            assessment.reasons,
            [
                "Wind 41 mph: high",
                "Rain 0.30 in/hr: high",
                "Wind 41 mph with 45,000 lb load: raised to severe",
            ],
        )

    def test_load_rule_can_raise_severe_wind_to_no_travel(self):
        assessment = assess_checkpoint(
            wind_mph=50, rain_in_hr=0, snow_in_hr=0, load_weight_lb=35000
        )

        self.assertEqual(assessment.level, RiskLevel.NO_TRAVEL)
        self.assertIn(
            "Wind 50 mph with 35,000 lb load: no travel", assessment.reasons
        )

    def test_normal_conditions_have_single_reason(self):
        assessment = assess_checkpoint(
            wind_mph=24, rain_in_hr=0.09, snow_in_hr=0.4, load_weight_lb=80000
        )

        self.assertEqual(assessment.level, RiskLevel.LOW)
        self.assertEqual(assessment.reasons, ["Conditions normal"])


class RouteSummaryTests(SimpleTestCase):
    @staticmethod
    def checkpoint(level, miles):
        return SimpleNamespace(level=level, segment_miles=miles)

    def test_summarizes_level_miles_weighted_average_and_maximum(self):
        checkpoints = [
            self.checkpoint(RiskLevel.LOW, 50.04),
            self.checkpoint(RiskLevel.MODERATE, 40.04),
            self.checkpoint(RiskLevel.HIGH, 30.04),
            self.checkpoint(RiskLevel.SEVERE, 20.04),
            self.checkpoint(RiskLevel.NO_TRAVEL, 10.04),
        ]

        summary = summarize_route(checkpoints)

        self.assertEqual(summary.low_miles, 50.0)
        self.assertEqual(summary.moderate_miles, 40.0)
        self.assertEqual(summary.high_miles, 30.0)
        self.assertEqual(summary.severe_miles, 20.0)
        self.assertEqual(summary.no_travel_miles, 10.0)
        self.assertEqual(summary.avg_risk, 2.33)
        self.assertEqual(summary.max_risk, RiskLevel.NO_TRAVEL)

    def test_zero_distance_uses_plain_average(self):
        summary = summarize_route(
            [
                self.checkpoint(RiskLevel.LOW, 0),
                self.checkpoint(RiskLevel.HIGH, 0),
            ]
        )

        self.assertEqual(summary.avg_risk, 2.0)

    def test_empty_route_raises_value_error(self):
        with self.assertRaises(ValueError):
            summarize_route([])
