import os
import tempfile
from datetime import datetime
from typing import Optional

from core.logger import logger
from core.models import UserResponse
from core.tag_list.parser import TagListParser, ParseResult, TagRow
from core.tag_list.validator import TagListValidator, ValidationResult
from core.tag_list.report import TagListReportGenerator


# ── Point type inference ───────────────────────────────────────────────────────

_POINT_TYPE_MAP = {
    "run_status":   "Digital",
    "fault_status": "Digital",
    "timestamp":    "Timestamp",
    "status":       "String",
}

_POINT_TYPE_SUFFIX = {
    "_mag":   "Float32",
    "_phase": "Float32",
    "_rate":  "Float32",
    "_speed": "Float32",
    "_current": "Float32",
    "_pressure": "Float32",
    "_flow":  "Float32",
    "_temp":  "Float32",
    "_level": "Float32",
}


def infer_point_type(tag_name: str) -> Optional[str]:
    """
    Infer PI point type from the tag name's attribute segment.

    Returns a valid point type string, or None if the attribute
    is not recognised — caller must ask BA before proceeding.

    Resolution order:
        1. Full lowercase tag name checked against compound keys (e.g. run_status)
           — catches multi-word attributes before the single-segment check.
        2. Last segment (attribute name) checked against exact keys.
        3. Full lowercase name checked against suffix patterns.
    """
    full_lower = tag_name.lower()
    attr = tag_name.split("_")[-1].lower() if "_" in tag_name else full_lower

    # Step 1: compound full-name match (e.g. run_status, fault_status, timestamp)
    for key, pt in _POINT_TYPE_MAP.items():
        if key in full_lower:
            return pt

    # Step 2: single last-segment exact match (e.g. status)
    if attr in _POINT_TYPE_MAP:
        return _POINT_TYPE_MAP[attr]

    # Step 3: suffix match (e.g. _mag, _phase, _rate)
    for suffix, pt in _POINT_TYPE_SUFFIX.items():
        if full_lower.endswith(suffix):
            return pt

    return None


# ── Implementor ───────────────────────────────────────────────────────────────

