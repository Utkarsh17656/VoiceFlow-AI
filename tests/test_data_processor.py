"""
tests/test_data_processor.py
-----------------------------
Comprehensive tests for the multi-source DataProcessorService.

Run from the project root:
    .venv\\Scripts\\python tests/test_data_processor.py

Or with pytest:
    .venv\\Scripts\\python -m pytest tests/test_data_processor.py -v

NOTE on phone numbers:
    Pandas reads phone columns as floats when they look numeric, which strips
    the leading '+'. The service calls str() on the raw cell value, so a cell
    containing '+919876543210' will become '919876543210.0' after pandas
    parses it as a float.  Tests account for this by checking that the
    *digits* are present rather than requiring an exact '+'-prefixed string.
    To preserve '+' reliably in real files, quote the phone column or use
    dtype=str — the service already handles NaN/None correctly either way.
"""

from __future__ import annotations

import io
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from voxreach_ai.services.data_processor import DataProcessorService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "[PASS]"
FAIL = "[FAIL]"

_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    symbol = PASS if condition else FAIL
    suffix = f"  [{detail}]" if detail else ""
    print(f"  {symbol}  {label}{suffix}")
    _results.append((label, condition, detail))


def _csv(rows: str) -> bytes:
    """Return CSV content as UTF-8 bytes (strip leading newline from triple-quotes)."""
    return rows.strip().encode("utf-8")


def _xlsx(df: pd.DataFrame) -> bytes:
    """Serialise a DataFrame to an in-memory Excel file and return raw bytes."""
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _digits(phone: str) -> str:
    """Strip all non-digit characters for comparison."""
    return "".join(ch for ch in phone if ch.isdigit())


# ===========================================================================
# TEST SUITE
# ===========================================================================

