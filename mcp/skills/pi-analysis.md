# Skill: PI Analysis

**Trigger:** Use this skill when the task involves reading existing analyses on AF elements,
verifying analysis expressions, or checking the output of derived attributes.

Prerequisite: `pi-tag-creator` skill must have completed — all raw attributes must be
linked to PI tags before derived attributes can be verified.

---

## Available MCP tools for this skill

| Tool | When to use |
|---|---|
| `get_element_by_path` | Get the element WebId before reading its analyses |
| `get_attribute_by_path` | Check a derived attribute's current value and data reference |
| `get_stream_value` | Read the live computed value of a derived attribute |
| `get_data_from_database` | Batch: pull all elements + attributes for a given template |

---

## Derived attributes in this project

These attributes are computed — they do not map to raw PI tags.
Their values come from PI Analysis expressions.

| Attribute | Expected source | Example expression |
|---|---|---|
| `VC_Mag` | Analysis expression | `Sqrt(Sqr('VA_Mag') + Sqr('VB_Mag'))` |
| `VC_Phase` | Analysis expression | `Atan2('VA_Phase', 'VB_Phase') * 180 / PI()` |

---

## Formula list expected format

The client must provide a formula list with these columns.
Validate before running — stop and surface errors if columns are missing.

| Column | Required | Notes |
|---|---|---|
| `element_path` | Yes | AF path to the element the analysis lives on |
| `analysis_name` | Yes | e.g. `Analysis1` |
| `variable_name` | Yes | e.g. `Variable1` |
| `expression` | Yes | PI expression string |
| `output_attribute` | Yes | Target derived attribute e.g. `VC_Mag` |
| `scheduling` | Yes | `EventTriggered` or `Periodic` |
| `trigger` | No | `Any Input` for EventTriggered, interval for Periodic |

---

## Step-by-step execution

### Step 1 — Confirm raw attributes are linked first
```
Tool: get_attribute_by_path
Check: VA_Mag, VA_Phase, VB_Mag, VB_Phase all have DataReferencePlugIn = "PI Point"
If any raw attribute is not linked: stop — analysis cannot compute without source data
Surface the missing links to the BA before continuing
```

### Step 2 — Read the derived attribute current state
```
Tool: get_attribute_by_path
Input path: \\PI-SYSTEM\GoogleManualLogger\DataGrid\<Location>\<Plant>\<Unit>|VC_Mag
Check: DataReferencePlugIn — should be null or "PI Point" depending on setup
Check: current value — if 0 or "No Data", analysis may not be running
```

### Step 3 — Read the live computed value
```
Tool: get_stream_value
Input web_id: <VC_Mag attribute WebId>
Expected: a computed numeric value
If "No Data": PI Analysis Service may not be running or expression has an error
Flag this in the report — do not attempt to fix automatically
```

### Step 4 — Batch verification across all Units
```
Tool: get_data_from_database
Input database_path: \\PI-SYSTEM\GoogleManualLogger
Input template_name: Unit
Returns: all Unit elements with their attributes
Use this to verify VC_Mag and VC_Phase across all units at once
More efficient than checking each unit individually
```

---

## Supported PI expression functions

Only use functions from this list. Never invent function names.

**Math:** `Abs`, `Acos`, `Asin`, `Atan`, `Atan2`, `Ceiling`, `Cos`, `Exp`,
`Floor`, `Ln`, `Log`, `Log10`, `Mod`, `Round`, `Sign`, `Sin`, `Sqrt`, `Tan`, `Truncate`

**Logic:** `If`, `And`, `Or`, `Not`, `IsSet`, `IsNoData`

**String:** `Concat`, `Left`, `Len`, `Mid`, `Right`, `Trim`, `Upper`, `Lower`

**Statistics:** `Average`, `Count`, `Maximum`, `Minimum`, `Range`, `StdDev`, `Total`

**Time-series:** `TagVal`, `PrevVal`

**Common patterns for electrical attributes:**
```
Magnitude:   Sqrt(Sqr('VA_Mag') + Sqr('VB_Mag'))
Phase angle: Atan2('VA_Phase', 'VB_Phase') * 180 / PI()
```

---

## Note on analysis creation

`create_analysis` is intentionally not in the current MCP tools.
During exploration phase, analyses are created manually in PI System Explorer
by the BA using the Analyses tab.

This skill handles verification of existing analyses only — reading outputs,
confirming the Analysis Service is running, and surfacing problems.

`create_analysis` will be added once the read/verify workflow is stable
and the BA has approved the formula list.

---

## Error handling

| Error | Action |
|---|---|
| Raw attribute not linked | Stop — surface to BA, do not proceed |
| Derived attribute = "No Data" | Flag in report — likely analysis not running |
| Expression references missing attribute | Stop this analysis, surface to BA |
| `get_stream_value` returns 400/500 | Log error, skip, flag in report |

---

## Output of this skill

- For each derived attribute (VC_Mag, VC_Phase) across all Units:
  - Current computed value (or "No Data")
  - Whether the analysis is connected to PI Analysis Service
  - Any expressions that reference attributes that don't exist
- Summary: N attributes verified, N with data, N with no data, N errors

This is the final verification step. Surface the full report to the BA for approval.