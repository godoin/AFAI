"""
conftest.py — shared pytest fixtures and mock PI service classes.

All tests import their mocks from here so the mock behaviour is
defined once and consistent across the suite.
"""

import io
import pytest
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# Mock PI service classes
# ═══════════════════════════════════════════════════════════════════════════════

class MockAssetServer:
    """Always returns a single reachable server."""
    def lists(self):
        return {"Items": [{"Name": "PI-SYSTEM", "WebId": "AS-001"}]}


class MockAssetDB:
    """Always returns a valid database."""
    def get_by_path(self, path):
        return {"success": True, "code": 200, "response": {"WebId": "DB-001", "Path": path}}


class MockPISystem:
    pi_server = "PI-SYSTEM"

    def get_all_elements(self, path):
        return {
            "locations":    {"Items": [{"Name": "TestLocation"}]},
            "power_plants": {"Items": [{"Name": "TestPlant"}]},
            "units":        {"Items": [{"Name": "TestUnit"}]},
        }


class MockElements:
    """
    Returns success for any path containing a plant name from existing_plants.
    Returns 404 otherwise.
    """
    def __init__(self, existing_plants=None):
        self.existing_plants = existing_plants or set()

    def get_by_path(self, path):
        if any(p in path for p in self.existing_plants):
            return {"success": True, "code": 200, "response": {"Name": "MockElement", "WebId": "EL-001"}}
        return {"success": False, "code": 404, "message": "Element not found", "response": "N/A"}


class MockAttributes:
    """
    Returns a valid attribute with an empty DataReferencePlugIn by default.
    Set already_linked=True to simulate an already-linked attribute.
    """
    def __init__(self, already_linked=False, fail_set=False):
        self.already_linked = already_linked
        self.fail_set = fail_set

    def get_by_path(self, path):
        dr = "PI Point" if self.already_linked else ""
        return {
            "success": True,
            "code": 200,
            "response": {"WebId": "ATTR-001", "DataReferencePlugIn": dr}
        }

    def set_value(self, web_id, value):
        if self.fail_set:
            return {"success": False, "code": 400, "message": "Malformed request", "response": "N/A"}
        return {"success": True, "code": 200, "message": "OK", "response": "N/A"}


class MockPoints:
    """
    Tracks existing and created tags.
    create_point (via MockDataServer) adds to self.created.
    """
    def __init__(self, existing=None):
        self.existing = set(existing or [])
        self.created  = set()

    @property
    def all_known(self):
        return self.existing | self.created

    def search(self, query, max_count=1000):
        prefix = query.replace("Tag:=", "").replace("_*", "")
        matched = [{"Name": t} for t in self.all_known if t.startswith(prefix)]
        return {"success": True, "code": 200, "response": {"Items": matched}}

    def get(self, name):
        if name in self.all_known:
            return {"success": True, "code": 200, "response": {"Name": name, "WebId": f"PT-{name}"}}
        return {"success": False, "code": 404, "message": "Not found", "response": "N/A"}


class MockDataServer:
    """
    Simulates tag creation by adding the tag name to mock_points.created.
    Set fail=True to simulate a PI server error.
    """
    def __init__(self, mock_points: MockPoints, fail=False):
        self.mock_points = mock_points
        self.fail = fail

    def create_point(self, web_id, name, point_type, **kwargs):
        if self.fail:
            return {"success": False, "code": 500, "message": "PI server error", "response": "N/A"}
        self.mock_points.created.add(name)
        return {
            "success": True,
            "code": 201,
            "message": f"Tag '{name}' created.",
            "response": {"Name": name, "Location": f"https://pi/points/{name}"}
        }


class MockStreams:
    """
    Returns a live value by default.
    Set no_data=True to simulate a tag with no data flowing.
    """
    def __init__(self, no_data=False):
        self.no_data = no_data

    def get_value(self, web_id):
        if self.no_data:
            return {"success": True, "code": 200, "response": {"Value": "No Data"}}
        return {"success": True, "code": 200, "response": {"Value": 42.0}}


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def chemflow_file(tmp_path):
    """
    Copy the ChemFlow mock tag list from mcp/data/ into a temp directory.
    Expected location: mcp/data/PI_Tag_List_ChemFlow.xlsx
    """
    import shutil, pathlib
    src = pathlib.Path(__file__).parent.parent / "data" / "PI_Tag_List_ChemFlow.xlsx"
    if not src.exists():
        pytest.skip(
            f"Test data file not found at {src}. "
            "Place PI_Tag_List_ChemFlow.xlsx in the mcp/data/ folder to run this test."
        )
    dst = tmp_path / "PI_Tag_List_ChemFlow.xlsx"
    shutil.copy(src, dst)
    return str(dst)