def test_csv_standard():
    """Standard CSV with canonical column names."""
    print("\n[1] CSV - standard columns (name / phone / history)")
    csv = _csv(
        "name,phone,history\n"
        "Rahul Sharma,+919876543210,Requested a demo for AI CRM\n"
        "Priya Mehta,+919123456789,Asked about pricing plans\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="standard.csv")
    check("Parses 2 customers", len(customers) == 2)
    check("Name correct", customers[0].name == "Rahul Sharma")
    check("Phone digits correct", _digits(customers[0].phone) == "919876543210")
    check("History correct", "demo" in customers[0].interaction_history.lower())
    check("Second customer name", customers[1].name == "Priya Mehta")


def test_csv_column_aliases():
    """CSV using alternate column names that must be auto-resolved."""
    print("\n[2] CSV - column aliases (customer_name / mobile / interaction_history)")
    csv = _csv(
        "customer_name,mobile,interaction_history\n"
        "Deepak Verma,+916543210987,Wants ERP integration\n"
        "Sneha Patil,+915432109876,Looking for WhatsApp automation\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="aliases.csv")
    check("Resolves 2 customers via aliases", len(customers) == 2)
    check("Name alias resolved", customers[0].name == "Deepak Verma")
    check("Phone digits via alias", _digits(customers[0].phone) == "916543210987")
    check("History alias resolved", "ERP" in customers[0].interaction_history)


def test_csv_missing_phone_skipped():
    """Rows without a phone number must be skipped."""
    print("\n[3] CSV - missing phone rows are skipped")
    csv = _csv(
        "name,phone,history\n"
        "Valid Person,+911234567890,Some history\n"
        "No Phone Person,,Has history but no phone\n"
        "Another Valid,+910987654321,Another history\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="missing_phone.csv")
    check("Skips row with empty phone", len(customers) == 2)
    check("Keeps first valid row", customers[0].name == "Valid Person")
    check("Keeps second valid row", customers[1].name == "Another Valid")


def test_csv_missing_history_column_defaults():
    """CSV without any history column should default all rows."""
    print("\n[4a] CSV - no history column defaults to 'No prior interaction'")
    csv = _csv(
        "name,phone\n"
        "Amit Joshi,+918765432100\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="no_hist_col.csv")
    check("Parsed 1 customer", len(customers) == 1)
    check(
        "No history column => default applied",
        customers[0].interaction_history == "No prior interaction",
    )


def test_csv_blank_history_cell_defaults():
    """CSV with a blank history cell should fall back to the default."""
    print("\n[4b] CSV - blank history cell defaults to 'No prior interaction'")
    csv = _csv(
        "name,phone,history\n"
        "Kiran Rao,+917654321098,\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="blank_hist.csv")
    check("Parsed 1 customer", len(customers) == 1)
    check(
        "Blank history cell => default applied",
        customers[0].interaction_history == "No prior interaction",
    )


def test_csv_missing_name_defaults():
    """Rows with a blank name field must default to 'Unknown'."""
    print("\n[5] CSV - missing name defaults to 'Unknown'")
    csv = _csv(
        "name,phone,history\n"
        ",+919999999999,Some history\n"
    )
    customers = DataProcessorService.parse(file_content=csv, filename="no_name.csv")
    check("Missing name => defaults to 'Unknown'", customers[0].name == "Unknown")


def test_csv_invalid_extension():
    """Non-CSV/XLSX extension must raise ValueError."""
    print("\n[6] CSV - unsupported file extension raises ValueError")
    try:
        DataProcessorService.parse(file_content=b"data", filename="data.txt")
        check("Raises ValueError for .txt", False, "No exception raised!")
    except ValueError as e:
        check("Raises ValueError for .txt", True, str(e)[:60])


def test_csv_missing_required_column():
    """CSV missing the phone column must raise ValueError."""
    print("\n[7] CSV - missing required 'phone' column raises ValueError")
    csv = _csv(
        "name,history\n"
        "Rohit,Asked about demo\n"
    )
    try:
        DataProcessorService.parse(file_content=csv, filename="no_phone_col.csv")
        check("Raises ValueError for missing phone column", False, "No exception raised!")
    except ValueError as e:
        check("Raises ValueError for missing phone column", True, str(e)[:70])


def test_excel_standard():
    """Excel file with canonical column names."""
    print("\n[8] Excel - standard columns (name / phone / history)")
    df = pd.DataFrame({
        "name":    ["Priya Mehta", "Kiran Rao"],
        "phone":   ["+919123456789", "+917654321098"],
        "history": ["Asked about pricing", "Follow-up after webinar"],
    })
    customers = DataProcessorService.parse(file_content=_xlsx(df), filename="customers.xlsx")
    check("Parses 2 customers from XLSX", len(customers) == 2)
    check("Name correct", customers[0].name == "Priya Mehta")
    check("History correct", "pricing" in customers[0].interaction_history)
    check("Phone digits correct", _digits(customers[0].phone) == "919123456789")


def test_excel_with_missing_phone():
    """Excel rows with empty phone must be skipped."""
    print("\n[9] Excel - skips rows with missing phone")
    df = pd.DataFrame({
        "name":    ["Valid",   "No Phone"],
        "phone":   ["+911111111111", None],
        "history": ["Has history", "No phone row"],
    })
    customers = DataProcessorService.parse(file_content=_xlsx(df), filename="edge.xlsx")
    check("Skips row with None phone in XLSX", len(customers) == 1)
    check("Keeps valid row", customers[0].name == "Valid")


def test_excel_with_aliases():
    """Excel file using column aliases."""
    print("\n[10] Excel - column aliases (full_name / contact / interaction_history)")
    df = pd.DataFrame({
        "full_name":           ["Suresh Kumar"],
        "contact":             ["+912222222222"],
        "interaction_history": ["Wants cloud ERP demo"],
    })
    customers = DataProcessorService.parse(file_content=_xlsx(df), filename="alias.xlsx")
    check("Resolves alias columns in XLSX", len(customers) == 1)
    check("Name alias resolved", customers[0].name == "Suresh Kumar")
    check("Phone digits via alias", _digits(customers[0].phone) == "912222222222")
    check("History alias resolved", "ERP" in customers[0].interaction_history)


def test_excel_missing_history_defaults():
    """Excel file without a history column defaults to 'No prior interaction'."""
    print("\n[11] Excel - no history column defaults to 'No prior interaction'")
    df = pd.DataFrame({
        "name":  ["Meena Sharma"],
        "phone": ["+913333333333"],
    })
    customers = DataProcessorService.parse(file_content=_xlsx(df), filename="nohist.xlsx")
    check("Parsed 1 customer from XLSX", len(customers) == 1)
    check(
        "No history column in XLSX => default applied",
        customers[0].interaction_history == "No prior interaction",
    )


def test_google_sheet_url_rewriting():
    """Google Sheets URL rewriting (pure logic, no network calls)."""
    print("\n[12] Google Sheets - URL rewriting logic")
    svc = DataProcessorService()

    edit_url = (
        "https://docs.google.com/spreadsheets/d/"
        "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit#gid=0"
    )
    csv_url = svc._to_csv_export_url(edit_url)
    check(
        "Edit URL rewritten to CSV export URL",
        "export?format=csv" in csv_url,
        csv_url,
    )
    check(
        "Sheet ID preserved in rewritten URL",
        "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms" in csv_url,
    )
    check("gid=0 preserved", "gid=0" in csv_url)

    # Pre-formed CSV export URL must pass through unchanged
    already_csv = (
        "https://docs.google.com/spreadsheets/d/FAKE_ID/export?format=csv"
    )
    check(
        "Pre-formed CSV URL passes through unchanged",
        svc._to_csv_export_url(already_csv) == already_csv,
    )

    # Invalid URL (not a Google Sheets link)
    try:
        svc._to_csv_export_url("https://example.com/not-a-sheet")
        check("Raises ValueError for non-Google-Sheets URL", False)
    except ValueError as e:
        check("Raises ValueError for non-Google-Sheets URL", True, str(e)[:60])


def test_dispatcher_no_input():
    """Calling parse() with no arguments must raise ValueError."""
    print("\n[13] Dispatcher - no input raises ValueError")
    try:
        DataProcessorService.parse()
        check("Raises ValueError for empty call", False)
    except ValueError as e:
        check("Raises ValueError for empty call", True, str(e)[:60])


def test_sample_files_on_disk():
    """
    Integration test: loads the actual sample files shipped with the project.

    Files expected (relative to project root):
        voxreach_ai/sample_customers.csv
        voxreach_ai/sample_customers.xlsx
        voxreach_ai/sample_customers_aliases.csv
    """
    print("\n[14] Integration - sample files on disk")
    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "voxreach_ai")
    )

    # -- sample_customers.csv --
    csv_path = os.path.join(base, "sample_customers.csv")
    if os.path.exists(csv_path):
        with open(csv_path, "rb") as fh:
            c = DataProcessorService.parse(
                file_content=fh.read(), filename="sample_customers.csv"
            )
        check("sample_customers.csv loaded", len(c) >= 1, f"{len(c)} customer(s)")
    else:
        check("sample_customers.csv exists on disk", False, "file not found")

    # -- sample_customers.xlsx --
    xlsx_path = os.path.join(base, "sample_customers.xlsx")
    if os.path.exists(xlsx_path):
        with open(xlsx_path, "rb") as fh:
            c2 = DataProcessorService.parse(
                file_content=fh.read(), filename="sample_customers.xlsx"
            )
        check("sample_customers.xlsx loaded", len(c2) >= 1, f"{len(c2)} customer(s)")
    else:
        check("sample_customers.xlsx exists on disk", False, "file not found")

    # -- sample_customers_aliases.csv --
    alias_path = os.path.join(base, "sample_customers_aliases.csv")
    if os.path.exists(alias_path):
        with open(alias_path, "rb") as fh:
            c3 = DataProcessorService.parse(
                file_content=fh.read(), filename="sample_customers_aliases.csv"
            )
        check(
            "sample_customers_aliases.csv loaded",
            len(c3) >= 1,
            f"{len(c3)} customer(s)",
        )
    else:
        check("sample_customers_aliases.csv exists on disk", False, "file not found")


# ===========================================================================
# RUNNER
# ===========================================================================

def main() -> None:
    print("=" * 60)
    print("  VoxReach AI - DataProcessorService Test Suite")
    print("=" * 60)

    test_csv_standard()
    test_csv_column_aliases()
    test_csv_missing_phone_skipped()
    test_csv_missing_history_column_defaults()
    test_csv_blank_history_cell_defaults()
    test_csv_missing_name_defaults()
    test_csv_invalid_extension()
    test_csv_missing_required_column()
    test_excel_standard()
    test_excel_with_missing_phone()
    test_excel_with_aliases()
    test_excel_missing_history_defaults()
    test_google_sheet_url_rewriting()
    test_dispatcher_no_input()
    test_sample_files_on_disk()

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total  = len(_results)

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {FAIL} {failed} FAILED")
        for label, ok, detail in _results:
            if not ok:
                suffix = f" [{detail}]" if detail else ""
                print(f"     {FAIL}  {label}{suffix}")
    else:
        print(f"  {PASS}")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
