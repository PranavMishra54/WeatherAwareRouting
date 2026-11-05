from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class RiskLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4
    NO_TRAVEL = 5

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "low",
            RiskLevel.MODERATE: "moderate",
            RiskLevel.HIGH: "high",
            RiskLevel.SEVERE: "severe",
            RiskLevel.NO_TRAVEL: "no_travel",
        }[self]


@dataclass
class RiskAssessment:
    level: RiskLevel
    reasons: list[str]


@dataclass
class RouteSummary:
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    moderate_miles: float
    low_miles: float
    avg_risk: float
    max_risk: RiskLevel


def classify_wind(mph: float) -> RiskLevel:
    if mph < 25:
        return RiskLevel.LOW
    if mph < 35:
        return RiskLevel.MODERATE
    if mph < 45:
        return RiskLevel.HIGH
    if mph < 55:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_rain(in_hr: float) -> RiskLevel:
    if in_hr < 0.10:
        return RiskLevel.LOW
    if in_hr <= 0.25:
        return RiskLevel.MODERATE
    if in_hr <= 0.50:
        return RiskLevel.HIGH
    if in_hr <= 1.00:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_snow(in_hr: float) -> RiskLevel:
    if in_hr < 0.5:
        return RiskLevel.LOW
    if in_hr <= 1.0:
        return RiskLevel.MODERATE
    if in_hr <= 2.0:
        return RiskLevel.HIGH
    if in_hr <= 3.0:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def assess_checkpoint(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lb: float,
) -> RiskAssessment:
    wind_level = classify_wind(wind_mph)
    rain_level = classify_rain(rain_in_hr)
    snow_level = classify_snow(snow_in_hr)
    load_level = wind_level
    reasons = []

    if wind_level > RiskLevel.LOW:
        reasons.append(f"Wind {wind_mph:g} mph: {wind_level.label.replace('_', ' ')}")
    if rain_level > RiskLevel.LOW:
        reasons.append(f"Rain {rain_in_hr:.2f} in/hr: {rain_level.label.replace('_', ' ')}")
    if snow_level > RiskLevel.LOW:
        reasons.append(f"Snow {snow_in_hr:.2f} in/hr: {snow_level.label.replace('_', ' ')}")

    load_reason = None
    if 45 <= wind_mph < 55 and load_weight_lb > 30000:
        load_level = RiskLevel.NO_TRAVEL
        load_reason = (
            f"Wind {wind_mph:g} mph with {load_weight_lb:,.0f} lb load: no travel"
        )
    elif 35 <= wind_mph < 45 and load_weight_lb > 40000:
        load_level = RiskLevel.SEVERE
        load_reason = (
            f"Wind {wind_mph:g} mph with {load_weight_lb:,.0f} lb load: "
            "raised to severe"
        )

    level = max(wind_level, rain_level, snow_level, load_level)
    if load_reason:
        reasons.append(load_reason)
    if not reasons:
        reasons.append("Conditions normal")

    return RiskAssessment(level=level, reasons=reasons)


def summarize_route(checkpoints: Iterable[object]) -> RouteSummary:
    checkpoints = list(checkpoints)
    if not checkpoints:
        raise ValueError("checkpoints must not be empty")

    miles_by_level = {level: 0.0 for level in RiskLevel}
    weighted_risk = 0.0
    total_miles = 0.0

    for checkpoint in checkpoints:
        miles = checkpoint.segment_miles
        miles_by_level[checkpoint.level] += miles
        weighted_risk += checkpoint.level.value * miles
        total_miles += miles

    if total_miles:
        avg_risk = weighted_risk / total_miles
    else:
        avg_risk = sum(checkpoint.level.value for checkpoint in checkpoints) / len(
            checkpoints
        )

    return RouteSummary(
        no_travel_miles=round(miles_by_level[RiskLevel.NO_TRAVEL], 1),
        severe_miles=round(miles_by_level[RiskLevel.SEVERE], 1),
        high_miles=round(miles_by_level[RiskLevel.HIGH], 1),
        moderate_miles=round(miles_by_level[RiskLevel.MODERATE], 1),
        low_miles=round(miles_by_level[RiskLevel.LOW], 1),
        avg_risk=round(avg_risk, 2),
        max_risk=max(checkpoint.level for checkpoint in checkpoints),
    )