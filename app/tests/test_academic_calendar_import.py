"""Unit tests for academic calendar CSV/XLSX parsing."""
from datetime import date

from app.services.academic_calendar_import import (
    _map_headers,
    _normalize_header,
    _parse_date_range_value,
    _parse_date_value,
    format_date_range_display,
    parse_csv_content,
)


def test_normalize_header():
    assert _normalize_header("  event   date  ") == "EVENT DATE"


def test_map_headers_default_aliases():
    date_idx, act_idx = _map_headers(["Date", "Activities"])
    assert date_idx == 0
    assert act_idx == 1


def test_map_headers_two_column_fallback():
    date_idx, act_idx = _map_headers(["Col A", "Col B"])
    assert date_idx == 0
    assert act_idx == 1


def test_parse_date_iso_and_slash():
    assert _parse_date_value("2025-09-01") == date(2025, 9, 1)
    assert _parse_date_value("15/12/2025") == date(2025, 12, 15)
    assert _parse_date_value("01/09/2025") == date(2025, 9, 1)


def test_parse_date_range_en_dash():
    start, end = _parse_date_range_value("01/09/2026 – 30/09/2026")
    assert start == date(2026, 9, 1)
    assert end == date(2026, 9, 30)


def test_parse_date_range_single_day():
    start, end = _parse_date_range_value("15/12/2026")
    assert start == date(2026, 12, 15)
    assert end == date(2026, 12, 15)


def test_format_date_range_display():
    assert format_date_range_display(date(2026, 9, 1), date(2026, 9, 30)) == "01/09/2026 – 30/09/2026"
    assert format_date_range_display(date(2026, 12, 15)) == "15/12/2026"


def test_parse_csv_standard_template():
    content = b"DATE,ACTIVITIES\n2025-09-01,Opening ceremony\n2025-12-15,Exams\n"
    rows, errors = parse_csv_content(content)
    assert not errors
    assert len(rows) == 2
    assert rows[0].event_date == date(2025, 9, 1)
    assert rows[0].event_end_date == date(2025, 9, 1)
    assert rows[0].activity == "Opening ceremony"
    assert rows[1].row_order == 2


def test_parse_csv_date_range():
    content = (
        b"DATE,ACTIVITIES\n"
        b"01/09/2026 \xe2\x80\x93 30/09/2026,Registration period\n"
        b"15/12/2026,Exams\n"
    )
    rows, errors = parse_csv_content(content)
    assert not errors
    assert len(rows) == 2
    assert rows[0].event_date == date(2026, 9, 1)
    assert rows[0].event_end_date == date(2026, 9, 30)
    assert rows[0].activity == "Registration period"


def test_parse_csv_skips_blank_rows_and_reports_bad_date():
    content = b"DATE,ACTIVITIES\n,\n2025-01-01,Valid\nnot-a-date,Bad\n"
    rows, errors = parse_csv_content(content)
    assert len(rows) == 1
    assert rows[0].activity == "Valid"
    assert any(e.row == 3 for e in errors)
    assert any(e.row == 4 for e in errors)
