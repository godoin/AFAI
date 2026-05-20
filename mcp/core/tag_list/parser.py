import re
import pandas as pd
from pathlib import Path
from typing import Optional

from core.logger import logger
from core.models import UserResponse


# ── Column definitions ─────────────────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "Plant",
    "Unit/System",
    "Source Tagname",
    "Source Tag",
    "Proposed New Tagname",
]

OPTIONAL_COLUMNS = [
    "Canary Tag Path",
    "Description",
    "eng_units",
    "Date Added",
    "Data Tag Naming for Checking (Remarks)",
]

ALL_EXPECTED_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Naming convention: alphanumeric + underscore only, no spaces, min 3 parts
_TAG_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')
_MIN_PARTS   = 3   # Location_Plant_Unit at minimum (attribute appended)


# ── Result dataclasses ─────────────────────────────────────────────────────────

class TagRow:
    """
    Represents one parsed and validated row from the tag list file.

    Attributes:
        row_number          1-based row number in the source file (excl. header)
        plant               Plant column value
        unit_system         Unit/System column value
        source_tagname      Source Tagname column value
        source_tag          Source Tag column value
        proposed_tagname    Proposed New Tagname column value
        canary_tag_path     Optional
        description         Optional
        eng_units           Optional
        date_added          Optional
        remarks             Optional
        naming_valid        True if proposed_tagname passed all naming checks
        naming_violation    Violation message string, or None if valid
        proposed_action     One of: TO_CREATE / NAMING_VIOLATION /
                            AF_ELEMENT_MISSING / TAG_ALREADY_EXISTS
                            (AF/PI statuses are set later in Phase 3)
        exists_in_pi        "Yes" / "No" / "Not checked"
        exists_in_af        "Yes" / "No" / "Not checked"
        error_detail        Free-text error string for the output report
    """

    __slots__ = [
        "row_number", "plant", "unit_system", "source_tagname", "source_tag",
        "proposed_tagname", "canary_tag_path", "description", "eng_units",
        "date_added", "remarks",
        "naming_valid", "naming_violation",
        "proposed_action", "exists_in_pi", "exists_in_af", "error_detail",
        # Phase 4 — populated by implementation step, defaults to "" until then
        "final_status", "pi_tag_created", "af_attribute_linked",
        "live_data_received",
    ]

    def __init__(
        self,
        row_number: int,
        plant: str,
        unit_system: str,
        source_tagname: str,
        source_tag: str,
        proposed_tagname: str,
        canary_tag_path: str = "",
        description: str = "",
        eng_units: str = "",
        date_added: str = "",
        remarks: str = "",
    ):
        self.row_number       = row_number
        self.plant            = plant
        self.unit_system      = unit_system
        self.source_tagname   = source_tagname
        self.source_tag       = source_tag
        self.proposed_tagname = proposed_tagname
        self.canary_tag_path  = canary_tag_path
        self.description      = description
        self.eng_units        = eng_units
        self.date_added       = date_added
        self.remarks          = remarks

        # Set by validator
        self.naming_valid     = True
        self.naming_violation = None

        # Set by Phase 3 (defaults here)
        self.proposed_action  = "TO_CREATE"
        self.exists_in_pi     = "Not checked"
        self.exists_in_af     = "Not checked"
        self.error_detail     = ""

        # Set by Phase 4 (defaults here — empty until implementation runs)
        self.final_status        = ""
        self.pi_tag_created      = ""
        self.af_attribute_linked = ""
        self.live_data_received  = ""

    def to_dict(self) -> dict:
        return {
            "Row #":                                  self.row_number,
            "Plant":                                  self.plant,
            "Unit/System":                            self.unit_system,
            "Source Tagname":                         self.source_tagname,
            "Source Tag":                             self.source_tag,
            "Proposed New Tagname":                   self.proposed_tagname,
            "Canary Tag Path":                        self.canary_tag_path,
            "Description":                            self.description,
            "eng_units":                              self.eng_units,
            "Date Added":                             self.date_added,
            "Data Tag Naming for Checking (Remarks)": self.remarks,
            "Naming Valid":   "Yes" if self.naming_valid else f"No — {self.naming_violation}",
            "Exists in PI":   self.exists_in_pi,
            "Exists in AF":   self.exists_in_af,
            "Proposed Action": self.proposed_action,
            "BA Notes":       "",
            "Error Detail":   self.error_detail,
        }


