# Skill: PI AF Tag Builder

**Trigger:** Use this skill when the task involves reading or navigating the AF hierarchy —
fetching elements, element templates, attribute templates, and understanding the current
structure before any write operation.

This skill is read-first. Always understand what exists before creating anything.

---

## Available MCP tools for this skill

| Tool | When to use |
|---|---|
| `list_asset_servers` | First call — confirm PI Web API is reachable |
| `get_asset_database_by_path` | Get the WebId of the target AF database |
| `get_database_elements` | List top-level elements under the database |
| `get_all_elements` | Batch fetch all Locations, PowerPlants, and Units in one call |
| `get_element_by_path` | Get a specific element by its relative path |
| `get_element_template` | Inspect a template by WebId |
| `get_element_template_by_path` | Inspect a template by path |
| `get_attribute_by_path` | Get a specific attribute and its current data reference |

---

## Standard AF hierarchy for this project

```
\\PI-SYSTEM\GoogleManualLogger\
└── DataGrid                        (root element)
    └── Location                    e.g. Cebu, Davao, Manila
        └── PowerPlant              e.g. Plant A, Plant B
            └── Unit                e.g. Unit1, Unit2, Unit3
                └── Attributes
                    ├── Status          String  · PI Point (raw)
                    ├── Timestamp       Timestamp · PI Point (raw)
                    ├── VA_Mag          Double · V · PI Point (raw)
                    ├── VA_Phase        Double · ° · PI Point (raw)
                    ├── VB_Mag          Double · V · PI Point (raw)
                    ├── VB_Phase        Double · ° · PI Point (raw)
                    ├── VC_Mag          Double   · Derived (formula)
                    └── VC_Phase        Double   · Derived (formula)
```

---

## Step-by-step: reading the hierarchy

### Step 1 — Verify connection
```
Tool: list_asset_servers
Expected: list of servers including PI-SYSTEM
If empty or error: stop — PI Web API is not reachable
```

### Step 2 — Get the database
```
Tool: get_asset_database_by_path
Input path: \\PI-SYSTEM\GoogleManualLogger
Save the returned WebId for subsequent calls
```

### Step 3 — Fetch the full element tree
```
Tool: get_all_elements
Input database_path: \\PI-SYSTEM\GoogleManualLogger
Returns: all Locations, PowerPlants, and Units in one batch
Use this as the baseline map before any writes
```

### Step 4 — Inspect a specific element
```
Tool: get_element_by_path
Input path: GoogleManualLogger\DataGrid\Cebu\Plant B\Unit1
Returns: element details including WebId, template, and attribute links
```

### Step 5 — Inspect attributes
```
Tool: get_attribute_by_path
Input path: \\PI-SYSTEM\GoogleManualLogger\DataGrid\Cebu\Plant B\Unit1|VA_Mag
Returns: attribute details including current data reference and value type
```

---

## Rules for this skill

- Always run `get_all_elements` before any create or modify operation — never assume the hierarchy matches the input file
- If `get_element_by_path` returns not found, the element does not exist — do not reference it in subsequent tools
- Surface the full element tree to the BA before proceeding to `pi-tag-creator` skill
- Never call a write tool from this skill — this skill is read-only navigation

---

## Output of this skill

A clear map of what currently exists in PI System:
- Which Locations, PowerPlants, and Units are already created
- Which element templates exist
- Which attributes already have data references assigned
- Gaps vs the input tag list — elements or attributes that are missing

Hand this map to the BA before proceeding.
Proceed to `pi-tag-creator` skill next.