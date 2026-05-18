# AF Builder

> AI-assisted AF hierarchy builder for OSIsoft PI System — automating up to 80% of a Business Analyst's configuration workload.

---

## What is AF Builder?

AF Builder is a locally-hosted web application that acts as an AI-powered "vibe coder" for Business Analysts working with OSIsoft PI System Asset Framework (AF). Instead of manually building element hierarchies, assigning attributes, creating PI tags, and writing analysis expressions — the BA provides a structured input list and AF Builder generates everything. The BA then validates and approves the output.

**The model:** AI generates → BA validates. Same team, more projects.

---

## Key capabilities

- Upload a procurement tag list and formula list
- AI interprets and maps inputs to AF structure (Company → Location → PowerPlant → Transformer → Unit)
- Automatically creates Element Templates and Attribute Templates in PI System Explorer
- Creates PI tags via Point Builder in PI System Management Tools
- Assigns Data References (PI Point) to attributes
- Builds Analysis expressions per attribute
- Generates a validation report for the BA to review and approve
- Full audit trail of every action taken

---

## Architecture overview

```
Browser (BA)
    │
    ▼
Web App (Local VM)          ← Python/Node backend, runs on PI System VM
    │
    ├── Claude AI API        ← Anthropic API (off-the-shelf, no training)
    │
    └── MCP Server           ← Local adaptor layer, talks to PI System
            │
            └── PI System    ← PI System Explorer + PI Mgmt Tools (AF SDK / PI Web API)
```

The entire stack runs **on the PI System VM** (Hyper-V guest). No data leaves the local network except the Claude API call, which is controlled via the backend.

---

## Project structure

```
af-builder/
├── README.md                  ← This file
├── GUARDRAILS.md              ← What the AI will and will not do
├── CLAUDE.md                  ← Root AI context for the project
├── frontend/
│   ├── CLAUDE.md              ← Frontend-specific AI context
│   └── src/
├── backend/
│   ├── CLAUDE.md              ← Backend-specific AI context
│   └── src/
└── .claude/
    └── skills/
        ├── pi-af-builder.md   ← Skill: build AF hierarchy
        ├── pi-tag-creator.md  ← Skill: create PI tags
        └── pi-analysis.md     ← Skill: write analysis expressions
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + Vite (simple form UI) |
| Backend | Python (FastAPI) or Node.js (Express) |
| AI | Anthropic Claude API (`claude-sonnet-4-5`) |
| MCP Server | Local MCP server (Python) |
| PI Integration | PI AF SDK (.NET) or PI Web API (REST) |
| Deployment | Local web server on PI System Hyper-V VM |

---

## Getting started

### Prerequisites

- PI System running on a Hyper-V VM
- Node.js 18+ or Python 3.10+
- Anthropic API key
- PI AF SDK or PI Web API access on the VM
- Network access from BA machine to the VM

### Installation

```bash
git clone https://github.com/your-org/af-builder.git
cd af-builder

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY

# Frontend
cd ../frontend
npm install
npm run dev # Vite dev server
```

### Running

```bash
# Start backend (from VM)
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# Start frontend (from VM or local machine)
cd frontend && npm run dev # Vite dev server

# Open browser
http://<vm-ip>:5173
```

---

## User flow

1. BA logs in
2. Uploads tag list (CSV/Excel) and formula list
3. AF Builder validates the input and maps to AF structure
4. BA confirms the structure before execution
5. AI orchestrates all PI System actions via MCP
6. BA reviews the generated validation report
7. BA approves or requests changes
8. Audit log is saved

---

## Status

> **Exploration / POC phase.** Not production-ready. Being evaluated for feasibility before full scoping.

---

## Team

| Role | Responsibility |
|---|---|
| Business Analyst | Domain expert, validation, rules definition |
| Developer | Build and maintain AF Builder |
| BA Lead | Owns guardrails, rules engine, scope decisions |