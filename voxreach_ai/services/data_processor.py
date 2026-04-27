"""
data_processor.py
-----------------
Modular, multi-source data ingestion service for VoxReach AI.

Supported input types:
  - CSV  (.csv)  — raw bytes or file path
  - Excel (.xlsx) — raw bytes (via openpyxl engine)
  - Google Sheets — public CSV export URL

Column standardization:
  Accepted aliases are normalised to the canonical schema:
    canonical      | accepted aliases
    ---------------|---------------------------------
    name           | name, customer_name, full_name
    phone          | phone, phone_number, mobile, contact
    history        | history, interaction_history,
                   | notes, last_interaction, summary

Validation rules:
  - Rows missing a phone number are skipped and logged.
  - Rows with any other missing required field fall back to safe defaults.
"""

from __future__ import annotations

import io
from typing import List, Tuple

import pandas as pd
import requests

from voxreach_ai.models.customer import Customer
from voxreach_ai.utils.logger import logger

# ---------------------------------------------------------------------------
# Column alias mapping
# ---------------------------------------------------------------------------
_NAME_ALIASES: Tuple[str, ...] = ("name", "customer_name", "full_name")
_PHONE_ALIASES: Tuple[str, ...] = ("phone", "phone_number", "mobile", "contact")
_HISTORY_ALIASES: Tuple[str, ...] = (
    "history",
    "interaction_history",
    "notes",
    "last_interaction",
    "summary",
)

