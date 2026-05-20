import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import PI_BASE, PI_SERVER, PI_USER, PI_PASS, AF_DATABASE
from core.tag_list import TagListImplementor
from services.pi_system.base import PISystem
from services.pi_system.assetserver import AssetServer
from services.pi_system.assetdatabase import AssetDatabases
from services.pi_system.elements import Elements
from services.pi_system.elementtemplates import ElementTemplates
from services.pi_system.attributes import Attributes
from services.pi_system.dataserver import DataServer
from services.pi_system.points import Points
from services.pi_system.streams import Streams

# ── Bootstrap PI services ──────────────────────────────────────────────────────
pi = PISystem(
    base_url=PI_BASE,
    pi_server=PI_SERVER,
    username=PI_USER,
    password=PI_PASS,
)

asset_server      = AssetServer(pi)
asset_database    = AssetDatabases(pi)
elements          = Elements(pi)
element_templates = ElementTemplates(pi)
attributes        = Attributes(pi)
data_server       = DataServer(pi)
points            = Points(pi)
streams           = Streams(pi)

# ── MCP app ────────────────────────────────────────────────────────────────────
app = Server("pi-system")


@app.list_tools()
async def list_tools():
    return [

        # ── Asset Server ───────────────────────────────────────────────
        Tool(
            name="list_asset_servers",
            description="List all Asset Servers known to PI Web API",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_asset_server",
            description="Get a specific Asset Server by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the Asset Server"}
                },
                "required": ["web_id"]
            }
        ),

        # ── Asset Database ─────────────────────────────────────────────
        Tool(
            name="get_asset_database",
            description="Get an Asset Database by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the Asset Database"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_asset_database_by_path",
            description="Get an Asset Database by its full path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": r"e.g. \\PI-SYSTEM\GoogleManualLogger"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_database_elements",
            description="Get all child elements of an Asset Database",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the Asset Database"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_all_elements",
            description="Get all Locations, PowerPlants, and Units from the AF database in one batch call",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_path": {
                        "type": "string",
                        "description": r"Full AF database path e.g. \\PI-SYSTEM\GoogleManualLogger"
                    }
                },
                "required": ["database_path"]
            }
        ),

        # ── Elements ───────────────────────────────────────────────────
        Tool(
            name="get_element",
            description="Get an AF element by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_element_by_path",
            description="Get an AF element by its path (relative to PI server)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": r"Path relative to PI server e.g. GoogleManualLogger\DataGrid\Cebu"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_element_attributes",
            description=(
                "Get all attributes of an AF element by WebId. "
                "Returns DataReferencePlugIn per attribute so you can confirm whether "
                "each attribute is linked to a PI Point, is a derived/formula attribute, "
                "or is a configuration item. Use this before any data reference assignment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the element"},
                    "name_filter": {
                        "type": "string",
                        "description": "Optional name filter e.g. 'VA_*' to narrow results"
                    },
                    "search_full_hierarchy": {
                        "type": "boolean",
                        "description": "Include nested child attributes. Default false."
                    }
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_child_elements",
            description=(
                "Get immediate child elements of an AF element by WebId. "
                "Optionally filter by template name e.g. 'Unit' to list only Unit elements "
                "under a PowerPlant. Use this to traverse the hierarchy one level at a time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the parent element"},
                    "template_name": {
                        "type": "string",
                        "description": "Optional template filter e.g. 'Unit', 'PowerPlant'"
                    },
                    "search_full_hierarchy": {
                        "type": "boolean",
                        "description": "Search beyond immediate children. Default false."
                    }
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_element_analyses",
            description=(
                "Get all analyses targeting an AF element by WebId. "
                "Returns analysis name, status (Enabled/Disabled), rule plugin "
                "(e.g. PerformanceEquation), and whether it is linked to a template. "
                "Use this to verify VC_Mag and VC_Phase analyses exist and are enabled "
                "before reading derived attribute values."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the element"}
                },
                "required": ["web_id"]
            }
        ),

        # ── Element Templates ──────────────────────────────────────────
        Tool(
            name="get_element_template",
            description="Get an element template by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_element_template_by_path",
            description="Get an element template by path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_element_template_attribute_templates",
            description=(
                "Get all attribute templates defined on an element template by WebId. "
                "Returns DataReferencePlugIn and ConfigString per attribute template — "
                "use this to confirm what data reference is expected on the template "
                "before inspecting live element attributes. "
                "Pass show_inherited=true to include attributes from base/parent templates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the element template"},
                    "show_inherited": {
                        "type": "boolean",
                        "description": "Include attribute templates from base templates. Default false."
                    },
                    "show_descendants": {
                        "type": "boolean",
                        "description": "Include nested child attribute templates. Default false."
                    }
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_element_template_analysis_templates",
            description=(
                "Get all analysis templates attached to an element template by WebId. "
                "Returns the analysis rule plugin (e.g. PerformanceEquation), time rule plugin, "
                "and CreateEnabled flag. Use alongside get_element_analyses to cross-check: "
                "this shows what analyses should exist per the template definition; "
                "get_element_analyses confirms whether they actually do on a live element."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the element template"}
                },
                "required": ["web_id"]
            }
        ),

        # ── Attributes ─────────────────────────────────────────────────
        Tool(
            name="get_attribute",
            description="Get an attribute by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="get_attribute_by_path",
            description="Get an attribute by its full path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="set_attribute_value",
            description="Set the value of a configuration item attribute",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string"},
                    "value":  {"description": "New value to set"}
                },
                "required": ["web_id", "value"]
            }
        ),

        # ── Data Server / Points ───────────────────────────────────────
        Tool(
            name="list_data_servers",
            description="List all Data Servers known to PI Web API",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_data_server_points",
            description="List all PI points/tags on a Data Server",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the Data Server"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="create_pi_tag",
            description=(
                "Create a new PI point (tag) on the specified Data Server. "
                "WRITE OPERATION — requires explicit BA confirmation in this conversation turn. "
                "Must only be called after: (1) BA explicitly requests tag creation, "
                "(2) get_point or search_points confirms the tag does NOT already exist, "
                "(3) naming convention validation has passed for the Proposed New Tagname. "
                "Returns 201 and the Location URL of the new tag on success."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {
                        "type": "string",
                        "description": "WebId of the Data Server (from list_data_servers)"
                    },
                    "name": {
                        "type": "string",
                        "description": "PI tag name — must pass naming convention validation"
                    },
                    "point_type": {
                        "type": "string",
                        "description": "Float32 | Float64 | Int16 | Int32 | String | Digital | Timestamp"
                    },
                    "descriptor": {
                        "type": "string",
                        "description": "Human-readable description (maps to Description column in tag list)"
                    },
                    "engineering_units": {
                        "type": "string",
                        "description": "Engineering units e.g. V, bar, A, spm — must match eng_units in tag list"
                    },
                    "point_class": {
                        "type": "string",
                        "description": "Always 'classic' unless BA specifies otherwise"
                    },
                    "step": {
                        "type": "boolean",
                        "description": "True for stepped/held values, False for interpolated. Default false."
                    },
                    "future": {
                        "type": "boolean",
                        "description": "Allow future-dated values. Default false."
                    },
                    "display_digits": {
                        "type": "integer",
                        "description": "Decimal places for display. Default -5 (auto)."
                    }
                },
                "required": ["web_id", "name", "point_type"]
            }
        ),
        Tool(
            name="get_point",
            description="Get a PI point/tag by tag name",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_name": {"type": "string", "description": "PI tag name"}
                },
                "required": ["tag_name"]
            }
        ),
        Tool(
            name="get_point_by_path",
            description=(
                "Get a PI point by its full PI path. "
                r"Expected format: \\PI-SYSTEM\TagName "
                r"e.g. \\PI-SYSTEM\Cebu_PlantA_Unit1_VA_Mag. "
                "Use when you have a path from a tag list but no WebId yet. "
                "Returns PointType, EngineeringUnits, and Descriptor for pre-link verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": r"Full PI path e.g. \\PI-SYSTEM\Cebu_PlantA_Unit1_VA_Mag"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_point_attributes",
            description=(
                "Get the low-level properties of a PI point by WebId. "
                "Returns tag attributes such as pointtype, engunits, descriptor, "
                "and typicalvalue. Use name_filter to narrow to specific attributes "
                "e.g. 'engunits' or 'pointtype'. "
                "Use this to verify tag configuration matches the tag list "
                "before linking the tag to an AF attribute."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the PI point"},
                    "name_filter": {
                        "type": "string",
                        "description": "Optional filter e.g. 'engunits', 'pointtype'"
                    }
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="search_points",
            description=(
                "Search for PI points by query string across the Data Archive. "
                "Follows PI Point Query syntax. Common patterns: "
                "'Tag:=Cebu_*' — all tags starting with Cebu_, "
                "'Tag:=*_VA_Mag' — all VA_Mag tags across all locations, "
                "'Tag:=Cebu_PlantA_Unit1_*' — all tags for a specific unit. "
                "Use during bulk tag verification to confirm which proposed tags "
                "from the client tag list already exist before data ref assignment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "PI Point Query string e.g. 'Tag:=Cebu_*'"
                    },
                    "data_server_web_id": {
                        "type": "string",
                        "description": "Optional WebId of Data Server to scope the search"
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Max results to return. Default 100, API max 1000."
                    }
                },
                "required": ["query"]
            }
        ),

        # ── Streams ────────────────────────────────────────────────────
        # ── Tag list intake workflow ──────────────────────────────────
        Tool(
            name="session_start",
            description=(
                "Phase 0: confirm PI Web API connection and map current AF state. "
                "Always call this at the start of every new session before anything else. "
                "Runs list_asset_servers, get_asset_database_by_path, and get_all_elements "
                "in sequence. Fails fast if PI is unreachable."
            ),
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="prepare_tag_list",
            description=(
                "Phases 1–3 + Gate 1: parse the uploaded tag list file, run naming "
                "convention validation, cross-check proposed tags against live AF and "
                "PI Data Archive, and produce a pre-action Excel report for BA review. "
                "DOES NOT write anything to PI System. "
                "Present the report to the BA and wait for explicit confirmation "
                "before calling implement_tag or link_attribute."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the uploaded tag list .xlsx or .csv file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="implement_tag",
            description=(
                "Phase 4, Step 4.1: create ONE PI tag and verify it exists. "
                "WRITE OPERATION — only call after prepare_tag_list and explicit BA confirmation. "
                "Call once per tag. Never batch multiple tags in one call (GUARDRAILS G11). "
                "Runs: final existence check → create_pi_tag → verify with get_point."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_name": {
                        "type": "string",
                        "description": "Proposed New Tagname to create"
                    },
                    "data_server_web_id": {
                        "type": "string",
                        "description": "WebId of the target PI Data Server (from list_data_servers)"
                    }
                },
                "required": ["tag_name", "data_server_web_id"]
            }
        ),
        Tool(
            name="link_attribute",
            description=(
                "Phase 4, Step 4.2: link an AF attribute to its PI tag and verify live data. "
                "WRITE OPERATION — only call after implement_tag confirms the tag was CREATED. "
                "Runs: get_attribute_by_path → set_attribute_value → get_stream_value."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_name": {
                        "type": "string",
                        "description": "The PI tag name whose AF attribute should be linked"
                    }
                },
                "required": ["tag_name"]
            }
        ),
        Tool(
            name="finalize_session",
            description=(
                "Phase 5: generate and deliver the final output report. "
                "Call after all implement_tag and link_attribute calls are complete. "
                "Produces a two-sheet Excel (Session Summary + Full Results) "
                "and returns the file path for delivery to the BA."
            ),
            inputSchema={"type": "object", "properties": {}}
        ),

        Tool(
            name="get_stream_value",
            description="Get the latest value of a PI stream (attribute linked to a PI tag)",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string", "description": "WebId of the attribute or stream"}
                },
                "required": ["web_id"]
            }
        ),
        Tool(
            name="update_stream_value",
            description="Write a new value to a PI stream",
            inputSchema={
                "type": "object",
                "properties": {
                    "web_id": {"type": "string"},
                    "value":  {"description": "Value to write"}
                },
                "required": ["web_id", "value"]
            }
        ),

        # ── Batch helpers ──────────────────────────────────────────────
        Tool(
            name="get_data_from_database",
            description="Batch call: get all elements and their attributes for a given template from the AF database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_path": {
                        "type": "string",
                        "description": r"Full AF database path e.g. \\PI-SYSTEM\GoogleManualLogger"
                    },
                    "template_name": {
                        "type": "string",
                        "description": "Element template name e.g. Unit"
                    }
                },
                "required": ["database_path", "template_name"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):

    def wrap(result):
        """Convert UserResponse or plain dict/str to TextContent."""
        import json
        if result is None:
            return [TextContent(type="text", text="No result returned.")]
        if isinstance(result, dict):
            if "response" in result:
                return [TextContent(type="text", text=json.dumps(result["response"], indent=2))]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        return [TextContent(type="text", text=str(result))]

    # ── Asset Server ───────────────────────────────────────────────────────────
    if name == "list_asset_servers":
        return wrap(asset_server.lists())

    if name == "get_asset_server":
        return wrap(asset_server.get(arguments["web_id"]))

    # ── Asset Database ─────────────────────────────────────────────────────────
    if name == "get_asset_database":
        return wrap(asset_database.get(arguments["web_id"]))

    if name == "get_asset_database_by_path":
        return wrap(asset_database.get_by_path(arguments["path"]))

    if name == "get_database_elements":
        return wrap(asset_database.get_elements(arguments["web_id"]))

    if name == "get_all_elements":
        return wrap(pi.get_all_elements(arguments["database_path"]))

    # ── Elements ───────────────────────────────────────────────────────────────
    if name == "get_element":
        return wrap(elements.get(arguments["web_id"]))

    if name == "get_element_by_path":
        return wrap(elements.get_by_path(arguments["path"]))

    if name == "get_element_attributes":
        return wrap(elements.get_attributes(
            web_id=arguments["web_id"],
            name_filter=arguments.get("name_filter"),
            search_full_hierarchy=arguments.get("search_full_hierarchy", False)
        ))

    if name == "get_child_elements":
        return wrap(elements.get_child_elements(
            web_id=arguments["web_id"],
            template_name=arguments.get("template_name"),
            search_full_hierarchy=arguments.get("search_full_hierarchy", False)
        ))

    if name == "get_element_analyses":
        return wrap(elements.get_analyses(arguments["web_id"]))

    # ── Element Templates ──────────────────────────────────────────────────────
    if name == "get_element_template":
        return wrap(element_templates.get(arguments["web_id"]))

    if name == "get_element_template_by_path":
        return wrap(element_templates.get_by_path(arguments["path"]))

    if name == "get_element_template_attribute_templates":
        return wrap(element_templates.get_attribute_templates(
            web_id=arguments["web_id"],
            show_inherited=arguments.get("show_inherited", False),
            show_descendants=arguments.get("show_descendants", False)
        ))

    if name == "get_element_template_analysis_templates":
        return wrap(element_templates.get_analysis_templates(arguments["web_id"]))

    # ── Attributes ─────────────────────────────────────────────────────────────
    if name == "get_attribute":
        return wrap(attributes.get(arguments["web_id"]))

    if name == "get_attribute_by_path":
        return wrap(attributes.get_by_path(arguments["path"]))

    if name == "set_attribute_value":
        return wrap(attributes.set_value(arguments["web_id"], arguments["value"]))

    # ── Data Server / Points ───────────────────────────────────────────────────
    if name == "list_data_servers":
        return wrap(data_server.lists())

    if name == "get_data_server_points":
        return wrap(data_server.get_points(arguments["web_id"]))

    if name == "create_pi_tag":
        return wrap(data_server.create_point(
            web_id=arguments["web_id"],
            name=arguments["name"],
            point_type=arguments["point_type"],
            descriptor=arguments.get("descriptor", ""),
            engineering_units=arguments.get("engineering_units", ""),
            point_class=arguments.get("point_class", "classic"),
            step=arguments.get("step", False),
            future=arguments.get("future", False),
            display_digits=arguments.get("display_digits", -5)
        ))

    if name == "get_point":
        return wrap(points.get(arguments["tag_name"]))

    if name == "get_point_by_path":
        return wrap(points.get_by_path(arguments["path"]))

    if name == "get_point_attributes":
        return wrap(points.get_attributes(
            web_id=arguments["web_id"],
            name_filter=arguments.get("name_filter")
        ))

    if name == "search_points":
        return wrap(points.search(
            query=arguments["query"],
            data_server_web_id=arguments.get("data_server_web_id"),
            max_count=arguments.get("max_count", 100)
        ))

    # ── Streams ────────────────────────────────────────────────────────────────
    # ── Tag list intake workflow ───────────────────────────────────────────────
    if name == "session_start":
        return wrap(implementor.session_start())

    if name == "prepare_tag_list":
        return wrap(implementor.prepare(arguments["file_path"]))

    if name == "implement_tag":
        return wrap(implementor.implement_one(
            tag_name=arguments["tag_name"],
            data_server_web_id=arguments["data_server_web_id"]
        ))

    if name == "link_attribute":
        return wrap(implementor.link_attribute(arguments["tag_name"]))

    if name == "finalize_session":
        return wrap(implementor.finalize())

    if name == "get_stream_value":
        return wrap(streams.get_value(arguments["web_id"]))

    if name == "update_stream_value":
        return wrap(streams.update_value(arguments["web_id"], arguments["value"]))

    # ── Batch ──────────────────────────────────────────────────────────────────
    if name == "get_data_from_database":
        return wrap(pi.get_data_from_database(
            arguments["database_path"],
            arguments["template_name"]
        ))

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())