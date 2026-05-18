# CLAUDE.md — MCP Server

Context for Claude Code when working inside the `mcp/` folder.

---

## What this folder is

A standalone MCP (Model Context Protocol) server that connects Claude Desktop
to OSIsoft PI System via PI Web API. It is used for local exploration and testing
before the full web app (frontend + backend) is built.

This is **not** a web server. It runs as a subprocess of Claude Desktop over stdio.

---

## Folder structure

```
mcp/
├── app.py                          ← MCP entrypoint — tool definitions + routing only
├── config.py                       ← PI credentials and connection settings
├── requirements.txt                ← mcp, requests
├── claude_desktop_config.example.json
├── README.md
├── CLAUDE.md                       ← You are here
├── services/
│   └── pi_system/                  ← PI Web API service layer (separated concerns)
│       ├── __init__.py
│       ├── base.py                 ← PISystem base class, send_request, batch helpers
│       ├── assetserver.py          ← AssetServer
│       ├── assetdatabase.py        ← AssetDatabases
│       ├── elements.py             ← Elements
│       ├── elementtemplates.py     ← ElementTemplates
│       ├── attributes.py           ← Attributes
│       ├── dataserver.py           ← DataServer
│       ├── points.py               ← Points
│       ├── streams.py              ← Streams
│       └── streamset.py            ← StreamSet
└── .claude/
    ├── skills/
    │   ├── pi-af-builder.md        ← Skill: read + navigate AF hierarchy
    │   ├── pi-tag-creator.md       ← Skill: verify tags + link attributes
    │   └── pi-analysis.md          ← Skill: verify derived attributes + analyses
    └── guardrails/
        └── GUARDRAILS.md           ← What this MCP can and cannot do
```

---

## Architecture — how it works

```
Claude Desktop
    │
    │  spawns as subprocess (stdio)
    ▼
app.py  (MCP server)
    │
    │  imports and calls
    ▼
services/pi_system/  (PI Web API wrapper)
    │
    │  HTTP via requests
    ▼
PI Web API  (REST on the Hyper-V VM)
    │
    ▼
PI System  (AF hierarchy + PI Data Archive)
```

`app.py` is intentionally thin — it only:
1. Boots service instances from `config.py`
2. Declares MCP tool schemas
3. Routes tool calls to the right service method
4. Wraps the response in `TextContent`

**All PI Web API logic lives in `services/pi_system/` — never in `app.py`.**

---

## Service layer conventions

These conventions come from the existing codebase — follow them exactly.

```python
# All service classes take a PISystem instance in __init__
class Elements:
    def __init__(self, pi_system: PISystem):
        self.pi_system = pi_system

# All methods return UserResponse
from core.models import UserResponse
return UserResponse.success(message="...", response=response.json(), code=200)
return UserResponse.error(message="...", code=400)

# All HTTP calls go through PISystem.send_request — never use requests directly
response = self.pi_system.send_request(
    method="GET",
    endpoint="elements",
    params=params
)

# Always guard against missing inputs
if not web_id:
    logger.error("No web_id provided", exc_info=False)
    return UserResponse.error(message="...", code=400)

# Always guard against failed responses
if not response:
    logger.error("...", exc_info=False)
    return UserResponse.error(message="...", code=500)
```

---

## How to add a new tool

**Step 1 — Add the service method** in the relevant `services/pi_system/*.py` file.
Follow the existing pattern: guard inputs, call `send_request`, return `UserResponse`.

**Step 2 — Register the tool in `app.py`**

```python
# In list_tools()
Tool(
    name="your_tool_name",
    description="Clear description of what it does — Claude reads this",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What this param is"}
        },
        "required": ["param"]
    }
),

# In call_tool()
if name == "your_tool_name":
    return wrap(your_service.your_method(arguments["param"]))
```

**Step 3 — Update `.claude/guardrails/GUARDRAILS.md`**
Add the tool to the "what the MCP CAN do" table.

**Step 4 — Update the relevant skill in `.claude/skills/`**
Add the tool to the "available MCP tools" table and document when to use it.

Do not add a write tool without a corresponding read tool already tested and working.

---

## config.py

```python
PI_HOST     = os.getenv("PI_HOST",     "https://localhost")
PI_BASE     = f"{PI_HOST}/piwebapi"
PI_SERVER   = os.getenv("PI_SERVER",   "PI-SYSTEM")
PI_USER     = os.getenv("PI_USER",     "piadmin")
PI_PASS     = os.getenv("PI_PASS",     "your-password-here")
AF_DATABASE = os.getenv("AF_DATABASE", "GoogleManualLogger")
```