class ParseResult:
    """
    Container returned by TagListParser.parse().

    Attributes:
        success             False if file could not be read or required columns
                            are missing — caller should stop and surface to BA.
        missing_columns     List of required column names not found in the file.
        valid_rows          TagRow objects that passed naming validation.
        violation_rows      TagRow objects that failed naming validation.
        total_rows          Total data rows read (excluding header).
        error_message       Human-readable failure reason when success=False.
    """

    def __init__(self):
        self.success         = True
        self.missing_columns = []
        self.valid_rows      = []
        self.violation_rows  = []
        self.total_rows      = 0
        self.error_message   = ""

    @property
    def all_rows(self) -> list:
        """All rows in original file order regardless of validation status."""
        combined = self.valid_rows + self.violation_rows
        return sorted(combined, key=lambda r: r.row_number)

    def summary(self) -> dict:
        return {
            "Total rows in file":       self.total_rows,
            "Rows passing validation":  len(self.valid_rows),
            "Naming violations":        len(self.violation_rows),
            "Rows skipped (total)":     len(self.violation_rows),
        }


# ── Parser ─────────────────────────────────────────────────────────────────────

class TagListParser:
    """
    Phase 2 service: parse a client tag list file and run naming validation.

    Responsibilities:
        - Accept Excel (.xlsx, .xls) or CSV (.csv) files
        - Validate that all required columns are present
        - Run naming convention checks on every row (Step 2.2)
        - Return a ParseResult for Phase 3 to consume

    Does NOT call any PI Web API — this is entirely offline.
    PI cross-checks (AF element existence, tag existence) happen in Phase 3.

    Usage:
        parser = TagListParser()
        result = parser.parse("path/to/taglist.xlsx")
        if not result.success:
            # surface result.error_message to BA and stop
        # proceed to Phase 3 with result.valid_rows
    """

    def __init__(self):
        pass

    # ── Public ────────────────────────────────────────────────────────────────

    def parse(self, file_path: str) -> ParseResult:
        """
        Parse the file at file_path and return a ParseResult.

        Steps:
            1. Read the file into a DataFrame
            2. Normalise column names (strip whitespace)
            3. Check required columns are present — fail fast if any missing
            4. Iterate rows and run naming validation on each
        """
        result = ParseResult()
        path   = Path(file_path)

        # ── Step 1: Read file ──────────────────────────────────────────────
        df = self._read_file(path, result)
        if not result.success:
            return result

        # ── Step 2: Normalise columns ──────────────────────────────────────
        df.columns = [str(c).strip() for c in df.columns]

        # ── Step 3: Check required columns ────────────────────────────────
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            result.success         = False
            result.missing_columns = missing
            result.error_message   = (
                f"The file is missing the following required columns: "
                f"{', '.join(missing)}. "
                f"Cannot proceed until these are present."
            )
            logger.error(result.error_message, exc_info=False)
            return result

        # ── Step 4: Parse and validate rows ───────────────────────────────
        result.total_rows = len(df)

        for idx, row in df.iterrows():
            row_number = int(idx) + 2   # +2: 1-based + header row

            tag_row = TagRow(
                row_number     = row_number,
                plant          = self._str(row, "Plant"),
                unit_system    = self._str(row, "Unit/System"),
                source_tagname = self._str(row, "Source Tagname"),
                source_tag     = self._str(row, "Source Tag"),
                proposed_tagname = self._str(row, "Proposed New Tagname"),
                canary_tag_path  = self._str(row, "Canary Tag Path"),
                description      = self._str(row, "Description"),
                eng_units        = self._str(row, "eng_units"),
                date_added       = self._str(row, "Date Added"),
                remarks          = self._str(row, "Data Tag Naming for Checking (Remarks)"),
            )

            self._validate_naming(tag_row)

            if tag_row.naming_valid:
                result.valid_rows.append(tag_row)
            else:
                tag_row.proposed_action = "SKIP — naming violation"
                result.violation_rows.append(tag_row)
                logger.info(
                    f"Row {row_number}: naming violation — "
                    f"'{tag_row.proposed_tagname}' — {tag_row.naming_violation}",
                    exc_info=False
                )

        logger.info(
            f"Parsed '{path.name}': {result.total_rows} rows total, "
            f"{len(result.valid_rows)} valid, "
            f"{len(result.violation_rows)} violations.",
            exc_info=False
        )
        return result

    # ── Private: file reading ─────────────────────────────────────────────────

    def _read_file(self, path: Path, result: ParseResult) -> Optional[pd.DataFrame]:
        """Read Excel or CSV into a DataFrame. Sets result.success=False on failure."""
        suffix = path.suffix.lower()
        try:
            if suffix in (".xlsx", ".xls"):
                return pd.read_excel(path, dtype=str).fillna("")
            elif suffix == ".csv":
                return pd.read_csv(path, dtype=str).fillna("")
            else:
                result.success       = False
                result.error_message = (
                    f"Unsupported file type '{suffix}'. "
                    f"Please provide an .xlsx, .xls, or .csv file."
                )
                logger.error(result.error_message, exc_info=False)
                return None
        except Exception as e:
            result.success       = False
            result.error_message = f"Failed to read file '{path.name}': {e}"
            logger.error(result.error_message, exc_info=False)
            return None

    # ── Private: naming validation ────────────────────────────────────────────

    def _validate_naming(self, tag_row: TagRow) -> None:
        """
        Run all four naming convention checks against tag_row.proposed_tagname.
        Sets tag_row.naming_valid and tag_row.naming_violation in place.

        Rules (all four must pass):
            1. No whitespace anywhere in the tag name
            2. Only alphanumeric characters and underscores
            3. At least Location_Plant_Unit segments (min 3 underscore-separated parts)
            4. Tag name is not empty
        """
        name = tag_row.proposed_tagname

        # Rule 0: not empty
        if not name:
            tag_row.naming_valid     = False
            tag_row.naming_violation = "Tag name is empty"
            return

        # Rule 1: no whitespace
        if re.search(r'\s', name):
            tag_row.naming_valid     = False
            tag_row.naming_violation = "Contains whitespace — use underscores only"
            return

        # Rule 2: alphanumeric + underscore only
        if not _TAG_PATTERN.match(name):
            invalid_chars = sorted(set(re.findall(r'[^A-Za-z0-9_]', name)))
            tag_row.naming_valid     = False
            tag_row.naming_violation = (
                f"Contains invalid characters: {' '.join(invalid_chars)}"
            )
            return

        # Rule 3: minimum segment count (Location_Plant_Unit_Attribute = 4 parts,
        # but we enforce >= 3 to allow client variations — the AF match in Phase 3
        # will catch structural mismatches against the live hierarchy)
        parts = name.split("_")
        if len(parts) < _MIN_PARTS:
            tag_row.naming_valid     = False
            tag_row.naming_violation = (
                f"Too few segments ({len(parts)}) — expected at least "
                f"Location_Plant_Unit (3 parts separated by underscores)"
            )
            return

        # All rules passed
        tag_row.naming_valid     = True
        tag_row.naming_violation = None

    # ── Private: helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _str(row: pd.Series, col: str) -> str:
        """Safely extract a column value as a stripped string, or '' if missing."""
        if col not in row.index:
            return ""
        val = row[col]
        return str(val).strip() if val else ""