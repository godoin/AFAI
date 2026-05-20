"""
test_implementor.py — unit tests for core.tag_list.implementor

Run:  pytest tests/test_implementor.py -v
"""

import os
import pytest

from core.tag_list.implementor import TagListImplementor, infer_point_type
from tests.conftest import (
    MockAssetServer, MockAssetDB, MockPISystem,
    MockElements, MockAttributes, MockPoints,
    MockDataServer, MockStreams,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════════

def make_implementor(
    tmp_path,
    existing_plants=None,
    existing_tags=None,
    ds_fail=False,
    no_live_data=False,
    already_linked=False,
    fail_set_attr=False,
):
    mp = MockPoints(existing_tags or [])
    return TagListImplementor(
        pi_system     = MockPISystem(),
        asset_server  = MockAssetServer(),
        asset_database= MockAssetDB(),
        elements      = MockElements(existing_plants or {"PlantA", "PlantB"}),
        attributes    = MockAttributes(already_linked=already_linked, fail_set=fail_set_attr),
        data_server   = MockDataServer(mp, fail=ds_fail),
        points        = mp,
        streams       = MockStreams(no_data=no_live_data),
        af_database_path = r"\\PI-SYSTEM\GoogleManualLogger",
        output_dir    = str(tmp_path),
    ), mp


# ═══════════════════════════════════════════════════════════════════════════════
# infer_point_type
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferPointType:

    @pytest.mark.parametrize("tag_name,expected", [
        ("Loc_Plant_Unit_Status",           "String"),
        ("Loc_Plant_Unit_Run_Status",       "Digital"),
        ("Loc_Plant_Unit_Fault_Status",     "Digital"),
        ("Loc_Plant_Unit_Timestamp",        "Timestamp"),
        ("Loc_Plant_Unit_VA_Mag",           "Float32"),
        ("Loc_Plant_Unit_VA_Phase",         "Float32"),
        ("Loc_Plant_Unit_Flow_Rate",        "Float32"),
        ("Loc_Plant_Unit_Discharge_Pressure","Float32"),
        ("Loc_Plant_Unit_Motor_Current",    "Float32"),
        ("Loc_Plant_Unit_Stroke_Speed",     "Float32"),
    ])
    def test_known_types(self, tag_name, expected):
        assert infer_point_type(tag_name) == expected

    def test_unknown_returns_none(self):
        assert infer_point_type("Plant_Unit_Sys_Widget") is None
        assert infer_point_type("Loc_Plant_Unknown")     is None

    def test_run_status_takes_priority_over_status(self):
        # "run_status" contains "status" — must resolve to Digital not String
        assert infer_point_type("A_B_C_Run_Status") == "Digital"

    def test_fault_status_takes_priority_over_status(self):
        assert infer_point_type("A_B_C_Fault_Status") == "Digital"


# ═══════════════════════════════════════════════════════════════════════════════
# session_start
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStart:

    def test_returns_success_when_pi_reachable(self, tmp_path):
        imp, _ = make_implementor(tmp_path)
        r = imp.session_start()
        assert r["success"] is True
        assert "AF state loaded" in r["message"]

    def test_fails_when_no_asset_servers(self, tmp_path):
        class NoServers:
            def lists(self): return {"Items": []}

        imp, _ = make_implementor(tmp_path)
        imp.asset_server = NoServers()
        r = imp.session_start()
        assert r["success"] is False
        assert "unreachable" in r["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# prepare
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrepare:

    def test_returns_success_with_report_path(self, tmp_path, valid_taglist_file):
        imp, _ = make_implementor(tmp_path)
        r = imp.prepare(valid_taglist_file)
        assert r["success"] is True
        assert "report_path" in r["response"]
        assert os.path.exists(r["response"]["report_path"])

    def test_summary_in_response(self, tmp_path, valid_taglist_file):
        imp, _ = make_implementor(tmp_path)
        r = imp.prepare(valid_taglist_file)
        s = r["response"]["summary"]
        assert s["Tags to create"]  == 5
        assert s["Naming violations"] == 0

    def test_fails_on_missing_columns(self, tmp_path, missing_columns_file):
        imp, _ = make_implementor(tmp_path)
        r = imp.prepare(missing_columns_file)
        assert r["success"] is False
        assert r["code"] == 400

    def test_fails_on_bad_file_type(self, tmp_path, tmp_path_factory):
        bad = tmp_path / "data.pdf"
        bad.write_bytes(b"not a pdf")
        imp, _ = make_implementor(tmp_path)
        r = imp.prepare(str(bad))
        assert r["success"] is False

    def test_pending_vr_set_after_prepare(self, tmp_path, valid_taglist_file):
        imp, _ = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        assert hasattr(imp, "_pending_vr")
        assert len(imp._pending_vr.to_create) == 5

    def test_calling_prepare_twice_replaces_pending(self, tmp_path, valid_taglist_file, csv_taglist_file):
        imp, _ = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        first_count = len(imp._pending_vr.to_create)
        imp.prepare(csv_taglist_file)
        second_count = len(imp._pending_vr.to_create)
        assert first_count  == 5
        assert second_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# implement_one
# ═══════════════════════════════════════════════════════════════════════════════

class TestImplementOne:

    def test_creates_tag_successfully(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = imp._pending_vr.to_create[0].proposed_tagname
        r   = imp.implement_one(tag, "DS-001")

        assert r["success"] is True
        assert r["response"]["final_status"] == "CREATED"

    def test_row_annotated_in_place(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = imp._pending_vr.to_create[0].proposed_tagname
        imp.implement_one(tag, "DS-001")

        row = imp._find_row(tag)
        assert row.final_status   == "CREATED"
        assert row.pi_tag_created == "Yes"

    def test_tag_added_to_point_store(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = imp._pending_vr.to_create[0].proposed_tagname
        imp.implement_one(tag, "DS-001")

        assert tag in mp.created

    def test_already_exists_on_final_check(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = imp._pending_vr.to_create[0].proposed_tagname
        mp.existing.add(tag)    # pre-exist before implement call
        r = imp.implement_one(tag, "DS-001")

        assert r["success"] is True
        assert imp._find_row(tag).final_status == "ALREADY EXISTED"

    def test_unknown_point_type_returns_error(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        row = imp._pending_vr.to_create[0]
        row.proposed_tagname = "Plant_Unit_Sys_Widget"
        r = imp.implement_one("Plant_Unit_Sys_Widget", "DS-001")

        assert r["success"] is False
        assert "Cannot infer" in r["message"]
        assert imp._find_row("Plant_Unit_Sys_Widget").final_status == "FAILED"

    def test_create_failure_marks_row_failed(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path, ds_fail=True)
        imp.prepare(valid_taglist_file)
        tag = imp._pending_vr.to_create[0].proposed_tagname
        r   = imp.implement_one(tag, "DS-001")

        assert r["success"] is False
        row = imp._find_row(tag)
        assert row.final_status   == "FAILED"
        assert row.pi_tag_created == "No"
        assert "PI server error" in row.error_detail

    def test_guard_requires_prepare_first(self, tmp_path):
        imp, _ = make_implementor(tmp_path)
        r = imp.implement_one("Any_Tag_Name", "DS-001")
        assert r["success"] is False
        assert "prepare()" in r["message"]

    def test_unknown_tag_name_returns_error(self, tmp_path, valid_taglist_file):
        imp, _ = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        r = imp.implement_one("NonExistent_Tag_Name", "DS-001")
        assert r["success"] is False
        assert "not found" in r["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# link_attribute
# ═══════════════════════════════════════════════════════════════════════════════

class TestLinkAttribute:

    def _create_tag(self, imp, mp):
        """Helper: implement the first to_create row and return its tag name."""
        tag = imp._pending_vr.to_create[0].proposed_tagname
        imp.implement_one(tag, "DS-001")
        return tag

    def test_links_successfully(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = self._create_tag(imp, mp)
        r   = imp.link_attribute(tag)

        assert r["success"] is True
        assert r["response"]["af_attribute_linked"] == "Yes"

    def test_live_data_yes_when_flowing(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        tag = self._create_tag(imp, mp)
        imp.link_attribute(tag)

        row = imp._find_row(tag)
        assert row.live_data_received == "Yes"

    def test_live_data_no_when_not_flowing(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path, no_live_data=True)
        imp.prepare(valid_taglist_file)
        tag = self._create_tag(imp, mp)
        imp.link_attribute(tag)

        row = imp._find_row(tag)
        assert row.live_data_received == "No"

    def test_skips_if_not_created(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        # Don't call implement_one — row.final_status is ""
        tag = imp._pending_vr.to_create[0].proposed_tagname
        r   = imp.link_attribute(tag)

        assert r["success"] is True
        row = imp._find_row(tag)
        assert row.af_attribute_linked == "N/A"

    def test_already_linked_skips_set_value(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path, already_linked=True)
        imp.prepare(valid_taglist_file)
        tag = self._create_tag(imp, mp)
        r   = imp.link_attribute(tag)

        assert r["success"] is True
        assert imp._find_row(tag).af_attribute_linked == "Yes"

    def test_set_value_failure_marks_row(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path, fail_set_attr=True)
        imp.prepare(valid_taglist_file)
        tag = self._create_tag(imp, mp)
        r   = imp.link_attribute(tag)

        assert r["success"] is False
        row = imp._find_row(tag)
        assert row.af_attribute_linked == "No"
        assert "400" in row.error_detail

    def test_guard_requires_prepare_first(self, tmp_path):
        imp, _ = make_implementor(tmp_path)
        r = imp.link_attribute("Any_Tag")
        assert r["success"] is False
        assert "prepare()" in r["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# finalize
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinalize:

    def test_creates_output_report(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        r = imp.finalize()
        assert r["success"] is True
        assert os.path.exists(r["response"]["report_path"])

    def test_counts_in_response(self, tmp_path, valid_taglist_file):
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)

        for row in imp._pending_vr.to_create:
            imp.implement_one(row.proposed_tagname, "DS-001")

        r = imp.finalize()
        assert r["response"]["created"] == 5
        assert r["response"]["failed"]  == 0

    def test_guard_requires_prepare_first(self, tmp_path):
        imp, _ = make_implementor(tmp_path)
        r = imp.finalize()
        assert r["success"] is False
        assert "prepare()" in r["message"]

    def test_partial_implementation_does_not_crash(self, tmp_path, valid_taglist_file):
        """finalize() should work even if not all rows have been implemented."""
        imp, mp = make_implementor(tmp_path)
        imp.prepare(valid_taglist_file)
        # Only implement 2 out of 5
        for row in imp._pending_vr.to_create[:2]:
            imp.implement_one(row.proposed_tagname, "DS-001")
        r = imp.finalize()
        assert r["success"] is True
        assert r["response"]["created"] == 2