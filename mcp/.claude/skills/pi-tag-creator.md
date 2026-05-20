# Skill: PI Tag Creator

**Trigger:** Use this skill when the task involves verifying PI tags exist and linking AF
attributes to PI tags via PI Point data reference. This is the bridge between the AF
hierarchy and live data in PI Data Archive.

Prerequisite: `pi-af-builder` skill must have completed and the element tree confirmed.

---

## Available MCP tools for this skill

| Tool | When to use |
|---|---|
| `list_data_servers` | Confirm the PI Data Archive server is reachable |
| `get_data_server_points` | List existing tags on the Data Server |
| `get_point` | Check a specific tag by name |
| `get_attribute_by_path` | Read current data reference on an attribute |
| `set_attribute_value` | Set a config item attribute value (non-stream) |
| `get_stream_value` | Read the current live value of a stream attribute |
| `update_stream_value` | Write a value to a stream attribute |

---

## Tag list expected format

The client-provided tag list must have these columns before this skill runs.
Claude must validate these are present — stop and surface errors if any are missing.

| Column | Required | Notes |
|---|---|---|
| `Plant` | Yes | Maps to PowerPlant element |
| `Unit/System` | Yes | Maps to Unit element |
| `Source Tagname` | Yes | Original tag name from client system |
| `Source Tag` | Yes | Actual source tag identifier |
| `Proposed New Tagname` | Yes | The PI tag name to create — must follow naming convention |
| `Canary Tag Path` | No | Canary integration path if applicable |
| `Description` | No | Human-readable description |
| `eng_units` | No | e.g. V, deg, blank if none |
| `Date Added` | No | For audit purposes |
| `Data Tag Naming for Checking (Remarks)` | No | BA notes on naming |

---

## Naming convention validation

Before any tag operation, validate `Proposed New Tagname` against these rules:

| Rule | Pattern | Example |
|---|---|---|
| No spaces | Reject if contains space | `Cebu_PlantB_Unit1_VA_Mag` ✓ |
| No special chars | Only alphanumeric + underscore | `Cebu_PlantB_Unit1_VA_Mag` ✓ |
| Follows hierarchy | `Location_Plant_Unit_Attribute` | `Cebu_PlantB_Unit1_Status` ✓ |
| Matches AF path | Location/Plant/Unit names must match AF element names exactly | — |

If a tag name fails validation — log it, skip that tag, continue with the next.
Surface all naming violations to the BA at the end as a batch — not one by one.

---

## Step-by-step execution

### Step 1 — Confirm Data Server is reachable
```
Tool: list_data_servers
Expected: PI-SYSTEM in the list
If not found: stop — cannot verify or create tags
```

### Step 2 — Check existing tags
```
Tool: get_point
Input tag_name: <Proposed New Tagname>
If found: skip creation, log "already exists", proceed to Step 4
If not found: surface to BA — tag needs to be created manually in Point Builder
             (create_pi_tag is not yet in the MCP — see note below)
```

### Step 3 — Read current attribute data reference
```
Tool: get_attribute_by_path
Input path: \\PI-SYSTEM\GoogleManualLogger\DataGrid\<Location>\<Plant>\<Unit>|<Attribute>
Check: does DataReferencePlugIn = "PI Point" already?
If yes: log "already linked", skip Step 4
If no: proceed to Step 4
```

### Step 4 — Set attribute value (config items only)
```
Tool: set_attribute_value
Input web_id: <attribute WebId from Step 3>
Input value:  <value from tag list>
Only for configuration item attributes (non-stream)
For stream attributes (PI Point linked): use update_stream_value instead
```

### Step 5 — Verify live value
```
Tool: get_stream_value
Input web_id: <attribute WebId>
Confirms the attribute is receiving data from PI Data Archive
If value = "No Data": flag in report — tag may not be sending data yet
```

---

## Note on tag creation

`create_pi_tag` is intentionally not in the current MCP tools.
During exploration phase, tags are created manually in Point Builder by the BA.
The MCP handles verification and data reference assignment only.

This is a guardrail — tag creation is a write operation that can't be undone easily.
Once the workflow is validated end-to-end, `create_pi_tag` will be added with full
BA confirmation flow.

---

## Batch processing order per Unit

Process attributes in this order for each Unit element:

1. `Status` (String — config item)
2. `Timestamp` (Timestamp)
3. `VA_Mag`, `VA_Phase` (Phase A — raw)
4. `VB_Mag`, `VB_Phase` (Phase B — raw)
5. Skip `VC_Mag`, `VC_Phase` — these are derived, handled by `pi-analysis` skill

---

## Error handling

| Error | Action |
|---|---|
| Tag not found | Log "tag missing", skip data ref assignment, flag for BA |
| Naming violation | Log violation with row number, skip, continue |
| Attribute not found in AF | Stop this unit, surface to BA — do not continue |
| `set_attribute_value` returns 400 | Log "malformed request", skip, continue |
| `set_attribute_value` returns 409 | Log "incompatible units", flag for BA review |

---

## Output of this skill

- List of attributes successfully linked to PI tags
- List of attributes skipped (already linked)
- List of tags missing from PI Data Archive (needs manual creation)
- List of naming violations
- Live value check results (receiving data / no data)

Proceed to `pi-analysis` skill for derived attributes (VC_Mag, VC_Phase).