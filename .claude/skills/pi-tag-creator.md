# Skill: PI AF Hierarchy Builder

**Trigger:** Use this skill when the task involves creating or modifying an AF element hierarchy in PI System Explorer — including element templates, attribute templates, and element instances.

---

## What this skill does

Guides the AI through the correct sequence of steps to build a complete AF hierarchy from a validated input list. Covers template creation in the Library and element creation under Elements.

---

## Prerequisites before running

- [ ] Tag list has been uploaded and validated (no missing columns, no blank tag names)
- [ ] Formula list has been uploaded (even if empty — confirms derived attributes)
- [ ] BA has reviewed and approved the preview
- [ ] `verify_tag_exists` has been run for all tags in the list
- [ ] No existing element template with the same name (check before creating)

---

## Step-by-step execution

### Phase 1 — Create Element Templates (Library)

Run these steps **once per project**, not once per element.

**Step 1.1 — Create top-level element templates**

For each template in the standard set (Company, Location, PowerPlant, Transformer, Unit):

```
Tool: create_element_template
Input:
  - name: <template name>
  - database: <AF database name>
  - base_template: null (these are root templates)
```

Expected result: Template appears in Library → Templates → Element Templates.

**Step 1.2 — Create Attribute Templates for each Element Template**

For each attribute in the standard set per template:

```
Tool: create_attribute_template
Input:
  - element_template: <parent template name>
  - name: <attribute name>         e.g. "Status", "VA_Mag"
  - value_type: <type>             e.g. "String", "Double", "Timestamp"
  - default_uom: <unit>            e.g. "V", "°", null
  - data_reference: "PI Point"     for raw attributes
  - data_reference: null           for derived attributes (analysis handles it)
  - default_value: <value>         e.g. "Active" for Status
```

**Standard attribute set for Unit template:**

| Attribute | Value Type | UOM | Source |
|---|---|---|---|
| Status | String | — | PI Point (raw) |
| Timestamp | Timestamp | — | PI Point (raw) |
| VA_Mag | Double | V | PI Point (raw) |
| VA_Phase | Double | ° | PI Point (raw) |
| VB_Mag | Double | V | PI Point (raw) |
| VB_Phase | Double | ° | PI Point (raw) |
| VC_Mag | Double | — | Derived (formula) |
| VC_Phase | Double | — | Derived (formula) |

---

### Phase 2 — Create Elements (Elements tab)

For each row in the tag list, create the hierarchy path if it does not already exist.

**Step 2.1 — Create root element (DataGrid)**

```
Tool: create_element
Input:
  - name: "DataGrid"
  - parent: null (root)
  - template: null
  - database: <AF database>
```

Only create if it does not already exist. Use `get_element_tree` to check first.

**Step 2.2 — Create Location elements**

```
Tool: create_element
Input:
  - name: <location>      e.g. "Cebu", "Davao"
  - parent: "DataGrid"
  - template: "Location"
```

**Step 2.3 — Create PowerPlant elements**

```
Tool: create_element
Input:
  - name: <plant>         e.g. "Plant A"
  - parent: <location>
  - template: "PowerPlant"
```

**Step 2.4 — Create Unit elements**

```
Tool: create_element
Input:
  - name: <unit>          e.g. "Unit1"
  - parent: <plant>
  - template: "Unit"
```

---

### Phase 3 — Verify hierarchy

After all elements are created:

```
Tool: get_element_tree
Input:
  - root: "DataGrid"
  - database: <AF database>
```

Compare the returned tree against the expected structure from the tag list. Surface any missing elements to the BA before proceeding.

---

## Error handling

| Error | Action |
|---|---|
| Template already exists | Skip creation, log "already exists", continue |
| Element already exists | Skip creation, log "already exists", continue |
| Parent element not found | Stop and surface to BA — do not create orphaned elements |
| Tool call fails 2x | Stop phase, surface error, wait for BA instruction |

---

## Output

After this skill completes, the BA should see in PI System Explorer:

- All Element Templates visible in Library → Templates → Element Templates
- All Attribute Templates visible under each Element Template
- Complete element hierarchy under Elements → DataGrid → [Locations] → [Plants] → [Units]

Proceed to `pi-tag-creator` skill next.