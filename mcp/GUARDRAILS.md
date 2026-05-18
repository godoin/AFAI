# GUARDRAILS.md — MCP Server

Rules that govern what the MCP server and AI agent are allowed to do
when operating against PI System via `app.py`. These are not suggestions.

---

## Current phase: exploration / read-heavy

The MCP is in testing phase. The emphasis is on reading and verifying —
not writing. Write tools are intentionally limited.

---

## What the MCP CAN do right now

| Category | Allowed |
|---|---|
| Read | List asset servers, databases, elements, templates, attributes |
| Read | Get element and template details by WebId or path |
| Read | Get stream values (live PI tag data) |
| Read | List data servers and their points |
| Read | Batch fetch all elements and attributes |
| Write | Set configuration item attribute values |
| Write | Update stream values (write to PI tags via streams) |

---

## What the MCP CANNOT do right now (intentionally missing tools)

| Action | Reason not included |
|---|---|
| `create_pi_tag` | Tag creation is irreversible — requires BA to do manually in Point Builder during POC |
| `create_element` | Element creation not yet validated end-to-end |
| `create_element_template` | Template changes affect all elements using that template |
| `create_analysis` | Formula verification must happen before any analysis is written |
| `delete_*` (anything) | Deletion is permanently disabled in exploration phase |
| `update_element` | Element modification not yet in scope |
| `update_element_template` | Template modification not yet in scope |

These tools will be added progressively as each step is validated with a real BA.

---

## Hard rules — never violated

| # | Rule |
|---|---|
| G1 | Never call `update_stream_value` or `set_attribute_value` without the BA explicitly requesting it in the conversation |
| G2 | Never assume a tag or element exists — always call `get_point` or `get_element_by_path` first |
| G3 | Never proceed past a "not found" response — surface it and stop |
| G4 | Never call more than one write tool per conversation turn without BA confirmation in between |
| G5 | Never construct or guess a PI path — use only paths provided in the tag list or returned by a prior tool call |
| G6 | Never surface PI credentials (PI_USER, PI_PASS) in any tool response or conversation message |
| G7 | Never retry a failed write tool call automatically — surface the error and wait for BA instruction |
| G8 | Never skip the naming convention validation step before any tag-related operation |

---

## Tool call sequencing rules

The agent must follow this order. Do not skip steps.

```
1. list_asset_servers          → confirm connection
2. get_asset_database_by_path  → get database WebId
3. get_all_elements            → map current state
4. get_element_by_path         → verify specific element exists
5. get_attribute_by_path       → verify attribute + data reference
6. get_point                   → verify tag exists in PI Data Archive
7. get_stream_value            → verify live data is flowing
8. set_attribute_value         → write only after all above confirmed
   OR update_stream_value
```

Never jump to step 8 without completing steps 1–7 for the relevant element.

---

## Naming convention rules (enforced before any tag operation)

A tag name is valid only if ALL of these pass:

- No spaces
- No special characters except underscore `_`
- Follows `Location_Plant_Unit_Attribute` pattern
- Location, Plant, Unit names match AF element names exactly (case-sensitive)

If a name fails: log the violation, skip that tag, continue with the next.
Never auto-correct a tag name — surface the original and the violation to the BA.

---

## Error behaviour

| HTTP status | Action |
|---|---|
| 400 | Log "malformed request", surface to BA, stop this operation |
| 401 | Log "authentication failed", stop all operations, check credentials |
| 404 | Log "not found", surface to BA, do not proceed |
| 409 | Log "conflict or incompatible units", surface to BA, stop this operation |
| 500 | Log "PI server error", surface to BA, stop all operations |

Never swallow errors silently. Every error surfaces to the BA.

---

## What "surface to the BA" means

Do not just log it internally. In the Claude Desktop conversation:

1. State which tool was called
2. State what the error or result was
3. State what you will NOT do as a result
4. Ask the BA how to proceed

Example:
> "I called `get_point` for tag `Cebu_PlantB_Unit1_VC_Mag` and it was not found in PI Data Archive.
> I will not attempt to set a data reference for this attribute until the tag exists.
> Should I skip this tag and continue with the next, or stop here?"

---

## Session scope

- Each Claude Desktop conversation is a fresh session — no memory of prior sessions
- Always re-read the current state at the start of each session (`get_all_elements`)
- Never assume what was created or verified in a previous conversation still applies

---

## When tools are added

Before adding a new write tool to `app.py`:

1. The read equivalent must be tested and working (e.g. `get_point` before `create_pi_tag`)
2. A BA must have approved the workflow in at least one real test session
3. The tool must be added to both `app.py` and this GUARDRAILS.md
4. The relevant skill file must be updated to include the new tool