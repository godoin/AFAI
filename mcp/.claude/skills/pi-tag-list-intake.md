# Skill: PI Tag List Intake

**Trigger:** Use this skill at the start of every new session where the BA provides
a client tag list (Excel or CSV). This skill governs the complete flow from file
intake through tag creation and AF attribute linking. It is the authoritative
sequence — do not skip or reorder phases.

This skill replaces ad-hoc tool calling. Every session follows this document top to bottom.

---

## Session entry — always run first

Before anything else, run this sequence to establish current state:

```
1. list_asset_servers          → confirm PI Web API is reachable
2. get_asset_database_by_path  → get database WebId
3. get_all_elements            → map current AF state (Locations, PowerPlants, Units)
```

If any of these fail, stop. Surface the error to the BA. Do not proceed.

No memory of prior sessions. Never assume what was created before still exists.

---

## Phase 1 — Input intake

Ask the BA:

> "To get started, please provide one of the following:
> - **Tag list** (Excel or CSV) — I will parse, validate, and propose the tag
>   creation plan for your review before any writes occur.
> - *(Future)* AF hierarchy document — not yet in scope.
> - *(Future)* Client dashboard — not yet in scope."

Wait for the file upload. Do not proceed until a file is provided.

Once received, confirm:

> "I have the file. I will now parse it, run validation checks, and build a
> pre-action report for your review before I touch anything in PI System."

---

## Phase 2 — Preprocess

### Step 2.1 — Parse the file

Read all rows and map to the expected columns:

| Column | Required | Notes |
|---|---|---|
| `Plant` | Yes | Maps to PowerPlant element |
| `Unit/System` | Yes | Maps to Unit element |
| `Source Tagname` | Yes | Original tag name from client system |
| `Source Tag` | Yes | Source tag identifier |
| `Proposed New Tagname` | Yes | The PI tag name to create |
| `Canary Tag Path` | No | Canary integration path |
| `Description` | No | Human-readable description |
| `eng_units` | No | e.g. V, bar, A, spm |
| `Date Added` | No | Audit field |
| `Data Tag Naming for Checking (Remarks)` | No | BA notes |

If any required column is missing from the file, stop immediately:

> "The file is missing the following required columns: [list]. I cannot proceed
> until these are present. Please check the file and re-upload."

### Step 2.2 — Naming convention check (per row)

For every row, validate `Proposed New Tagname` against all four rules:

| Rule | Check |
|---|---|
| No spaces | Reject if contains any whitespace |
| No special characters | Only alphanumeric + underscore allowed |
| Follows hierarchy pattern | Must match `Location_Plant_Unit_Attribute` |
| Matches AF element names | Location, Plant, Unit must match AF element names exactly (case-sensitive) |

For each violation:
- Log it with the row number and the original value
- Mark the row `NAMING_VIOLATION` in the pre-action report
- Skip that row for all further processing
- Continue with the next row

Never auto-correct. Never guess the intended value. Surface every violation to the BA.

---

## Phase 3 — Validate

### Step 3.1 — Cross-check against live AF

For each valid row (passed naming checks), verify:

```
Tool: get_element_by_path
Purpose: confirm the parent Unit element exists in AF
If not found → mark row as AF_ELEMENT_MISSING, do not attempt tag creation
```

### Step 3.2 — Cross-check against PI Data Archive

For each valid row:

```
Tool: get_point  OR  search_points (for bulk pattern matching)
Purpose: check whether the Proposed New Tagname already exists as a PI tag
If found → mark row as TAG_ALREADY_EXISTS, skip creation
If not found → mark row as TO_CREATE
```

### Step 3.3 — Build the pre-action report

Compile every row into two Excel sheets:

**Sheet 1 — Summary**

| Field | Value |
|---|---|
| Total rows in file | N |
| Rows passing validation | N |
| Tags to create | N |
| Tags already existing | N |
| AF elements missing | N |
| Naming violations | N |
| Rows skipped (total) | N |

**Sheet 2 — Tags (one row per tag)**

All original columns from the client file, plus:

| Added column | Values |
|---|---|
| `Proposed Action` | `CREATE` · `SKIP — already exists` · `SKIP — AF element missing` · `SKIP — naming violation` |
| `Exists in PI` | `Yes` · `No` · `Not checked` |
| `Exists in AF` | `Yes` · `No` · `Not checked` |
| `Naming Valid` | `Yes` · `No — [reason]` |
| `BA Notes` | Blank — for BA to fill in |

---

## Gate 1 — BA confirmation (mandatory, no exceptions)

Present the pre-action report Excel file to the BA.

State clearly:

> "Here is the pre-action report. Please review before I proceed:
>
> - **[N] tags will be created** in PI Data Archive
> - **[N] tags already exist** — these will be skipped
> - **[N] rows have naming violations** — listed in the Tags sheet
> - **[N] rows have missing AF elements** — the parent Unit does not yet exist
>
> I will not write anything to PI System until you explicitly confirm.
> Reply **'confirmed'** to proceed, or let me know what to change."