@pytest.fixture
def valid_taglist_file(tmp_path):
    """
    Minimal valid tag list — 5 rows, all passing naming convention.
    Plant names match MockElements.existing_plants in mock_services fixture.
    """
    rows = [
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "SRC_A1_Flow",   "Source Tag": "T1", "Proposed New Tagname": "PlantA_Unit1_Flow_Rate",    "eng_units": "L/min", "Description": "Flow rate A1"},
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "SRC_A1_Press",  "Source Tag": "T2", "Proposed New Tagname": "PlantA_Unit1_Pressure",      "eng_units": "bar",   "Description": "Pressure A1"},
        {"Plant": "PlantA", "Unit/System": "Unit2", "Source Tagname": "SRC_A2_Status", "Source Tag": "T3", "Proposed New Tagname": "PlantA_Unit2_Run_Status",    "eng_units": "",      "Description": "Run status A2"},
        {"Plant": "PlantB", "Unit/System": "Unit1", "Source Tagname": "SRC_B1_Mag",    "Source Tag": "T4", "Proposed New Tagname": "PlantB_Unit1_VA_Mag",        "eng_units": "V",     "Description": "Voltage mag B1"},
        {"Plant": "PlantB", "Unit/System": "Unit1", "Source Tagname": "SRC_B1_Phase",  "Source Tag": "T5", "Proposed New Tagname": "PlantB_Unit1_VA_Phase",      "eng_units": "°",     "Description": "Voltage phase B1"},
    ]
    path = tmp_path / "valid_taglist.xlsx"
    pd.DataFrame(rows).to_excel(str(path), index=False)
    return str(path)


@pytest.fixture
def violation_taglist_file(tmp_path):
    """Tag list with a mix of valid and invalid naming."""
    rows = [
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "S1", "Source Tag": "T1", "Proposed New Tagname": "PlantA_Unit1_Flow_Rate"},    # valid
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "S2", "Source Tag": "T2", "Proposed New Tagname": "Has Space In Name"},           # violation: whitespace
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "S3", "Source Tag": "T3", "Proposed New Tagname": "Has-Hyphen"},                  # violation: invalid char
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "S4", "Source Tag": "T4", "Proposed New Tagname": "TooShort"},                    # violation: too few segments
        {"Plant": "PlantA", "Unit/System": "Unit1", "Source Tagname": "S5", "Source Tag": "T5", "Proposed New Tagname": ""},                            # violation: empty
    ]
    path = tmp_path / "violations.xlsx"
    pd.DataFrame(rows).to_excel(str(path), index=False)
    return str(path)


@pytest.fixture
def missing_columns_file(tmp_path):
    """Tag list missing required columns."""
    path = tmp_path / "missing_cols.xlsx"
    pd.DataFrame({"Plant": ["PlantA"], "Unit/System": ["Unit1"]}).to_excel(str(path), index=False)
    return str(path)


@pytest.fixture
def csv_taglist_file(tmp_path):
    """Single-row CSV tag list."""
    path = tmp_path / "tags.csv"
    pd.DataFrame([{
        "Plant": "PlantA", "Unit/System": "Unit1",
        "Source Tagname": "SRC", "Source Tag": "T1",
        "Proposed New Tagname": "PlantA_Unit1_Flow_Rate"
    }]).to_csv(str(path), index=False)
    return str(path)


@pytest.fixture
def mock_services():
    """
    Returns a dict of mock service instances with PlantA and PlantB
    existing in AF, no pre-existing PI tags.
    """
    mp = MockPoints()
    return {
        "pi_system":    MockPISystem(),
        "asset_server": MockAssetServer(),
        "asset_db":     MockAssetDB(),
        "elements":     MockElements(existing_plants={"PlantA", "PlantB"}),
        "attributes":   MockAttributes(),
        "data_server":  MockDataServer(mp),
        "points":       mp,
        "streams":      MockStreams(),
    }


@pytest.fixture
def af_database_path():
    return r"\\PI-SYSTEM\GoogleManualLogger"