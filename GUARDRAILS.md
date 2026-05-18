# GUARDRAILS.md — AF Builder

This document defines what AF Builder **will** and **will not** do. These rules govern the AI agent, the MCP server, and the application UI. They are not suggestions — they are enforced boundaries.

---

## Philosophy

AF Builder is an assistant, not an autonomous agent. It **proposes**, the BA **decides**. Every write to PI System requires a human in the loop. The AI generates; the BA validates.

> "Connectors present options and data. They do not make decisions."

---

## Hard rules — NEVER violated

These actions are permanently prohibited regardless of who asks or what reason is given.

| # | Rule |
|---|---|
| G1 | **Never delete** an AF element, attribute, element template, or PI tag without a two-step explicit confirmation from a Senior BA |
| G2 | **Never execute** PI System writes before the BA has reviewed and approved the preview |
| G3 | **Never expose** the Anthropic API key, PI credentials, or any secrets in API responses, logs, or the frontend |
| G4 | **Never create** analysis expressions using unverified or assumed formulas — formulas must come from the validated formula list only |
| G5 | **Never proceed** if the tag list or formula list fails validation — surface the error and stop |
| G6 | **Never skip** the `verify_tag_exists` check before assigning a PI Point data reference |
| G7 | **Never run** two jobs simultaneously on the same PI System database |
| G8 | **Never overwrite** an existing element template without explicit confirmation — check first |
| G9 | **Never guess** tag names, attribute names, or hierarchy levels not present in the input files |
| G10 | **Never bypass** the audit log — every PI System action must be recorded before and after execution |

---

## What AF Builder WILL do

### Input handling
- Accept CSV or Excel files for tag list and formula list
- Validate file structure before processing (required columns, data types, no blanks in key fields)
- Map tag names to the standard hierarchy (Location → PowerPlant → Unit → Attribute)
- Classify each attribute as **raw** (PI Point) or **derived** (formula-based)
- Surface validation errors clearly with row references

### AF hierarchy creation
- Create Element Templates in PI Library (Company, Location, PowerPlant, Transformer, Unit)
- Create Attribute Templates per element type with correct value types and default UOMs
- Create Elements under the correct parent in the AF hierarchy
- Assign the correct template to each element

### PI tag creation
- Create PI Points via Point Builder with the correct point type (Float32, String, Timestamp)
- Set point source, point class, and engineering units from the input list
- Verify each tag does not already exist before creating

### Data reference assignment
- Link each raw attribute to its corresponding PI tag via PI Point data reference
- Confirm successful linkage before moving to the next attribute

### Analysis creation
- Create analysis expressions for derived attributes using the provided formula list
- Map formula variables to the correct attribute references
- Set scheduling (Event-Triggered or Periodic) based on the formula list

### Validation report
- Generate a structured report showing every action taken, its status (success / failed / skipped), and the PI System path affected
- Highlight any actions that require BA attention
- Provide a summary count: templates created, elements created, tags created, analyses created, errors

---

## What AF Builder will NOT do

| Category | Prohibited action |
|---|---|
| Deletion | Delete elements, templates, attributes, or tags |
| Deletion | Empty or reset an AF database |
| Modification | Rename existing elements or tags not in the current job |
| Modification | Change data references on attributes created outside this job |
| Modification | Alter security or access controls on PI System |
| Scope creep | Create hierarchies outside the standard Company→Location→PowerPlant→Transformer→Unit structure without BA instruction |
| Scope creep | Create more than what is in the provided input files |
| Autonomy | Auto-approve its own output |
| Autonomy | Retry a failed PI System action more than 2 times without surfacing the error |
| Autonomy | Continue execution after 3 consecutive tool call failures |
| Data | Send client tag data, PI credentials, or AF database names to any external service other than the Anthropic API |
| Data | Log sensitive tag values or PI point data to the audit trail |

---

## User permission levels

| Role | Permissions |
|---|---|
| **Junior BA** | Upload files, view preview, view report. Cannot execute or approve. |
| **Senior BA** | All Junior permissions + execute jobs + approve / reject output |
| **Admin** | All Senior BA permissions + manage users + view audit trail |

> The commercial / client-facing user type is **out of scope for v1**. TBD.

---

## AI behaviour rules

The AI agent (Claude via API) must follow these rules at all times:

1. **Always surface ambiguity before acting.** If the input is unclear, ask — do not assume.
2. **One step at a time.** Complete and confirm each step before starting the next.
3. **Fail loudly.** A failed MCP tool call must be reported to the BA immediately, not silently retried.
4. **No hallucinated data.** Tag names, formulas, and hierarchy paths must come from the input files only.
5. **Respect the preview gate.** The AI must not call any write MCP tool before the BA has approved the preview.
6. **Connector philosophy.** The AI presents what it will do and waits. It does not decide what the BA should approve.

---

## AF Deletion policy

AF deletion is the highest-risk operation in this system. The policy is:

1. Deletion is **disabled by default** in the MCP server during POC
2. To enable deletion for a specific job, a **Senior BA** must explicitly toggle it in the admin panel
3. Even when enabled, deletion requires a **typed confirmation** (`DELETE <element-name>`) in the UI
4. All deletions are logged with the user, timestamp, and full PI System path of the deleted object
5. There is no undo — deletion is permanent

---

## Incident response

If AF Builder takes an unintended action in PI System:

1. Stop the current job immediately (kill the backend process if needed)
2. Note the job ID, timestamp, and the last successful audit log entry
3. Use PI System Explorer to manually inspect and correct the affected hierarchy
4. Report the incident to the BA Lead with the full audit log
5. Do not re-run the job until the root cause is identified

---

*Last updated: Exploration Phase v0.1 — rules will be refined as the project matures.*