class TagListImplementor:
    """
    Phase 4 orchestrator: create PI tags and link AF attributes.

    Sits between the validator/report layer and the PI service layer.
    Called by app.py after Gate 1 is confirmed by the BA.

    Responsibilities:
        - Run Phases 0–Gate 1 in sequence (parse → validate → pre-action report)
        - After BA confirmation, execute Phase 4 row by row:
            - Final existence check (get_point)
            - create_pi_tag
            - Verify with get_point
            - get_attribute_by_path → set_attribute_value
            - get_stream_value → live data check
        - Annotate each TagRow with Phase 4 results
        - Generate and return the final output report

    GUARDRAILS enforced here:
        G2  — final existence check before every create
        G4  — one tag created per call; caller loops one row at a time
        G7  — no auto-retry on failure
        G9  — this class is only instantiated after Gate 1 is confirmed
        G11 — one create per call enforced by implement_one()
    """

    def __init__(
        self,
        pi_system,
        asset_server,
        asset_database,
        elements,
        attributes,
        data_server,
        points,
        streams,
        af_database_path: str,
        af_root: str = "DataGrid",
        output_dir: str = ".",
    ):
        self.pi          = pi_system
        self.asset_server = asset_server
        self.asset_db     = asset_database
        self.elements     = elements
        self.attributes   = attributes
        self.data_server  = data_server
        self.points       = points
        self.streams      = streams
        self.af_db_path   = af_database_path
        self.af_root      = af_root
        self.output_dir   = output_dir

        self._parser    = TagListParser()
        self._reporter  = TagListReportGenerator()
        self._data_server_web_id: Optional[str] = None

    # ── Public: Phase 0 — session start ──────────────────────────────────────

    def session_start(self) -> dict:
        """
        Phase 0: confirm PI Web API connection and map current AF state.

        Returns a UserResponse-shaped dict with the current element tree,
        or an error dict if any step fails.
        """
        logger.info("Phase 0: session start", exc_info=False)

        # Step 1 — confirm connection
        servers = self.asset_server.lists()
        if not servers or not servers.get("Items"):
            return UserResponse.error(
                message="PI Web API unreachable — no asset servers returned. "
                        "Check credentials and PI_HOST in config.py.",
                code=503
            )

        # Step 2 — get database WebId
        db = self.asset_db.get_by_path(self.af_db_path)
        if not db or not db.get("success", True) is not False:
            return UserResponse.error(
                message=f"Could not retrieve AF database at path: {self.af_db_path}",
                code=404
            )

        # Step 3 — map current AF state
        all_elements = self.pi.get_all_elements(self.af_db_path)
        if not all_elements:
            return UserResponse.error(
                message="get_all_elements returned no data. "
                        "Verify the database path and that the AF hierarchy exists.",
                code=500
            )

        logger.info("Phase 0 complete: PI connection confirmed, AF state loaded.", exc_info=False)
        return UserResponse.success(
            message="Session started. PI Web API reachable and AF state loaded.",
            response=all_elements,
            code=200
        )

    # ── Public: Phases 1–Gate 1 ───────────────────────────────────────────────

    def prepare(self, file_path: str) -> dict:
        """
        Phases 1–Gate 1: parse file, validate, build pre-action report.

        Args:
            file_path: Path to the uploaded tag list file (.xlsx or .csv)

        Returns a UserResponse dict with:
            response = {
                "report_path":      str   — path to the pre-action Excel
                "summary":          dict  — counts for the BA message
                "validation_id":    str   — key to retrieve ValidationResult later
            }

        The ValidationResult is stored on self._pending so implement()
        can pick it up after BA confirmation. Only one pending validation
        is held at a time — calling prepare() again replaces it.
        """
        logger.info(f"Phase 1–3: preparing tag list from {file_path}", exc_info=False)

        # Phase 2 — parse
        parse_result = self._parser.parse(file_path)
        if not parse_result.success:
            return UserResponse.error(
                message=parse_result.error_message,
                code=400
            )

        # Phase 3 — validate against live PI
        validator = TagListValidator(
            elements=self.elements,
            points=self.points,
            pi_system=self.pi
        )
        vr = validator.validate(parse_result, self.af_db_path, self.af_root)
        if not vr.success:
            return UserResponse.error(
                message=vr.error_message,
                code=500
            )

        # Build pre-action report
        report_path = self._reporter.pre_action_report(
            vr, output_dir=self.output_dir
        )

        # Stash for implement()
        self._pending_vr   = vr
        self._pending_path = report_path

        summary = vr.summary()
        logger.info(f"Pre-action report ready: {report_path}", exc_info=False)

        return UserResponse.success(
            message=(
                f"Pre-action report ready. "
                f"{summary['Tags to create']} tags to create, "
                f"{summary['Tags already existing']} already exist, "
                f"{summary['Naming violations']} naming violations, "
                f"{summary['AF elements missing']} AF elements missing. "
                f"Report saved to: {report_path}"
            ),
            response={
                "report_path":   report_path,
                "summary":       summary,
            },
            code=200
        )

    # ── Public: Phase 4 — implement one tag ───────────────────────────────────

    def implement_one(self, tag_name: str, data_server_web_id: str) -> dict:
        """
        Phase 4, Step 4.1: create one PI tag and verify it.

        Implements GUARDRAILS G11 — one tag per call.
        Must be called once per CREATE row after Gate 1 is confirmed.

        Args:
            tag_name:            The Proposed New Tagname to create
            data_server_web_id:  WebId of the target PI Data Server

        Returns a UserResponse dict describing the outcome for this tag.
        The corresponding TagRow in self._pending_vr is annotated in place.
        """
        if not hasattr(self, "_pending_vr"):
            return UserResponse.error(
                message="No pending validation result. Run prepare() first.",
                code=400
            )

        row = self._find_row(tag_name)
        if not row:
            return UserResponse.error(
                message=f"Tag '{tag_name}' not found in pending validation result.",
                code=404
            )

        if row.proposed_action != "TO_CREATE" and row.proposed_action != "CREATE":
            return UserResponse.error(
                message=f"Tag '{tag_name}' is not marked for creation "
                        f"(current action: {row.proposed_action}). Skipping.",
                code=400
            )

        # ── G2: final existence check ──────────────────────────────────────
        existing = self.points.get(tag_name)
        if isinstance(existing, dict) and existing.get("success"):
            row.final_status    = "ALREADY EXISTED"
            row.pi_tag_created  = "No"
            row.error_detail    = "Tag found on final pre-create check — skipped."
            logger.info(f"Tag '{tag_name}' already exists — skipping create.", exc_info=False)
            return UserResponse.success(
                message=f"Tag '{tag_name}' already exists. Marked as ALREADY EXISTED.",
                response={"tag_name": tag_name, "final_status": "ALREADY EXISTED"},
                code=200
            )

        # ── Infer point type ───────────────────────────────────────────────
        point_type = infer_point_type(tag_name)
        if not point_type:
            row.final_status  = "FAILED"
            row.pi_tag_created = "No"
            row.error_detail  = (
                f"Cannot infer point type for tag '{tag_name}'. "
                "BA must specify point_type manually."
            )
            logger.error(row.error_detail, exc_info=False)
            return UserResponse.error(
                message=row.error_detail,
                code=400
            )

        # ── create_pi_tag ──────────────────────────────────────────────────
        create_resp = self.data_server.create_point(
            web_id=data_server_web_id,
            name=tag_name,
            point_type=point_type,
            descriptor=row.description,
            engineering_units=row.eng_units,
        )

        if not isinstance(create_resp, dict) or not create_resp.get("success"):
            code = create_resp.get("code", "?") if isinstance(create_resp, dict) else "?"
            msg  = create_resp.get("message", "Unknown error") if isinstance(create_resp, dict) else str(create_resp)
            row.final_status   = "FAILED"
            row.pi_tag_created = "No"
            row.error_detail   = f"create_pi_tag failed [{code}]: {msg}"
            logger.error(row.error_detail, exc_info=False)
            return UserResponse.error(message=row.error_detail, code=code)

        # ── Verify with get_point ──────────────────────────────────────────
        verify = self.points.get(tag_name)
        if not isinstance(verify, dict) or not verify.get("success"):
            row.final_status   = "FAILED"
            row.pi_tag_created = "No"
            row.error_detail   = f"Tag '{tag_name}' not found after create — verify manually."
            logger.error(row.error_detail, exc_info=False)
            return UserResponse.error(message=row.error_detail, code=500)

        row.final_status   = "CREATED"
        row.pi_tag_created = "Yes"
        logger.info(f"Tag '{tag_name}' created and verified.", exc_info=False)

        return UserResponse.success(
            message=f"Tag '{tag_name}' created successfully ({point_type}).",
            response={
                "tag_name":   tag_name,
                "point_type": point_type,
                "final_status": "CREATED",
            },
            code=201
        )

    # ── Public: Phase 4, Step 4.2 — link one AF attribute ────────────────────

    def link_attribute(self, tag_name: str) -> dict:
        """
        Phase 4, Step 4.2: link the AF attribute to the PI tag and verify
        live data is flowing.

        Args:
            tag_name: The PI tag name (used to look up the TagRow and
                      build the attribute path)

        Returns a UserResponse dict describing the link outcome.
        The TagRow is annotated in place.
        """
        if not hasattr(self, "_pending_vr"):
            return UserResponse.error(
                message="No pending validation result. Run prepare() first.",
                code=400
            )

        row = self._find_row(tag_name)
        if not row:
            return UserResponse.error(
                message=f"Tag '{tag_name}' not found in pending validation result.",
                code=404
            )

        if row.final_status != "CREATED":
            row.af_attribute_linked = "N/A"
            row.live_data_received  = "Not checked"
            return UserResponse.success(
                message=f"Tag '{tag_name}' was not created — skipping attribute link.",
                response={"tag_name": tag_name, "af_attribute_linked": "N/A"},
                code=200
            )

        # Build attribute path from the tag row's plant/unit/attribute name
        attr_name  = tag_name.split("_")[-1] if "_" in tag_name else tag_name
        attr_path  = (
            f"{self.af_db_path}\\{self.af_root}"
            f"\\{row.plant}\\{row.unit_system}|{attr_name}"
        )

        # ── get_attribute_by_path ──────────────────────────────────────────
        attr_resp = self.attributes.get_by_path(attr_path)
        if not isinstance(attr_resp, dict) or not attr_resp.get("success"):
            row.af_attribute_linked = "No"
            row.live_data_received  = "Not checked"
            row.error_detail        = f"Attribute not found at path: {attr_path}"
            logger.error(row.error_detail, exc_info=False)
            return UserResponse.error(message=row.error_detail, code=404)

        attr_payload = attr_resp.get("response", {})
        attr_web_id  = attr_payload.get("WebId") if isinstance(attr_payload, dict) else None

        if not attr_web_id:
            row.af_attribute_linked = "No"
            row.error_detail        = f"Could not extract WebId from attribute at: {attr_path}"
            return UserResponse.error(message=row.error_detail, code=500)

        # ── Confirm not already linked ─────────────────────────────────────
        if (isinstance(attr_payload, dict) and
                attr_payload.get("DataReferencePlugIn") == "PI Point"):
            row.af_attribute_linked = "Yes"
            logger.info(f"Attribute '{attr_path}' already linked to PI Point.", exc_info=False)
        else:
            # ── set_attribute_value ────────────────────────────────────────
            set_resp = self.attributes.set_value(attr_web_id, tag_name)
            if not isinstance(set_resp, dict) or not set_resp.get("success"):
                code = set_resp.get("code", "?") if isinstance(set_resp, dict) else "?"
                msg  = set_resp.get("message", "Unknown error") if isinstance(set_resp, dict) else str(set_resp)
                row.af_attribute_linked = "No"
                row.error_detail        = f"set_attribute_value failed [{code}]: {msg}"
                logger.error(row.error_detail, exc_info=False)
                return UserResponse.error(message=row.error_detail, code=code)

            row.af_attribute_linked = "Yes"
            logger.info(f"Attribute '{attr_path}' linked to tag '{tag_name}'.", exc_info=False)

        # ── get_stream_value — live data check ─────────────────────────────
        stream_resp = self.streams.get_value(attr_web_id)
        if not isinstance(stream_resp, dict) or not stream_resp.get("success"):
            row.live_data_received = "No"
            logger.info(f"No live data for '{tag_name}' — tag may not be sending yet.", exc_info=False)
        else:
            payload = stream_resp.get("response", {})
            value   = payload.get("Value") if isinstance(payload, dict) else None
            row.live_data_received = "No" if value in (None, "No Data", "No data") else "Yes"

        return UserResponse.success(
            message=(
                f"Attribute '{attr_name}' linked to tag '{tag_name}'. "
                f"Live data: {row.live_data_received}."
            ),
            response={
                "tag_name":             tag_name,
                "af_attribute_linked":  row.af_attribute_linked,
                "live_data_received":   row.live_data_received,
            },
            code=200
        )

    # ── Public: Phase 5 — generate output report ──────────────────────────────

    def finalize(self) -> dict:
        """
        Phase 5: generate and return the final output report.

        Requires that implement_one() and link_attribute() have been called
        for all CREATE rows. Rows not yet processed will have empty Phase 4
        fields and appear with blank Final Status in the report.

        Returns a UserResponse dict with the path to the output Excel file.
        """
        if not hasattr(self, "_pending_vr"):
            return UserResponse.error(
                message="No pending validation result. Run prepare() first.",
                code=400
            )

        report_path = self._reporter.output_report(
            self._pending_vr,
            af_database_path=self.af_db_path,
            output_dir=self.output_dir
        )

        summary = self._pending_vr.summary()
        created  = sum(1 for r in self._pending_vr.all_rows if r.final_status == "CREATED")
        failed   = sum(1 for r in self._pending_vr.all_rows if r.final_status == "FAILED")
        skipped  = sum(1 for r in self._pending_vr.all_rows if r.final_status in ("SKIPPED", "ALREADY EXISTED", ""))

        logger.info(f"Phase 5: output report saved to {report_path}", exc_info=False)

        return UserResponse.success(
            message=(
                f"Session complete. Output report saved. "
                f"{created} tags created, {failed} failed, {skipped} skipped. "
                f"Report: {report_path}"
            ),
            response={
                "report_path": report_path,
                "created":     created,
                "failed":      failed,
                "skipped":     skipped,
            },
            code=200
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _find_row(self, tag_name: str) -> Optional[TagRow]:
        """Find a TagRow by proposed_tagname in the pending ValidationResult."""
        if not hasattr(self, "_pending_vr"):
            return None
        for row in self._pending_vr.all_rows:
            if row.proposed_tagname == tag_name:
                return row
        return None