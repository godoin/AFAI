# CLAUDE.md — AF Builder (Root)

This file tells Claude what AF Builder is, how it works, and how to behave when assisting with this project.

---

## Project summary

AF Builder is a locally-hosted web application that automates OSIsoft PI System Asset Framework (AF) hierarchy creation. A Business Analyst provides a tag list and formula list; the AI generates the full AF configuration and the BA validates and approves it.

**Core mental model:** The BA is the "vibe coder" — AI does the heavy lifting, the BA reviews and signs off.

---

## Tech stack

- **Frontend:** React + Vite
- **Backend:** Python (FastAPI) — runs on the PI System VM
- **AI:** Anthropic Claude API (`claude-sonnet-4-5`, off-the-shelf, no fine-tuning)
- **MCP Server:** Local Python MCP server on the same VM
- **PI Integration:** PI AF SDK or PI Web API
- **Deployment:** All components run on the Hyper-V guest VM running PI System

---

## Repository structure

```
af-builder/
├── README.md
├── CLAUDE.md                  ← You are here
├── GUARDRAILS.md
├── frontend/
│   ├── CLAUDE.md
│   └── src/
├── backend/
│   ├── CLAUDE.md
│   └── src/
└── .claude/
    └── skills/
        ├── pi-af-builder.md
        ├── pi-tag-creator.md
        └── pi-analysis.md
```

---

## Domain knowledge

### PI System concepts Claude must understand

| Term | Meaning |
|---|---|
| AF | Asset Framework — hierarchical model of physical assets in PI System |
| Element | A node in the AF hierarchy (e.g. Company, Location, PowerPlant, Unit) |
| Element Template | A reusable definition of an element type with preset attribute templates |
| Attribute | A property of an element (e.g. VA_Mag, Status, Timestamp) |
| Attribute Template | A reusable definition of an attribute type |
| PI Tag / Point | A time-series data point stored in PI Data Archive |
| Data Reference | How an attribute gets its value — usually "PI Point" linking attribute to a tag |
| Analysis | A formula expression that derives a value from other attributes |
| Raw attribute | Value sourced directly from a PI tag (real-time data) |
| Derived attribute | Value computed from a formula using other attributes |
| Point Builder | Tool in PI System Management Tools to create/manage PI tags |
| AF SDK | .NET SDK for programmatic PI AF access |
| PI Web API | REST API for PI System |

### Standard AF hierarchy for this project

```
DataGrid (root)
└── Location (e.g. Cebu, Davao, Manila)
    └── PowerPlant (e.g. Plant A, Plant B)
        └── Unit (e.g. Unit1, Unit2, Unit3)
            └── Attributes: Status, Timestamp, VA_Mag, VA_Phase, VB_Mag, VB_Phase, VC_Mag, VC_Phase
```

### Standard attribute types

| Attribute | Type | Source |
|---|---|---|
| Status | String | PI Point (raw) |
| Timestamp | Timestamp | PI Point (raw) |
| VA_Mag | Float32 | PI Point (raw) |
| VA_Phase | Float32 | PI Point (raw) |
| VB_Mag | Float32 | PI Point (raw) |
| VB_Phase | Float32 | PI Point (raw) |
| VC_Mag | Float32 | PI Point (derived — formula) |
| VC_Phase | Float32 | PI Point (derived — formula) |

---

## How Claude should behave in this project

### Do
- Follow the step-by-step process: validate input → map structure → create templates → create elements → create tags → assign data refs → create analyses
- Always surface ambiguities to the BA before executing
- Treat every PI System action as irreversible — double-check before calling MCP tools
- Use the skills in `.claude/skills/` for domain-specific tasks
- Refer to GUARDRAILS.md before taking any action that modifies PI System

### Do not
- Delete any AF element, template, or PI tag without explicit BA confirmation
- Create analyses without a validated formula list
- Proceed if the tag list or formula list is malformed or incomplete
- Assume a tag exists — always verify via Point Builder before referencing
- Make up PI tag names or attribute names not present in the input

---

## MCP tools available

| Tool | What it does |
|---|---|
| `create_element_template` | Creates a new element template in AF library |
| `create_attribute_template` | Adds an attribute template to an element template |
| `create_element` | Creates an element under a parent in the hierarchy |
| `create_pi_tag` | Creates a PI point/tag in Point Builder |
| `set_data_reference` | Links an attribute to a PI tag via PI Point data reference |
| `create_analysis` | Creates an analysis expression for an element |
| `verify_tag_exists` | Checks whether a PI tag exists before referencing it |
| `get_element_tree` | Returns the current AF hierarchy for a given root |

---

## Key constraints

- All processing happens on the local VM — no cloud storage of PI data
- Claude API key is stored server-side only, never exposed to the frontend
- The BA must explicitly approve before any write to PI System
- Derived attributes require a validated formula — never guess formulas
- AF deletion is a prohibited action without a senior BA and an explicit two-step confirmation