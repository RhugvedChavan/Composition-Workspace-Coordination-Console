# Composition Workspace & Coordination Console

A writing/document editor with version history and comments, paired with a
coordination console for task assignment and project-wide status tracking.

- **Backend:** FastAPI + SQLModel + SQLite + Pydantic v2
- **Frontend:** Vanilla HTML/CSS/JS single-page app (no build step), served
  directly by FastAPI as static files
- **Tests:** pytest, 25 tests covering documents, versions, comments, tasks,
  and the dashboard

## Features

**Workspace (writing side)**
- Create, edit, delete documents ("manuscripts")
- Automatic version snapshot on every content change, with restore
- Status workflow: `draft → in_review → approved → published`
- Threaded comments per document, with resolve/unresolve

**Coordination Console (dashboard side)**
- Kanban-style task board (`todo` / `in_progress` / `done`), optionally
  linked to a document
- Dashboard summary: document counts by status, task counts by status,
  overdue task count, collaborator count
- Live activity feed of everything happening across the workspace

## Project structure

```
composition-workspace/
├── app/
│   ├── main.py            # FastAPI app + static file mount
│   ├── database.py        # SQLite engine/session setup
│   ├── models.py          # SQLModel tables
│   ├── schemas.py         # Pydantic v2 request/response schemas
│   ├── crud.py            # Shared DB helpers (versioning, activity log)
│   └── routers/
│       ├── users.py
│       ├── documents.py   # documents, versions, comments
│       ├── coordination.py # tasks
│       └── dashboard.py   # summary + activity feed
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   └── test_api.py
├── requirements.txt
└── README.md
```

## Step-by-step: running it locally

### 1. Prerequisites
- Python 3.10+ installed (`python3 --version` to check)

### 2. Unzip and enter the project
```bash
unzip composition-workspace.zip
cd composition-workspace
```

### 3. Create a virtual environment
```bash
python3 -m venv venv
```

Activate it:
- **macOS / Linux:** `source venv/bin/activate`
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (cmd):** `venv\Scripts\activate.bat`

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the server
```bash
uvicorn app.main:app --reload --port 8000
```

The `--reload` flag auto-restarts the server on code changes; drop it for
production-like runs.

### 6. Open the app
- App UI: **http://127.0.0.1:8000/**
- Interactive API docs (Swagger): **http://127.0.0.1:8000/docs**
- Alternative API docs (ReDoc): **http://127.0.0.1:8000/redoc**

A SQLite file `composition_workspace.db` is created automatically in the
project root on first run — no separate database setup needed.

### 7. Run the tests
```bash
pytest tests/ -v
```
All 25 tests should pass.

## Using the app

1. On first load, a default "You" user is created automatically (stored in
   your browser via `localStorage`) and used as the author/assignee for
   anything you create.
2. Click **+ New** in the Workspace tab to start a manuscript. Edit the
   title/content, pick a status, and click **Save** — this snapshots a new
   version automatically whenever content changes.
3. Use the **Version history** panel to restore any prior version.
4. Add **Comments** under a document for collaborator notes; resolve them
   once addressed.
5. Switch to the **Console** tab to see the dashboard stats, manage tasks on
   the kanban board (drag isn't wired up — use the status dropdown on each
   card), and watch the activity feed update in real time.

## Resetting the database

To start fresh, stop the server and delete the SQLite file:
```bash
rm composition_workspace.db
```
It will be recreated empty the next time you start the server.

## Notes / possible extensions

- Currently single-tenant with a locally-stored "current user" — add real
  auth (e.g. OAuth2 + JWT) if you need multiple real accounts.
- The dashboard polls on tab switch; wire up WebSockets or SSE for live
  push updates if multiple people use it concurrently.
- Swap SQLite for Postgres by changing `DATABASE_URL` in `app/database.py`
  if you outgrow a single file.
