# Skill: PI Tag Creator

**Trigger:** Use this skill when the task involves creating PI Points (tags) in PI System Management Tools → Point Builder, and assigning them as Data References to AF attributes.

---

## What this skill does

Creates PI tags from a validated tag list and links each tag to the corresponding AF attribute via a PI Point data reference. This is the bridge between the AF hierarchy and the PI Data Archive.

---

## Prerequisites before running

- [ ] Phase 1 and Phase 2 of `pi-af-builder` skill are complete (templates and elements exist)
- [ ] Tag list is validated — all required columns present
- [ ] BA has approved the preview
- [ ] No concurrent jobs running

---

## Tag list expected format

The input tag list must have these columns:

| Column | Required | Description |
|---|---|---|
| `tag_name` | Yes | Full PI tag name e.g. `Cebu_PlantB_Unit1_Status` |
| `element_path` | Yes | AF path e.g. `DataGrid\Cebu\Plant B\Unit1` |
| `attribute_name` | Yes | AF attribute e.g. `Status` |
| `point_type` | Yes | `Float32`, `String`, `Int32`, `Timestamp` |
| `point_source` | Yes | Usually `L` |
| `engineering_units` | No | e.g. `V`, `°`, blank for dimensionless |
| `description` | No | Human-readable description |

---

## Step-by-step execution

### Phase 1 — Verify existing tags

Before creating any tag, check if it already exists.

```
Tool: verify_tag_exists
Input:
  - tag_name: <tag_name>
  - server: "PI-SYSTEM"
```

- If tag **exists**: skip creation, log "tag already exists", proceed to data reference assignment
- If tag **does not exist**: proceed to creation

### Phase 2 — Create PI tag

```
Tool: create_pi_tag
Input:
  - name: <tag_name>               e.g. "Cebu_PlantB_Unit1_Status"
  - server: "PI-SYSTEM"
  - point_type: <point_type>       e.g. "String", "Float32"
  - point_source: <point_source>   e.g. "L"
  - point_class: "classic"
  - engineering_units: <eng_units> or null
  - description: <description>     or null
```

Expected result: Tag appears in Point Builder with "Real-time data" stored values.

### Phase 3 — Assign Data Reference

Link the PI tag to the AF attribute.

```
Tool: set_data_reference
Input:
  - element_path: <element_path>        e.g. "DataGrid\Cebu\Plant B\Unit1"
  - attribute_name: <attribute_name>    e.g. "Status"
  - data_reference_type: "PI Point"
  - tag_name: <tag_name>
  - server: "PI-SYSTEM"
  - read_only: false
```

Expected result: Attribute shows PI Point data reference in PI System Explorer. Path format: `\\PI-SYSTEM\<tag_name>;ReadOnly=False`

---

## Naming convention

Tag names follow the pattern:

```
<Location>_<Plant>_<Unit>_<Attribute>
```

Examples:
```
Cebu_PlantA_Unit1_Status
Cebu_PlantA_Unit1_VA_Mag
Davao_PlantB_Unit3_VB_Phase
```

Rules:
- No spaces — use underscores
- Location, Plant, and Unit names must match the AF element names exactly
- Attribute name must match the AF attribute name exactly
- All characters must be alphanumeric or underscore

---

## Batch processing

Process tags in this order for each Unit:
1. Status (String)
2. Timestamp
3. VA_Mag, VA_Phase (Phase A)
4. VB_Mag, VB_Phase (Phase B)
5. VC_Mag, VC_Phase (Phase C) — only if raw; skip if derived

Skip derived attributes here — they are handled by `pi-analysis` skill.

---

## Error handling

| Error | Action |
|---|---|
| Tag name contains invalid characters | Surface to BA, skip this tag, continue |
| Point type not recognised | Surface to BA, stop this tag, continue with next |
| Element path not found in AF | Stop and surface — do not create orphaned tags |
| Data reference assignment fails | Log failure, mark attribute as "needs manual attention" in report |
| Tool call fails 2x | Stop and surface error to BA |

---

## Output

After this skill completes:

- All raw tags visible in Point Builder with correct point types
- All raw attributes in AF show PI Point data reference with correct tag path
- Derived attributes still show `<None>` data reference — this is expected
- Validation report section: "Tags created: N, Data references assigned: N, Skipped: N, Errors: N"

Proceed to `pi-analysis` skill next for derived attributes.