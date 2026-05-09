# CLAUDE.md — KYC Document Parser

## Get Shit Done (GSD) — Execution Mode

For **implementation**: use Edit / Write / Read / Bash / Glob / Grep directly. Do NOT spawn Superpowers subagents during execution — it is far too slow.

For **planning**: Superpowers (`superpowers:brainstorming`, `superpowers:writing-plans`) is fine and encouraged.

Rule: one tool call → one change. Read a file, edit it, move on.

---

## Recommended Skills

| Skill | When to use |
|-------|-------------|
| `claude-api` | Modifying `ocr.py`, `extract.py`, or any Anthropic SDK code |
| `security-review` | Before any PR touching crypto, auth, or PII handling |
| `simplify` | After large implementations to trim bloat |
| `superpowers:brainstorming` | Planning new features (NOT during execution) |
| `superpowers:writing-plans` | Writing implementation plans (NOT during execution) |
| `frontend-design` | Before writing any new frontend UI |

---

## Backend Architecture

```
backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, request logging middleware
│   ├── config.py        # Settings (env vars)
│   ├── database.py      # SQLAlchemy async engine
│   ├── logger.py        # Logging setup — import get_logger(__name__) everywhere
│   ├── models/
│   │   └── submission.py  # Submission, Document, DocumentInfo, AuditLog
│   ├── routes/
│   │   ├── submit.py    # POST /api/v1/submit — create submission
│   │   ├── upload.py    # POST /api/v1/upload/{ref} — upload doc + persist DocumentInfo
│   │   ├── extract.py   # POST /api/v1/extract — stateless OCR (no DB write)
│   │   ├── status.py    # GET /api/v1/status/{ref}
│   │   └── admin.py     # Admin review endpoints
│   └── services/
│       ├── ocr.py       # Anthropic Claude Haiku OCR — loads prompt from agents/
│       ├── storage.py   # Cloudflare R2 upload
│       ├── crypto.py    # Field-level encryption for PII
│       └── email.py     # Submission confirmation email
├── agents/
│   └── identity_extractor.agent.md  # OCR agent definition (YAML frontmatter + system prompt)
└── alembic/versions/    # Database migrations
```

**Database:** PostgreSQL (Supabase) via SQLAlchemy async  
**Migrations:** Alembic — run `alembic upgrade head` from `backend/`  
**Logging:** `backend/app/logger.py` — call `get_logger(__name__)` in every module. Dev = human-readable stdout; prod = JSON stdout.

---

## Agent Files

- Location: `backend/agents/`
- Format: YAML frontmatter (agent name, version, model, max_tokens) + body = system prompt verbatim
- `ocr.py` loads the agent file at import time via `_load_agent()`
- To update the OCR prompt: edit `backend/agents/identity_extractor.agent.md` and redeploy
- Future agents follow the same pattern: `identity_verifier.agent.md`, `address_checker.agent.md`, etc.

---

## Sample Images

- `sample/` at project root — use for manual OCR testing
- Test OCR locally:
  ```bash
  curl -X POST http://localhost:8000/api/v1/extract \
    -F "file=@sample/nric_front.png" | python -m json.tool
  ```
- Expected: `extraction_failed: false`, `fields` contains at least `document_number` and `full_name`
- Check backend logs for `ocr_response` line showing token counts and latency

---

## Frontend

**File:** `frontend/index.html` — single-file, all styles inline.

**Wizard flow (4 steps):**
```
Step 1: Personal Details → Step 2: Upload & Verify → Step 3: Review → Step 4: Done
```

Step 2 is combined Upload + OCR: user uploads files, clicks "Scan Documents", OCR results appear inline below the file list (no page navigation). Approve → go to Review.

**Stack:** Tailwind CSS via CDN, vanilla JS, no build step.

**Dev server:** `node serve.mjs` → `http://localhost:3000`

### Screenshot Workflow
- Always screenshot from localhost (never `file:///`)
- `node screenshot.mjs http://localhost:3000` → saves to `temporary screenshots/screenshot-N.png`
- Read the PNG with the Read tool and compare pixel-precisely
- Do at least 2 comparison rounds before declaring done

### Brand Assets
- Check `brand_assets/` before designing — use real logos/colors if present
- Never invent brand colors; derive from what's in `brand_assets/`

### Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.)
- **Shadows:** Layered, color-tinted — never flat `shadow-md`
- **Typography:** Different fonts for headings vs body. Tight tracking on large headings (`-0.03em`), generous line-height on body (`1.7`)
- **Animations:** Only `transform` and `opacity`. Never `transition-all`
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states
- **Depth:** Base → elevated → floating layer system

### Hard Rules
- Do not add features not in the reference
- Do not "improve" a reference design — match it
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color
