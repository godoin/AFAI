# AF Builder — MCP Server

Local MCP server for testing PI System integration via Claude Desktop.
Delegates all PI Web API calls to the existing service layer — `app.py` is just a thin MCP wrapper.

---

## Folder structure

```
mcp/
├── app.py                             ← MCP server entrypoint (thin wrapper only)
├── config.py                          ← PI credentials and connection settings
├── requirements.txt
├── claude_desktop_config.example.json
├── README.md
└── services/
    └── pi_system/                     ← your existing PI service layer
        ├── __init__.py
        ├── base.py                    ← PISystem base class + batch helpers
        ├── assetserver.py
        ├── assetdatabase.py
        ├── elements.py
        ├── elementtemplates.py
        ├── attributes.py
        ├── dataserver.py
        ├── points.py
        ├── streams.py
        └── streamset.py
```

`app.py` does three things only:
1. Boots up the service instances using `config.py`
2. Declares MCP tools (names, descriptions, input schemas)
3. Routes each tool call to the right service method

All the actual PI Web API logic lives in `services/pi_system/` — same as your backend.

---

## Setup

**1. Install dependencies**

```bash
cd mcp
pip install -r requirements.txt
```

**2. Set your credentials in `config.py`**

```python
PI_HOST   = "https://your-vm-ip"
PI_USER   = "piadmin"
PI_PASS   = "your-password"
PI_SERVER = "PI-SYSTEM"
AF_DATABASE = "GoogleManualLogger"
```

Or use environment variables:

```bash
set PI_HOST=https://192.168.1.50
set PI_USER=piadmin
set PI_PASS=yourpassword
```

**3. Register with Claude Desktop**

Find the config file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac:     `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this (update the path):

```json
{
  "mcpServers": {
    "pi-system": {
      "command": "python",
      "args": ["C:/Users/YOU/af-builder/mcp/app.py"]
    }
  }
}
```

**4. Restart Claude Desktop** — look for the 🔨 hammer icon in the chat input.

---

## Available tools

| Tool | Service method |
|---|---|
| `list_asset_servers` | `AssetServer.lists()` |
| `get_asset_server` | `AssetServer.get()` |
| `get_asset_database` | `AssetDatabases.get()` |
| `get_asset_database_by_path` | `AssetDatabases.get_by_path()` |
| `get_database_elements` | `AssetDatabases.get_elements()` |
| `get_all_elements` | `PISystem.get_all_elements()` — batch: Locations + PowerPlants + Units |
| `get_element` | `Elements.get()` |
| `get_element_by_path` | `Elements.get_by_path()` |
| `get_element_template` | `ElementTemplates.get()` |
| `get_element_template_by_path` | `ElementTemplates.get_by_path()` |
| `get_attribute` | `Attributes.get()` |
| `get_attribute_by_path` | `Attributes.get_by_path()` |
| `set_attribute_value` | `Attributes.set_value()` |
| `list_data_servers` | `DataServer.lists()` |
| `get_data_server_points` | `DataServer.get_points()` |
| `get_point` | `Points.get()` |
| `get_stream_value` | `Streams.get_value()` |
| `update_stream_value` | `Streams.update_value()` |
| `get_data_from_database` | `PISystem.get_data_from_database()` — batch: elements + attributes |

---

## Test prompts to try in Claude Desktop

Start read-only:

```
List all asset servers
```

```
Get all elements from the GoogleManualLogger database
```

```
Use get_element_by_path to fetch GoogleManualLogger\DataGrid\Cebu
```

Then try the batch call:

```
Use get_all_elements with database path \\PI-SYSTEM\GoogleManualLogger
to show me all Locations, PowerPlants, and Units
```

---

## Note on the services folder

The `services/pi_system/` files here are a copy from the backend for standalone Claude Desktop testing.
When the full web app is wired up, `app.py` will import directly from `../backend/services/pi_system/`
instead of keeping a local copy.