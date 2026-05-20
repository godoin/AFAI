"""
test_parser.py — unit tests for core.tag_list.parser.TagListParser

Run:  pytest tests/test_parser.py -v
"""

import pytest
from core.tag_list.parser import TagListParser, TagRow, ParseResult


@pytest.fixture
def parser():
    return TagListParser()


# ── File reading ───────────────────────────────────────────────────────────────

class TestFileReading:

    def test_reads_xlsx(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        assert result.success
        assert result.total_rows == 5

    def test_reads_csv(self, parser, csv_taglist_file):
        result = parser.parse(csv_taglist_file)
        assert result.success
        assert result.total_rows == 1

    def test_reads_chemflow_100_rows(self, parser, chemflow_file):
        result = parser.parse(chemflow_file)
        assert result.success
        assert result.total_rows == 100

    def test_unsupported_file_type(self, parser, tmp_path):
        bad = tmp_path / "tags.pdf"
        bad.write_bytes(b"not a real pdf")
        result = parser.parse(str(bad))
        assert not result.success
        assert "Unsupported" in result.error_message

    def test_nonexistent_file(self, parser):
        result = parser.parse("/nonexistent/path/tags.xlsx")
        assert not result.success
        assert result.error_message


# ── Column validation ──────────────────────────────────────────────────────────

class TestColumnValidation:

    def test_missing_required_columns_stops_parse(self, parser, missing_columns_file):
        result = parser.parse(missing_columns_file)
        assert not result.success
        assert len(result.missing_columns) > 0
        assert "Source Tagname" in result.missing_columns
        assert "Source Tag" in result.missing_columns
        assert "Proposed New Tagname" in result.missing_columns

    def test_optional_columns_absent_is_fine(self, parser, tmp_path):
        import pandas as pd
        rows = [{"Plant": "P", "Unit/System": "U", "Source Tagname": "S",
                 "Source Tag": "T", "Proposed New Tagname": "P_U_S_Attr"}]
        path = tmp_path / "minimal.xlsx"
        pd.DataFrame(rows).to_excel(str(path), index=False)
        result = parser.parse(str(path))
        assert result.success
        assert result.total_rows == 1

    def test_extra_columns_are_ignored(self, parser, tmp_path):
        import pandas as pd
        rows = [{"Plant": "P", "Unit/System": "U", "Source Tagname": "S",
                 "Source Tag": "T", "Proposed New Tagname": "P_U_S_Attr",
                 "Mystery Column": "foo", "Another Extra": "bar"}]
        path = tmp_path / "extra_cols.xlsx"
        pd.DataFrame(rows).to_excel(str(path), index=False)
        result = parser.parse(str(path))
        assert result.success


# ── Naming convention validation ───────────────────────────────────────────────

class TestNamingValidation:

    def test_valid_names_pass(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        assert result.success
        assert len(result.violation_rows) == 0
        assert len(result.valid_rows) == 5

    def test_whitespace_in_name_is_violation(self, parser, tmp_path):
        import pandas as pd
        path = tmp_path / "t.xlsx"
        pd.DataFrame([{"Plant":"P","Unit/System":"U","Source Tagname":"S","Source Tag":"T","Proposed New Tagname":"Has Space"}]).to_excel(str(path),index=False)
        result = parser.parse(str(path))
        assert len(result.violation_rows) == 1
        assert "whitespace" in result.violation_rows[0].naming_violation.lower()

    def test_hyphen_is_violation(self, parser, tmp_path):
        import pandas as pd
        path = tmp_path / "t.xlsx"
        pd.DataFrame([{"Plant":"P","Unit/System":"U","Source Tagname":"S","Source Tag":"T","Proposed New Tagname":"Has-Hyphen"}]).to_excel(str(path),index=False)
        result = parser.parse(str(path))
        assert len(result.violation_rows) == 1
        assert "-" in result.violation_rows[0].naming_violation

    def test_too_few_segments_is_violation(self, parser, tmp_path):
        import pandas as pd
        path = tmp_path / "t.xlsx"
        pd.DataFrame([{"Plant":"P","Unit/System":"U","Source Tagname":"S","Source Tag":"T","Proposed New Tagname":"TwoSegs"}]).to_excel(str(path),index=False)
        result = parser.parse(str(path))
        assert len(result.violation_rows) == 1
        assert "segment" in result.violation_rows[0].naming_violation.lower()

    def test_empty_name_is_violation(self, parser, tmp_path):
        import pandas as pd
        path = tmp_path / "t.xlsx"
        pd.DataFrame([{"Plant":"P","Unit/System":"U","Source Tagname":"S","Source Tag":"T","Proposed New Tagname":""}]).to_excel(str(path),index=False)
        result = parser.parse(str(path))
        assert len(result.violation_rows) == 1
        assert "empty" in result.violation_rows[0].naming_violation.lower()

    def test_mixed_valid_and_violations(self, parser, violation_taglist_file):
        result = parser.parse(violation_taglist_file)
        assert result.success
        assert result.total_rows == 5
        assert len(result.valid_rows) == 1
        assert len(result.violation_rows) == 4

    def test_chemflow_zero_violations(self, parser, chemflow_file):
        result = parser.parse(chemflow_file)
        assert result.success
        assert len(result.violation_rows) == 0

    def test_violation_rows_have_proposed_action_set(self, parser, violation_taglist_file):
        result = parser.parse(violation_taglist_file)
        for row in result.violation_rows:
            assert row.proposed_action == "SKIP — naming violation"
            assert row.naming_valid is False
            assert row.naming_violation is not None


# ── ParseResult behaviour ──────────────────────────────────────────────────────

class TestParseResult:

    def test_all_rows_in_file_order(self, parser, violation_taglist_file):
        result = parser.parse(violation_taglist_file)
        row_numbers = [r.row_number for r in result.all_rows]
        assert row_numbers == sorted(row_numbers)

    def test_row_numbers_start_at_2(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        assert result.valid_rows[0].row_number == 2

    def test_summary_counts(self, parser, violation_taglist_file):
        result = parser.parse(violation_taglist_file)
        s = result.summary()
        assert s["Total rows in file"] == 5
        assert s["Rows passing validation"] == 1
        assert s["Naming violations"] == 4


# ── TagRow ─────────────────────────────────────────────────────────────────────

class TestTagRow:

    def test_to_dict_contains_all_expected_keys(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        d = result.valid_rows[0].to_dict()
        for key in ["Row #", "Plant", "Unit/System", "Source Tagname", "Source Tag",
                    "Proposed New Tagname", "Naming Valid", "Exists in PI",
                    "Exists in AF", "Proposed Action", "BA Notes", "Error Detail"]:
            assert key in d, f"Missing key: {key}"

    def test_valid_row_naming_valid_yes(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        d = result.valid_rows[0].to_dict()
        assert d["Naming Valid"] == "Yes"

    def test_violation_row_naming_valid_no(self, parser, violation_taglist_file):
        result = parser.parse(violation_taglist_file)
        d = result.violation_rows[0].to_dict()
        assert d["Naming Valid"].startswith("No —")

    def test_phase4_fields_default_to_empty(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        row = result.valid_rows[0]
        assert row.final_status        == ""
        assert row.pi_tag_created      == ""
        assert row.af_attribute_linked == ""
        assert row.live_data_received  == ""

    def test_phase3_defaults(self, parser, valid_taglist_file):
        result = parser.parse(valid_taglist_file)
        row = result.valid_rows[0]
        assert row.proposed_action == "TO_CREATE"
        assert row.exists_in_pi    == "Not checked"
        assert row.exists_in_af    == "Not checked"
        assert row.error_detail    == ""