_DEFAULT_HISTORY = "No prior interaction"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_column(df_columns: List[str], aliases: Tuple[str, ...]) -> str | None:
    """Return the first alias found in *df_columns*, or None."""
    col_set = set(df_columns)
    for alias in aliases:
        if alias in col_set:
            return alias
    return None


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename DataFrame columns to canonical names:
      name, phone, history

    Raises ValueError if *name* or *phone* cannot be resolved.
    """
    # Normalise header casing
    df.columns = [str(c).lower().strip() for c in df.columns]

    name_col = _find_column(list(df.columns), _NAME_ALIASES)
    phone_col = _find_column(list(df.columns), _PHONE_ALIASES)
    history_col = _find_column(list(df.columns), _HISTORY_ALIASES)

    missing = []
    if name_col is None:
        missing.append(f"name (tried: {', '.join(_NAME_ALIASES)})")
    if phone_col is None:
        missing.append(f"phone (tried: {', '.join(_PHONE_ALIASES)})")

    if missing:
        raise ValueError(
            f"Required column(s) not found in file: {'; '.join(missing)}"
        )

    rename_map: dict[str, str] = {name_col: "name", phone_col: "phone"}
    if history_col:
        rename_map[history_col] = "history"

    df = df.rename(columns=rename_map)

    # Add history column with default if it was absent
    if "history" not in df.columns:
        logger.warning(
            "No 'history' column found — defaulting all rows to '%s'.",
            _DEFAULT_HISTORY,
        )
        df["history"] = _DEFAULT_HISTORY

    return df[["name", "phone", "history"]]


def _build_customers(df: pd.DataFrame, source_label: str) -> List[Customer]:
    """
    Convert a normalised DataFrame into a list of :class:`Customer` objects.

    - Rows with an empty / NaN phone are skipped (logged as warnings).
    - Name defaults to "Unknown" if blank.
    - History defaults to *_DEFAULT_HISTORY* if blank / NaN.
    """
    customers: List[Customer] = []
    skipped = 0

    for idx, row in df.iterrows():
        row_label = f"[{source_label} row {idx + 2}]"  # +2: 1-indexed + header

        # --- phone validation (hard requirement) ---
        raw_phone = str(row.get("phone", "")).strip()
        if not raw_phone or raw_phone.lower() in ("nan", "none", ""):
            logger.warning("%s Skipped — missing phone number.", row_label)
            skipped += 1
            continue

        # --- name (soft requirement) ---
        raw_name = str(row.get("name", "")).strip()
        if not raw_name or raw_name.lower() in ("nan", "none"):
            logger.warning("%s Missing name — defaulting to 'Unknown'.", row_label)
            raw_name = "Unknown"

        # --- history (optional) ---
        raw_history = str(row.get("history", "")).strip()
        if not raw_history or raw_history.lower() in ("nan", "none"):
            raw_history = _DEFAULT_HISTORY

        try:
            customers.append(
                Customer(
                    name=raw_name,
                    phone=raw_phone,
                    interaction_history=raw_history,
                )
            )
        except Exception as exc:
            logger.error("%s Failed to create Customer object — %s", row_label, exc)
            skipped += 1

    logger.info(
        "Parsed %d customer(s) from '%s' (%d skipped).",
        len(customers),
        source_label,
        skipped,
    )
    return customers


# ---------------------------------------------------------------------------
# Public DataProcessorService
# ---------------------------------------------------------------------------

class DataProcessorService:
    """
    Stateless service that reads customer data from multiple sources
    and returns a validated list of :class:`Customer` models.
    """

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------
    @staticmethod
    def parse_csv(file_content: bytes, source_label: str = "csv") -> List[Customer]:
        """
        Parse CSV bytes into a list of Customer objects.

        Compatible with the original interface — drop-in replacement.
        """
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            df = _normalise_columns(df)
            return _build_customers(df, source_label)
        except ValueError:
            raise  # already has a clear message
        except Exception as exc:
            logger.error("Error parsing CSV: %s", exc)
            raise ValueError(f"Failed to process CSV file: {exc}") from exc

    # ------------------------------------------------------------------
    # Excel (.xlsx)
    # ------------------------------------------------------------------
    @staticmethod
    def parse_excel(file_content: bytes, source_label: str = "xlsx") -> List[Customer]:
        """
        Parse Excel (.xlsx) bytes into a list of Customer objects.
        Requires *openpyxl* (listed in requirements.txt).
        """
        try:
            df = pd.read_excel(io.BytesIO(file_content), engine="openpyxl")
            df = _normalise_columns(df)
            return _build_customers(df, source_label)
        except ValueError:
            raise
        except Exception as exc:
            logger.error("Error parsing Excel file: %s", exc)
            raise ValueError(f"Failed to process Excel file: {exc}") from exc

    # ------------------------------------------------------------------
    # Google Sheets (public CSV export URL)
    # ------------------------------------------------------------------
    @staticmethod
    def parse_google_sheet(sheet_url: str) -> List[Customer]:
        """
        Fetch a *publicly shared* Google Sheet via its CSV export URL and
        parse the result into Customer objects.

        Accepted URL formats:
          - Full edit URL:  https://docs.google.com/spreadsheets/d/<ID>/edit#gid=0
          - Sharing URL:    https://docs.google.com/spreadsheets/d/<ID>/...
          - Direct CSV URL: https://docs.google.com/spreadsheets/d/<ID>/export?format=csv

        The method automatically rewrites any edit/share URL to the
        ``/export?format=csv`` form.
        """
        try:
            csv_url = DataProcessorService._to_csv_export_url(sheet_url)
            logger.info("Fetching Google Sheet CSV: %s", csv_url)

            response = requests.get(csv_url, timeout=15)
            response.raise_for_status()

            df = pd.read_csv(io.StringIO(response.text))
            df = _normalise_columns(df)
            return _build_customers(df, "google_sheet")

        except ValueError:
            raise
        except requests.RequestException as exc:
            logger.error("Network error fetching Google Sheet: %s", exc)
            raise ValueError(
                f"Could not fetch Google Sheet — ensure it is publicly shared. ({exc})"
            ) from exc
        except Exception as exc:
            logger.error("Error parsing Google Sheet: %s", exc)
            raise ValueError(f"Failed to process Google Sheet: {exc}") from exc

    # ------------------------------------------------------------------
    # Smart dispatcher — pick parser based on file extension or URL
    # ------------------------------------------------------------------
    @staticmethod
    def parse(
        *,
        file_content: bytes | None = None,
        filename: str | None = None,
        sheet_url: str | None = None,
    ) -> List[Customer]:
        """
        Unified entry point that dispatches to the correct parser.

        Usage:
            # From an uploaded file (CSV or XLSX)
            customers = data_processor_service.parse(
                file_content=raw_bytes, filename="data.xlsx"
            )

            # From a Google Sheet URL
            customers = data_processor_service.parse(
                sheet_url="https://docs.google.com/spreadsheets/d/..."
            )
        """
        if sheet_url:
            return DataProcessorService.parse_google_sheet(sheet_url)

        if file_content is None or filename is None:
            raise ValueError(
                "Provide either (file_content + filename) or sheet_url."
            )

        lower_name = filename.lower()
        if lower_name.endswith(".csv"):
            return DataProcessorService.parse_csv(file_content, source_label=filename)
        elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
            return DataProcessorService.parse_excel(file_content, source_label=filename)
        else:
            raise ValueError(
                f"Unsupported file type '{filename}'. "
                "Please upload a .csv or .xlsx file, or provide a Google Sheets URL."
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_csv_export_url(url: str) -> str:
        """
        Rewrite a Google Sheets sharing/edit URL to a direct CSV export URL.
        Returns the URL unchanged if it already contains ``export?format=csv``.
        """
        if "export?format=csv" in url or "export?format=csv" in url:
            return url

        # Extract the spreadsheet ID and rewrite
        import re
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError(
                "Could not extract a spreadsheet ID from the provided URL. "
                "Please use a valid Google Sheets share link."
            )
        sheet_id = match.group(1)

        # Preserve optional gid (sheet tab)
        gid_match = re.search(r"[?&]gid=(\d+)", url) or re.search(r"#gid=(\d+)", url)
        gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""

        return (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/export?format=csv{gid_param}"
        )


# Module-level singleton
data_processor_service = DataProcessorService()
