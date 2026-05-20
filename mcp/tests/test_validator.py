"""
test_validator.py — unit tests for core.tag_list.validator.TagListValidator

Run:  pytest tests/test_validator.py -v
"""

import pytest
from core.tag_list.parser import TagListParser
from core.tag_list.validator import TagListValidator, ValidationResult
from tests.conftest import MockElements, MockPoints, MockDataServer, MockPISystem


@pytest.fixture
def parser():
    return TagListParser()


def make_validator(elements, points, pi_system=None):
    return TagListValidator(
        elements=elements,
        points=points,
        pi_system=pi_system or MockPISystem()
    )


# ── Happy path ─────────────────────────────────────────────────────────────────

class TestHappyPath:

    def test_all_to_create_when_af_exists_no_pi_tags(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        v  = make_validator(MockElements({"PlantA", "PlantB"}), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert vr.success
        assert len(vr.to_create)     == 5
        assert len(vr.already_exist) == 0
        assert len(vr.af_missing)    == 0

    def test_chemflow_all_to_create(self, parser, chemflow_file, af_database_path):
        pr = parser.parse(chemflow_file)
        all_plants = {r.plant for r in pr.valid_rows}
        v  = make_validator(MockElements(all_plants), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert vr.success
        assert len(vr.to_create) == 100
        assert len(vr.already_exist) == 0
        assert len(vr.af_missing) == 0

    def test_naming_violations_pass_through_unchanged(
        self, parser, violation_taglist_file, af_database_path
    ):
        pr = parser.parse(violation_taglist_file)
        v  = make_validator(MockElements({"PlantA"}), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert len(vr.naming_violations) == 4
        assert len(vr.to_create) == 1


# ── Tag already exists ─────────────────────────────────────────────────────────

class TestTagAlreadyExists:

    def test_existing_tags_marked_skip(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        existing = {r.proposed_tagname for r in pr.valid_rows[:2]}
        v  = make_validator(MockElements({"PlantA", "PlantB"}), MockPoints(existing))
        vr = v.validate(pr, af_database_path)

        assert vr.success
        assert len(vr.already_exist) == 2
        assert len(vr.to_create)     == 3

    def test_already_exist_rows_have_correct_fields(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        existing = {pr.valid_rows[0].proposed_tagname}
        v  = make_validator(MockElements({"PlantA", "PlantB"}), MockPoints(existing))
        vr = v.validate(pr, af_database_path)

        row = vr.already_exist[0]
        assert row.exists_in_pi     == "Yes"
        assert row.exists_in_af     == "Yes"
        assert row.proposed_action  == "SKIP — already exists"

    def test_all_tags_exist_zero_to_create(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        all_tags = {r.proposed_tagname for r in pr.valid_rows}
        v  = make_validator(MockElements({"PlantA", "PlantB"}), MockPoints(all_tags))
        vr = v.validate(pr, af_database_path)

        assert len(vr.to_create)     == 0
        assert len(vr.already_exist) == 5


# ── AF element missing ─────────────────────────────────────────────────────────

class TestAFElementMissing:

    def test_missing_af_plant_marks_rows(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        # Only PlantA exists in AF — PlantB rows should be AF_ELEMENT_MISSING
        v  = make_validator(MockElements({"PlantA"}), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert vr.success
        assert len(vr.af_missing) == 2   # PlantB has 2 rows
        assert len(vr.to_create)  == 3   # PlantA has 3 rows

    def test_af_missing_rows_have_correct_fields(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        v  = make_validator(MockElements({"PlantA"}), MockPoints())
        vr = v.validate(pr, af_database_path)

        for row in vr.af_missing:
            assert row.exists_in_af    == "No"
            assert row.proposed_action == "SKIP — AF element missing"

    def test_no_af_elements_all_missing(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        v  = make_validator(MockElements(set()), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert len(vr.af_missing) == 5
        assert len(vr.to_create)  == 0


# ── Error propagation ──────────────────────────────────────────────────────────

class TestErrorPropagation:

    def test_500_from_elements_stops_validation(
        self, parser, valid_taglist_file, af_database_path
    ):
        class FailElements:
            def get_by_path(self, path):
                return {"success": False, "code": 500, "message": "PI server error", "response": "N/A"}

        pr = parser.parse(valid_taglist_file)
        v  = make_validator(FailElements(), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert not vr.success
        assert "PI server error" in vr.error_message

    def test_401_from_elements_stops_validation(
        self, parser, valid_taglist_file, af_database_path
    ):
        class UnauthorisedElements:
            def get_by_path(self, path):
                return {"success": False, "code": 401, "message": "Authentication failed", "response": "N/A"}

        pr = parser.parse(valid_taglist_file)
        v  = make_validator(UnauthorisedElements(), MockPoints())
        vr = v.validate(pr, af_database_path)

        assert not vr.success

    def test_404_from_elements_is_not_an_error(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        v  = make_validator(MockElements(set()), MockPoints())   # all 404
        vr = v.validate(pr, af_database_path)

        assert vr.success        # 404 = missing, not an API failure
        assert len(vr.af_missing) == 5

    def test_empty_parse_result_returns_empty_validation(
        self, parser, missing_columns_file, af_database_path
    ):
        pr = parser.parse(missing_columns_file)
        assert not pr.success    # file is bad — ParseResult has no valid rows

        # ValidationResult should still return cleanly with empty valid_rows
        v  = make_validator(MockElements({"PlantA"}), MockPoints())
        vr = v.validate(pr, af_database_path)    # pr.valid_rows is empty

        assert vr.success
        assert len(vr.to_create) == 0


# ── ValidationResult ──────────────────────────────────────────────────────────

class TestValidationResult:

    def test_all_rows_in_file_order(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        # Mix: PlantA to_create, PlantB af_missing
        v  = make_validator(MockElements({"PlantA"}), MockPoints())
        vr = v.validate(pr, af_database_path)

        nums = [r.row_number for r in vr.all_rows]
        assert nums == sorted(nums)

    def test_summary_counts_correct(
        self, parser, valid_taglist_file, af_database_path
    ):
        pr = parser.parse(valid_taglist_file)
        existing = {pr.valid_rows[0].proposed_tagname}
        v  = make_validator(MockElements({"PlantA", "PlantB"}), MockPoints(existing))
        vr = v.validate(pr, af_database_path)

        s = vr.summary()
        assert s["Tags to create"]        == 4
        assert s["Tags already existing"] == 1
        assert s["AF elements missing"]   == 0
        assert s["Naming violations"]     == 0
        assert s["Rows skipped (total)"]  == 1

    def test_deduplication_af_calls(
        self, parser, valid_taglist_file, af_database_path
    ):
        """PlantA has 3 rows, PlantB has 2 rows — only 4 unique (Plant, Unit) combos."""
        call_log = []

        class LoggingElements:
            def get_by_path(self, path):
                call_log.append(path)
                return {"success": True, "code": 200, "response": {"Name": "El"}}

        pr = parser.parse(valid_taglist_file)
        v  = make_validator(LoggingElements(), MockPoints())
        v.validate(pr, af_database_path)

        # 5 rows but only 4 unique plant+unit combos: PlantA/Unit1, PlantA/Unit2, PlantB/Unit1 x2
        # PlantB/Unit1 appears twice but should only be looked up once
        unique_paths = set(call_log)
        assert len(call_log) == len(unique_paths), (
            f"Expected deduplicated calls, got {len(call_log)} calls for {len(unique_paths)} unique paths"
        )