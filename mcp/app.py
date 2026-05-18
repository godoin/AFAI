import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import PI_BASE, PI_SERVER, PI_USER, PI_PASS, AF_DATABASE
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

asset_server     = AssetServer(pi)
asset_database   = AssetDatabases(pi)
elements         = Elements(pi)
element_templates = ElementTemplates(pi)
attributes       = Attributes(pi)
data_server      = DataServer(pi)
points           = Points(pi)
streams          = Streams(pi)

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
            name="get_point",
            description="Get a PI point/tag by WebId",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_name": {"type": "string", "description": "PI tag name (used as WebId here)"}
                },
                "required": ["tag_name"]
            }
        ),

        # ── Streams ────────────────────────────────────────────────────
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
            # UserResponse pattern — has 'message' and optionally 'response'
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

    # ── Element Templates ──────────────────────────────────────────────────────
    if name == "get_element_template":
        return wrap(element_templates.get(arguments["web_id"]))

    if name == "get_element_template_by_path":
        return wrap(element_templates.get_by_path(arguments["path"]))

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

    if name == "get_point":
        return wrap(points.get(arguments["tag_name"]))

    # ── Streams ────────────────────────────────────────────────────────────────
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