Do not proceed until the BA replies with explicit approval.
If the BA requests changes, return to Phase 2 with their corrections.
If the BA says stop, stop. Do not attempt partial execution.

---

## Phase 4 — Implementation

Only runs after Gate 1 approval. Implement rows marked `CREATE` only.

### Step 4.1 — Create PI tags (one per turn)

For each `CREATE` row, in order:

```
1. Confirm tag does not exist (get_point — one final check before write)
2. Call create_pi_tag with:
     web_id          = Data Server WebId (from list_data_servers)
     name            = Proposed New Tagname
     point_type      = inferred from attribute type (see mapping below)
     descriptor      = Description column value
     engineering_units = eng_units column value
     point_class     = "classic"
3. Verify creation with get_point
4. Surface result to BA before moving to next row
```

**Point type mapping from attribute name:**

| Attribute | point_type |
|---|---|
| `Status` | `String` |
| `Timestamp` | `Timestamp` |
| `*_Mag` | `Float32` |
| `*_Phase` | `Float32` |
| `Flow_Rate`, `Pressure`, `Current`, `Speed` | `Float32` |
| `Run_Status`, `Fault_Status` | `Digital` |
| Any other string attribute | `String` |
| Default (unknown) | Ask BA before proceeding |

If `create_pi_tag` returns an error:
- Log it
- Mark the row `FAILED — [error code and message]` in the output report
- Surface to the BA immediately
- Do not retry automatically
- Ask: "Should I skip this tag and continue, or stop here?"

Never create more than one tag per conversation turn without BA confirmation.

### Step 4.2 — Link AF attributes

After all tags in the batch are created and verified:

```
For each successfully created tag:
1. get_attribute_by_path → get attribute WebId
2. Confirm DataReferencePlugIn is not already "PI Point"
3. set_attribute_value → link attribute to the PI tag
4. get_stream_value → verify live data is flowing
5. Surface result per attribute
```

Skip derived attributes (`VC_Mag`, `VC_Phase`) — these are handled by `pi-analysis` skill.

---

## Phase 5 — Output report

After all rows are processed, generate the final output Excel file.

**Sheet 1 — Session summary**

| Field | Value |
|---|---|
| Session date | [date] |
| AF database | [path] |
| Tags created successfully | N |
| Tags already existed (skipped) | N |
| Tags failed | N |
| Tags skipped (naming violation) | N |
| Tags skipped (AF element missing) | N |
| Attributes linked successfully | N |
| Attributes with no live data | N |

**Sheet 2 — Full results (one row per tag)**

All columns from the pre-action report Tags sheet, plus:

| Added column | Values |
|---|---|
| `Final Status` | `CREATED` · `ALREADY EXISTED` · `FAILED` · `SKIPPED` |
| `PI Tag Created` | `Yes` · `No` |
| `AF Attribute Linked` | `Yes` · `No` · `N/A (derived)` |
| `Live Data Received` | `Yes` · `No` · `Not checked` |
| `Error Detail` | Error message if failed, blank otherwise |

Deliver the file to the BA.

State:

> "Session complete. Here is the final report. [N] tags were created successfully,
> [N] were skipped, [N] failed. Please review the Error Detail column for any
> failed rows and advise how to proceed."

---

## Error handling summary

| Condition | Action |
|---|---|
| PI Web API unreachable | Stop session. Surface to BA. Do not continue. |
| Required column missing from file | Stop preprocessing. Surface to BA. Request corrected file. |
| Naming violation | Log, skip row, continue. Surface all violations in pre-action report. |
| AF element not found | Mark row. Skip tag creation. Surface in pre-action report. |
| Tag already exists | Mark row. Skip creation. Include in report as `ALREADY EXISTED`. |
| `create_pi_tag` returns 400 | Log, mark row `FAILED`, surface to BA, ask to skip or stop. |
| `create_pi_tag` returns 409 | Log, mark row `FAILED — CONFLICT`, verify with `get_point`, surface to BA. |
| `create_pi_tag` returns 500 | Log, stop all creates, surface to BA immediately. |
| `set_attribute_value` fails | Log, mark attribute `FAILED`, surface to BA, do not retry. |
| `get_stream_value` returns No Data | Mark attribute `NO LIVE DATA`, flag in report, do not treat as failure. |

---

## Derived attributes — handoff to pi-analysis skill

After this skill completes, if derived attributes (e.g. `VC_Mag`, `VC_Phase`) are
present in the AF template, hand off to the `pi-analysis` skill.

State to BA:

> "Tag creation and attribute linking are complete. The derived attributes
> (VC_Mag, VC_Phase) are computed by PI Analysis and were not part of this
> process. Would you like me to verify the analysis outputs now?"

Do not attempt to create analyses — `create_analysis` is not yet in scope.