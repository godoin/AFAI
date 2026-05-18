# Skill: PI Analysis Creator

**Trigger:** Use this skill when the task involves creating PI Analysis expressions for derived AF attributes — formulas that compute values from other attributes or PI tags.

---

## What this skill does

Creates PI Analysis definitions on AF elements for derived attributes. Analyses run in PI Analysis Service and continuously write computed values back to output attributes (or PI tags).

---

## Prerequisites before running

- [ ] `pi-af-builder` and `pi-tag-creator` skills are complete
- [ ] All raw attributes have PI Point data references assigned and confirmed
- [ ] Formula list is validated — all required columns present
- [ ] No formula references an attribute that does not exist in the AF element
- [ ] BA has approved the preview

---

## Formula list expected format

| Column | Required | Description |
|---|---|---|
| `element_path` | Yes | AF path e.g. `DataGrid\Cebu\Plant B\Unit1` |
| `analysis_name` | Yes | Name of the analysis e.g. `Analysis1` |
| `variable_name` | Yes | Variable identifier in the expression e.g. `Variable1` |
| `expression` | Yes | PI expression string e.g. `Abs('VA_Mag')` |
| `output_attribute` | Yes | Target AF attribute e.g. `VC_Mag` |
| `scheduling` | Yes | `EventTriggered` or `Periodic` |
| `trigger` | No | For EventTriggered: `Any Input`. For Periodic: interval e.g. `1h` |

---

## Step-by-step execution

### Phase 1 — Validate formula references

Before creating any analysis, verify that every attribute referenced in the expression exists on the element.

For each expression variable:
- Parse the expression for attribute references (quoted names e.g. `'VA_Mag'`)
- Confirm each referenced attribute exists on the target element via `get_element_tree`
- If any referenced attribute is missing — **stop and surface to BA, do not proceed**

### Phase 2 — Create Analysis

```
Tool: create_analysis
Input:
  - element_path: <element_path>
  - analysis_name: <analysis_name>      e.g. "Analysis1"
  - analysis_type: "Expression"         default for formula-based
  - variable_name: <variable_name>      e.g. "Variable1"
  - expression: <expression>            e.g. "Abs('VA_Mag')"
  - output_attribute: <attribute>       e.g. "VC_Mag"
  - scheduling: <scheduling>            "EventTriggered" or "Periodic"
  - trigger_on: <trigger>               e.g. "Any Input" or "1h"
```

### Phase 3 — Verify analysis status

After creation, check that the analysis is connected to PI Analysis Service.

Expected status: `Connected to the PI Analysis Service` (visible in PI System Explorer → Analyses tab, bottom status bar).

If not connected after 30 seconds — log warning, continue, flag in report for BA to manually check.

---

## Supported PI expression functions

The following functions are available in PI Analysis expressions. Claude must only use functions from this list — never invent function names.

**Math:**
`Abs`, `Acos`, `Asin`, `Atan`, `Atan2`, `Ceiling`, `Cos`, `Exp`, `Floor`, `Ln`, `Log`, `Log10`, `Mod`, `Round`, `Sign`, `Sin`, `Sqrt`, `Tan`, `Truncate`

**Comparison / Logic:**
`If`, `And`, `Or`, `Not`, `IsSet`, `IsNoData`

**String:**
`Concat`, `Left`, `Len`, `Mid`, `Right`, `Trim`, `Upper`, `Lower`

**Time / Statistics:**
`Average`, `Count`, `Maximum`, `Minimum`, `Range`, `StdDev`, `Total`, `TagVal`, `PrevVal`

**Phase calculations (common for electrical attributes):**
`Sqrt(Sqr('VA_Mag') + Sqr('VB_Mag'))` — magnitude calculation pattern
`Atan2('VA_Phase', 'VB_Phase') * 180 / PI()` — phase angle pattern

---

## Naming conventions

Analysis names follow the pattern:

```
Analysis<N>           e.g. Analysis1, Analysis2
```

Or descriptive names if provided in the formula list:

```
VC_Magnitude_Calc
VC_Phase_Calc
```

Variable names follow the pattern:

```
Variable<N>           e.g. Variable1
```

---

## Error handling

| Error | Action |
|---|---|
| Referenced attribute not found | Stop this analysis, surface to BA, skip, continue with next |
| Invalid function name in expression | Surface to BA — do not create with invalid function |
| Analysis already exists with same name | Ask BA: overwrite or skip? Never auto-overwrite |
| Analysis service not connected after 60s | Log warning, flag in report, continue |
| Tool call fails 2x | Stop and surface to BA |

---

## Output

After this skill completes:

- All derived attributes have an analysis created under the element's Analyses tab
- Each analysis shows the correct expression, variable mapping, and output attribute
- Analysis status shows "Connected to PI Analysis Service"
- Validation report section: "Analyses created: N, Skipped: N, Warnings: N, Errors: N"

---

## Full job complete

When all three skills have run successfully:

1. Generate the full validation report (totals across all three phases)
2. Present the report to the BA for final review
3. Wait for BA approval or rejection
4. On approval — write the final audit log entry and mark job as `APPROVED`
5. On rejection — mark job as `REJECTED`, log the reason, do not re-execute automatically