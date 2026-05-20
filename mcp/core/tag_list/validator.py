from dataclasses import dataclass, field
from typing import Optional

from core.logger import logger
from core.models import UserResponse
from core.tag_list.parser import ParseResult, TagRow


# ── Result container ───────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """
    Output of TagListValidator.validate().

    Carries all rows with their PI and AF statuses resolved,
    plus the summary counts used for the pre-action report Summary sheet.

    Attributes:
        success             False if PI Web API was unreachable during checks.
        error_message       Populated when success=False.
        to_create           Rows confirmed non-existent in PI — safe to create.
        already_exist       Rows whose proposed tagname already exists in PI.
        af_missing          Rows whose parent AF element was not found.
        naming_violations   Passed through from ParseResult unchanged.
        all_rows            Every row in original file order (all categories).
    """
    success:            bool       = True
    error_message:      str        = ""
    to_create:          list       = field(default_factory=list)
    already_exist:      list       = field(default_factory=list)
    af_missing:         list       = field(default_factory=list)
    naming_violations:  list       = field(default_factory=list)

    @property
    def all_rows(self) -> list:
        combined = (
            self.to_create +
            self.already_exist +
            self.af_missing +
            self.naming_violations
        )
        return sorted(combined, key=lambda r: r.row_number)

    def summary(self) -> dict:
        skipped = (
            len(self.already_exist) +
            len(self.af_missing) +
            len(self.naming_violations)
        )
        return {
            "Total rows in file":      self._total(),
            "Rows passing validation": len(self.to_create) + len(self.already_exist) + len(self.af_missing),
            "Tags to create":          len(self.to_create),
            "Tags already existing":   len(self.already_exist),
            "AF elements missing":     len(self.af_missing),
            "Naming violations":       len(self.naming_violations),
            "Rows skipped (total)":    skipped,
        }

    def _total(self) -> int:
        return (
            len(self.to_create) +
            len(self.already_exist) +
            len(self.af_missing) +
            len(self.naming_violations)
        )


# ── Validator ──────────────────────────────────────────────────────────────────

class TagListValidator:
    """
    Phase 3 service: cross-check parsed tag rows against live PI System.

    Responsibilities:
        Step 3.1 — Verify parent AF element exists for each valid row
                   via get_element_by_path (Elements service)
        Step 3.2 — Verify proposed tagname does not already exist in PI
                   Data Archive via search_points (Points service),
                   falling back to get_point for individual confirmation
        Step 3.3 — Assign final proposed_action and exists_in_pi/af
                   fields on each TagRow

    Does NOT write anything to PI System.
    Does NOT build the Excel report — that is the responsibility of
    the report module (Phase 3.3 / Gate 1).

    Separation from the parser:
        TagListParser   — offline, no network, pure file + naming logic
        TagListValidator — requires live PI Web API, calls service layer

    Usage:
        from services.pi_system.elements import Elements
        from services.pi_system.points import Points
        from core.tag_list.validator import TagListValidator

        validator = TagListValidator(elements=elements, points=points, pi_system=pi)
        result = validator.validate(parse_result, af_database_path, pi_server)
    """

    def __init__(self, elements, points, pi_system):
        """
        Args:
            elements:   Initialised Elements service instance
            points:     Initialised Points service instance
            pi_system:  Initialised PISystem base instance (for pi_server name)
        """
        self.elements   = elements
        self.points     = points
        self.pi_system  = pi_system

    # ── Public ────────────────────────────────────────────────────────────────

    def validate(
        self,
        parse_result: ParseResult,
        af_database_path: str,
        af_root: str = "DataGrid",
    ) -> ValidationResult:
        """
        Run Phase 3 cross-checks against live PI System.

        Args:
            parse_result:       Output of TagListParser.parse()
            af_database_path:   Full AF database path
                                e.g. \\\\PI-SYSTEM\\GoogleManualLogger
            af_root:            Root element under the database that contains
                                the hierarchy. Default "DataGrid".

        Returns:
            ValidationResult with all rows categorised and annotated.
        """
        result = ValidationResult()

        # Pass naming violations through — no PI checks needed for these
        result.naming_violations = parse_result.violation_rows

        if not parse_result.valid_rows:
            logger.info("No valid rows to validate against PI System.", exc_info=False)
            return result

        # ── Step 3.1: Build unique AF element paths and check existence ────
        af_status = self._check_af_elements(
            parse_result.valid_rows,
            af_database_path,
            af_root,
            result
        )
        if not result.success:
            return result

        # ── Step 3.2: Bulk search for existing PI tags ─────────────────────
        existing_tags = self._bulk_check_pi_tags(parse_result.valid_rows, result)
        if not result.success:
            return result

        # ── Step 3.3: Assign final proposed_action per row ─────────────────
        for row in parse_result.valid_rows:
            af_exists = af_status.get(self._af_key(row), False)
            pi_exists = row.proposed_tagname in existing_tags

            row.exists_in_af = "Yes" if af_exists else "No"
            row.exists_in_pi = "Yes" if pi_exists else "No"

            if not af_exists:
                row.proposed_action = "SKIP — AF element missing"
                result.af_missing.append(row)
            elif pi_exists:
                row.proposed_action = "SKIP — already exists"
                result.already_exist.append(row)
            else:
                row.proposed_action = "CREATE"
                result.to_create.append(row)

        logger.info(
            f"Validation complete: "
            f"{len(result.to_create)} to create, "
            f"{len(result.already_exist)} already exist, "
            f"{len(result.af_missing)} AF missing, "
            f"{len(result.naming_violations)} naming violations.",
            exc_info=False
        )
        return result

    # ── Private: AF element checks ────────────────────────────────────────────

    def _check_af_elements(
        self,
        rows: list,
        af_database_path: str,
        af_root: str,
        result: ValidationResult,
    ) -> dict:
        """
        Check AF element existence for every unique Plant + Unit/System
        combination in the valid rows.

        Deduplicates paths so each unique element is only looked up once,
        regardless of how many tags belong to it.

        Returns:
            dict mapping af_key → bool (True = element found in AF)
        """
        # Collect unique (plant, unit) combinations
        unique_paths = {}
        for row in rows:
            key = self._af_key(row)
            if key not in unique_paths:
                unique_paths[key] = self._build_af_path(
                    row, af_database_path, af_root
                )

        af_status = {}
        for key, path in unique_paths.items():
            found = self._element_exists(path, result)
            if not result.success:
                return {}
            af_status[key] = found
            status = "found" if found else "NOT FOUND"
            logger.info(f"AF check — {path}: {status}", exc_info=False)

        return af_status

    def _element_exists(self, path: str, result: ValidationResult) -> bool:
        """
        Call get_element_by_path and return True if the element exists.
        Sets result.success=False only on a hard API failure (not on 404).
        """
        try:
            response = self.elements.get_by_path(path)

            if isinstance(response, dict):
                code = response.get("code", "")
                if not response.get("success", True):
                    # 404 = element does not exist — not a hard failure
                    if str(code) == "404":
                        return False
                    # 401/500 = genuine API problem — stop everything
                    if str(code) in ("401", "500"):
                        result.success       = False
                        result.error_message = response.get("message", "PI Web API error during AF check.")
                        return False
                    return False
                return True

            return response is not None

        except Exception as e:
            logger.error(f"Unexpected error during AF element check: {e}", exc_info=False)
            result.success       = False
            result.error_message = f"Unexpected error during AF element check: {e}"
            return False

    # ── Private: PI tag checks ────────────────────────────────────────────────

    def _bulk_check_pi_tags(
        self,
        rows: list,
        result: ValidationResult,
    ) -> set:
        """
        Use search_points to bulk-check which proposed tagnames already exist
        in PI Data Archive.

        Strategy:
            1. Collect all unique proposed tagnames from valid rows.
            2. Group them by their first segment (Location/Plant prefix) so
               each search query is scoped and stays under 1000 results.
            3. For any tagname that search_points returns, mark as existing.
            4. Fall back to individual get_point calls for any tagname that
               could not be confirmed by search (e.g. unusual naming that
               defeats the prefix pattern).

        Returns:
            set of tagnames confirmed to already exist in PI Data Archive.
        """
        existing = set()
        all_tagnames = {row.proposed_tagname for row in rows}

        # Group by first segment to keep search queries focused
        prefix_groups = {}
        for name in all_tagnames:
            prefix = name.split("_")[0]
            prefix_groups.setdefault(prefix, set()).add(name)

        for prefix, names in prefix_groups.items():
            query = f"Tag:={prefix}_*"
            found_in_search = self._search_tags(query, result)
            if not result.success:
                return set()

            # Intersect search results with what we're looking for
            matched = names & found_in_search
            existing.update(matched)

            # For names not covered by search, fall back to individual check
            unchecked = names - found_in_search - matched
            for name in unchecked:
                exists = self._point_exists(name, result)
                if not result.success:
                    return set()
                if exists:
                    existing.add(name)

        return existing

    def _search_tags(self, query: str, result: ValidationResult) -> set:
        """
        Call search_points and return a set of tag names from the results.
        Returns empty set on 404 (no tags matched) without failing.
        """
        try:
            response = self.points.search(query=query, max_count=1000)

            if isinstance(response, dict):
                if not response.get("success", True):
                    code = response.get("code", "")
                    if code == 404 or str(code) == "404":
                        return set()
                    if code in (401, 500) or str(code) in ("401", "500"):
                        result.success       = False
                        result.error_message = response.get("message", "PI Web API error during tag search.")
                        return set()
                    return set()

                payload = response.get("response", {})
                items   = payload.get("Items", []) if isinstance(payload, dict) else []
                return {item.get("Name", "") for item in items if item.get("Name")}

            return set()

        except Exception as e:
            logger.error(f"Unexpected error during tag search '{query}': {e}", exc_info=False)
            result.success       = False
            result.error_message = f"Unexpected error during tag search: {e}"
            return set()

    def _point_exists(self, tag_name: str, result: ValidationResult) -> bool:
        """
        Individual get_point fallback for tags not covered by search_points.
        Returns True if the tag exists, False if not found.
        """
        try:
            response = self.points.get(tag_name)

            if isinstance(response, dict):
                if not response.get("success", True):
                    code = response.get("code", "")
                    if code == 404 or str(code) == "404":
                        return False
                    if code in (401, 500) or str(code) in ("401", "500"):
                        result.success       = False
                        result.error_message = response.get("message", "PI Web API error during point lookup.")
                        return False
                    return False
                return True

            return response is not None

        except Exception as e:
            logger.error(f"Unexpected error checking point '{tag_name}': {e}", exc_info=False)
            result.success       = False
            result.error_message = f"Unexpected error checking point: {e}"
            return False

    # ── Private: path helpers ─────────────────────────────────────────────────

    @staticmethod
    def _af_key(row: TagRow) -> str:
        """Unique key for deduplicating AF element lookups."""
        return f"{row.plant}|{row.unit_system}"

    @staticmethod
    def _build_af_path(row: TagRow, af_database_path: str, af_root: str) -> str:
        """
        Build the full AF element path for a given row's Plant + Unit/System.

        The database path already contains the server and database name.
        We append af_root + plant + unit to form the full element path.

        Example input:
            af_database_path = "PI-SYSTEM/GoogleManualLogger"
            af_root          = "DataGrid"
            row.plant        = "DBNPA N7320"
            row.unit_system  = "Dosing Pump A"

        Example output:
            "PI-SYSTEM/GoogleManualLogger/DataGrid/DBNPA N7320/Dosing Pump A"
        """
        # Strip leading slashes from the database path for the elements endpoint
        db = af_database_path.lstrip("\\")
        return f"{db}\\{af_root}\\{row.plant}\\{row.unit_system}"