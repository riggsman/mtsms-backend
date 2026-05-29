from decimal import Decimal
from types import SimpleNamespace

from app.services.gpa_service import (
    DEFAULT_GRADING_RANGES,
    GPAEngine,
    calculate_cumulative_gpa,
)


def _make_range(minimum_score, maximum_score, grade, grade_point):
    return SimpleNamespace(
        minimum_score=minimum_score,
        maximum_score=maximum_score,
        grade=grade,
        grade_point=grade_point,
    )


def test_gpa_engine_maps_score_to_grade_and_weighted_points():
    ranges = [
        _make_range(90.0, 100.0, "A", 4.0),
        _make_range(80.0, 89.99, "B", 3.0),
        _make_range(0.0, 59.99, "F", 0.0),
    ]

    result = GPAEngine.calculate_grade(83, 3, ranges)

    assert result["grade"] == "B"
    assert result["grade_point"] == 3.0
    assert result["course_weight"] == 3.0
    assert result["weighted_points"] == 9.0


def test_gpa_engine_returns_na_for_out_of_range_score():
    ranges = [_make_range(60.0, 100.0, "P", 0.0)]

    result = GPAEngine.calculate_grade(50, 1, ranges)

    assert result["grade"] == "N/A"
    assert result["grade_point"] == 0.0
    assert result["weighted_points"] == 0.0


def test_calculate_cumulative_gpa_is_credit_weighted():
    records = [
        SimpleNamespace(gpa=Decimal("4.0"), course_weight=Decimal("3.0")),
        SimpleNamespace(gpa=Decimal("2.0"), course_weight=Decimal("1.0")),
    ]

    assert calculate_cumulative_gpa(records) == 3.5


def test_calculate_cumulative_gpa_defaults_missing_weight_to_one():
    records = [
        SimpleNamespace(gpa=Decimal("4.0"), course_weight=None),
        SimpleNamespace(gpa=Decimal("2.0"), course_weight=None),
    ]

    assert calculate_cumulative_gpa(records) == 3.0


def test_default_grading_ranges_cover_full_score_scale():
    assert len(DEFAULT_GRADING_RANGES) == 5
    assert DEFAULT_GRADING_RANGES[0]["minimum_score"] == 0.0
    assert DEFAULT_GRADING_RANGES[-1]["maximum_score"] == 100.0
