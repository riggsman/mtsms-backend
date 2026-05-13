from decimal import Decimal

from app.services.ranking_service import compute_dense_rank


def test_compute_dense_rank_with_ties():
    sorted_pairs = [
        ("S1", Decimal("90")),
        ("S2", Decimal("90")),
        ("S3", Decimal("84")),
        ("S4", Decimal("79")),
        ("S5", Decimal("79")),
    ]
    ranked = compute_dense_rank(sorted_pairs)
    assert ranked == [
        ("S1", Decimal("90"), 1),
        ("S2", Decimal("90"), 1),
        ("S3", Decimal("84"), 2),
        ("S4", Decimal("79"), 3),
        ("S5", Decimal("79"), 3),
    ]


def test_compute_dense_rank_empty():
    assert compute_dense_rank([]) == []
