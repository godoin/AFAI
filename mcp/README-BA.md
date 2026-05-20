# PI Tag List Intake — BA Quick Start Guide

This guide is for Business Analysts. No technical setup required on your end.
The dev team has already configured everything. You just need to follow these steps.

---

## What this does

You provide a client tag list (Excel or CSV), and the system will:

1. Validate all tag names against naming conventions
2. Check which tags already exist in PI System
3. Show you a pre-action report for your review
4. **Wait for your approval before writing anything to PI**
5. Create the approved tags and link them to the AF hierarchy
6. Deliver a final report showing what was created, skipped, or failed

Nothing is written to PI System without your explicit confirmation.

---

## How to start a session

Open Claude Desktop and type exactly this:

> **"Start a new PI session"**

That's it. Claude will handle the rest — it will confirm the PI connection
is live and ask you what you want to provide.

---

## What to have ready

- Your client tag list as an **Excel (.xlsx) or CSV (.csv)** file
- The file must have these columns:
  - `Plant`
  - `Unit/System`
  - `Source Tagname`
  - `Source Tag`
  - `Proposed New Tagname`

Optional but helpful:
  - `Description`
  - `eng_units`
  - `Canary Tag Path`

---

## What happens step by step

### Step 1 — You start the session
Type: **"Start a new PI session"**
Claude confirms PI is reachable.

### Step 2 — You upload the tag list
Claude asks for your file. Upload your Excel or CSV.
Claude parses and validates it — no PI writes yet.

### Step 3 — You review the pre-action report
Claude delivers an Excel report showing:
- Tags that will be **created**
- Tags that **already exist** (will be skipped)
- Tags with **naming violations** (will be skipped)
- Tags whose **AF element is missing** (will be skipped)

There is a **BA Notes** column for you to annotate.

### Step 4 — You confirm or request changes
If the report looks good, reply:
> **"Confirmed, proceed"**

If you want changes, tell Claude what to fix and it will re-run.

### Step 5 — Tags are created
Claude creates one tag at a time and tells you the result of each.
If anything fails, Claude stops and asks you how to proceed.

### Step 6 — You receive the final report
Claude delivers a final Excel report showing the outcome of every tag.
Keep this for your records.

---

## Key rules Claude will always follow

- **Nothing is written to PI without your explicit "confirmed"**
- Claude will never auto-correct a naming violation — it will show you and ask
- If a tag already exists, it is skipped — never overwritten
- If any PI call fails, Claude stops and surfaces the error to you
- Claude never retries a failed write automatically

---

## If something goes wrong

Tell Claude exactly what you see. It will surface the error and ask
how you want to proceed. You can always say:

> **"Stop the session"**

And Claude will halt without making any further changes.

---

## Trigger phrases (for reference)

| What you want to do | What to say |
|---|---|
| Start a new session | `Start a new PI session` |
| Confirm the pre-action report | `Confirmed, proceed` |
| Request changes to the report | `Please revise — [describe the change]` |
| Stop everything | `Stop the session` |
| Check session status | `What is the current status?` |

---

*For technical issues, contact the dev team.*
*Do not attempt to restart the PI server or modify config files.*