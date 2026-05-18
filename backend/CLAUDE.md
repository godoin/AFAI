# CLAUDE.md — Backend

Context for Claude when working on the AF Builder backend.

---

## Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **AI SDK:** `anthropic` Python SDK
- **MCP:** `mcp` Python library (local server)
- **PI Integration:** PI Web API (REST) or `clr` bridge to PI AF SDK (.NET)
- **Job queue:** In-memory (POC) → Redis (production)
- **Validation:** Pydantic v2
- **File parsing:** `pandas`, `openpyxl`

---

## Folder structure

```
backend/
├── CLAUDE.md               ← You are here
├── main.py                 ← FastAPI app entrypoint
├── requirements.txt
├── .env.example
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py      ← POST /upload/tags, /upload/formulas
│   │   │   ├── jobs.py        ← GET/POST /jobs/:id/*
│   │   │   └── auth.py        ← POST /auth/login
│   │   └── deps.py            ← Shared dependencies (auth, DB)
│   ├── services/
│   │   ├── ai_orchestrator.py ← Calls Claude API, builds system prompt
│   │   ├── mcp_client.py      ← Calls MCP server tools
│   │   ├── pi_validator.py    ← Validates tag list, formula list
│   │   └── job_service.py     ← Job lifecycle management
│   ├── mcp/
│   │   ├── server.py          ← MCP server definition
│   │   └── tools/
│   │       ├── af_tools.py    ← PI AF element/template creation tools
│   │       ├── tag_tools.py   ← PI tag creation tools
│   │       └── analysis_tools.py ← PI analysis creation tools
│   ├── models/
│   │   ├── job.py             ← Job, JobStatus, JobStep
│   │   ├── tag.py             ← ParsedTag, TagList
│   │   └── af.py              ← AFElement, AFTemplate, AFAttribute
│   └── utils/
│       ├── parser.py          ← CSV/Excel parsing
│       └── audit.py           ← Audit log writer
```

---

## Environment variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...          # Required — never commit this
PI_WEB_API_URL=https://pi-system:443  # PI Web API base URL
PI_USERNAME=piadmin                    # PI System credentials
PI_PASSWORD=...                        # Never commit this
AF_DATABASE=GoogleManualLogger         # Target AF database
SECRET_KEY=...                         # JWT signing key
```

---

## AI orchestration pattern

The backend calls Claude with a structured system prompt and the BA's input. Claude responds with a sequence of MCP tool calls. The backend executes each tool call against the local MCP server, collects results, and feeds them back to Claude until the task is complete.

```python
# Simplified flow
async def orchestrate(job: Job) -> JobResult:
    messages = build_initial_messages(job)
    
    while True:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            system=SYSTEM_PROMPT,         # loaded from skills
            tools=MCP_TOOL_DEFINITIONS,
            messages=messages
        )
        
        if response.stop_reason == "end_turn":
            break
            
        # Execute tool calls
        tool_results = []
        for tool_use in response.content:
            if tool_use.type == "tool_use":
                result = await mcp_client.call(tool_use.name, tool_use.input)
                tool_results.append(result)
                
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    
    return build_result(response)
```

---

## API routes

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | BA login |
| POST | `/upload/tags` | Upload tag list CSV/Excel |
| POST | `/upload/formulas` | Upload formula list |
| GET | `/jobs/:id/preview` | Get mapped AF structure preview |
| POST | `/jobs/:id/execute` | Start PI System execution |
| GET | `/jobs/:id/status` | Poll job progress |
| GET | `/jobs/:id/report` | Get validation report |
| POST | `/jobs/:id/approve` | BA approval → write audit log |
| POST | `/jobs/:id/reject` | BA rejection with reason |

---

## Rules Claude must follow in the backend

### Security
- `ANTHROPIC_API_KEY` is loaded from `.env` only — never hardcoded, never logged, never returned in any API response
- PI credentials are server-side only
- All user input is validated through Pydantic models before processing

### PI System safety
- Every MCP tool call is logged to the audit trail before and after execution
- The `delete` family of tools does not exist in the MCP server during POC
- Tag creation is idempotent — check existence before creating (`verify_tag_exists` first)
- Analysis creation only runs after the tag/data-reference step is confirmed successful

### Job lifecycle
- Jobs are immutable once in `APPROVED` state
- Jobs in `EXECUTING` state cannot be cancelled mid-run (PI System writes are not transactional)
- All job state transitions are logged with timestamps

### Error handling
- Wrap every MCP tool call in try/except — a single failed tool call should not crash the job
- Return structured errors: `{ step, tool, error, recoverable: bool }`
- Never return raw PI System error messages to the frontend — sanitise first

---

## What Claude should NOT do here

- Do not add a delete endpoint for PI elements or tags
- Do not expose PI credentials in any API response or log
- Do not skip the `verify_tag_exists` check before `set_data_reference`
- Do not allow job execution without a prior `preview` step being completed
- Do not run more than one job per session simultaneously during POC