Use environment variables in all environments. Never hardcode credentials.
`config.py` is the only file that reads credentials — do not import `os.getenv`
anywhere else in the codebase.

---

## PI domain knowledge

### Standard AF hierarchy

```
\\PI-SYSTEM\GoogleManualLogger\
└── DataGrid
    └── Location          e.g. Cebu, Davao, Manila, CDO, Dumaguete
        └── PowerPlant    e.g. Plant A, Plant B, Plant C, Plant D
            └── Unit      e.g. Unit1, Unit2, Unit3
                └── Attributes
                    ├── Status      String  · PI Point (raw)
                    ├── Timestamp   Timestamp · PI Point (raw)
                    ├── VA_Mag      Double · V · PI Point (raw)
                    ├── VA_Phase    Double · ° · PI Point (raw)
                    ├── VB_Mag      Double · V · PI Point (raw)
                    ├── VB_Phase    Double · ° · PI Point (raw)
                    ├── VC_Mag      Double · Derived (formula)
                    └── VC_Phase    Double · Derived (formula)
```

### Tag naming convention

```
<Location>_<Plant>_<Unit>_<Attribute>
e.g. Cebu_PlantB_Unit1_VA_Mag
```

- No spaces
- No special characters except underscore
- Location, Plant, Unit must match AF element names exactly (case-sensitive)

### Raw vs derived attributes

| Type | Source | Example |
|---|---|---|
| Raw | PI Point data reference → PI tag | `VA_Mag`, `Status` |
| Derived | PI Analysis expression | `VC_Mag = Sqrt(Sqr('VA_Mag') + Sqr('VB_Mag'))` |

### PI Web API path formats

```python
# Asset database
f"\\\\{PI_SERVER}\\{AF_DATABASE}"
# e.g. \\PI-SYSTEM\GoogleManualLogger

# Element
f"\\\\{PI_SERVER}\\{AF_DATABASE}\\DataGrid\\Cebu\\Plant B\\Unit1"

# Attribute (note the pipe separator)
f"\\\\{PI_SERVER}\\{AF_DATABASE}\\DataGrid\\Cebu\\Plant B\\Unit1|VA_Mag"

# PI tag
f"\\\\{PI_SERVER}\\Cebu_PlantB_Unit1_VA_Mag"
```

---

## Currently available tools in app.py

### Read tools (safe — use freely)
- `list_asset_servers` — `AssetServer.lists()`
- `get_asset_server` — `AssetServer.get(web_id)`
- `get_asset_database` — `AssetDatabases.get(web_id)`
- `get_asset_database_by_path` — `AssetDatabases.get_by_path(path)`
- `get_database_elements` — `AssetDatabases.get_elements(web_id)`
- `get_all_elements` — `PISystem.get_all_elements(database_path)` ← batch
- `get_element` — `Elements.get(web_id)`
- `get_element_by_path` — `Elements.get_by_path(path)`
- `get_element_template` — `ElementTemplates.get(web_id)`
- `get_element_template_by_path` — `ElementTemplates.get_by_path(path)`
- `get_attribute` — `Attributes.get(web_id)`
- `get_attribute_by_path` — `Attributes.get_by_path(path)`
- `list_data_servers` — `DataServer.lists()`
- `get_data_server_points` — `DataServer.get_points(web_id)`
- `get_point` — `Points.get(tag_name)`
- `get_stream_value` — `Streams.get_value(web_id)`
- `get_data_from_database` — `PISystem.get_data_from_database(path, template)` ← batch

### Write tools (use with BA confirmation only)
- `set_attribute_value` — `Attributes.set_value(web_id, value)`
- `update_stream_value` — `Streams.update_value(web_id, value)`

### Not yet implemented (intentional — see GUARDRAILS.md)
- `create_pi_tag`
- `create_element`
- `create_element_template`
- `create_analysis`
- Any `delete_*` tool

---

## What Claude Code should do here

- Keep `app.py` thin — tool definitions and routing only
- Add all new PI logic to the appropriate `services/pi_system/` class
- Follow existing `UserResponse` and `send_request` patterns exactly
- Always read GUARDRAILS.md before adding any write tool
- Update the relevant skill file when adding a new tool
- Use `requests` only — do not add `httpx` or any other HTTP library

## What Claude Code should NOT do here

- Do not add business logic to `app.py`
- Do not call `requests` directly in `app.py` — use service methods
- Do not add a delete tool for any PI resource
- Do not hardcode credentials anywhere — always use `config.py`
- Do not add tools that skip the read-before-write sequence
- Do not add `create_pi_tag` or `create_analysis` until the BA has signed off on the read workflow in a real test session
- Do not modify `base.py` without understanding how `send_request` and `send_batch_request` are used across all services