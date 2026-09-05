# SIH Browser Agent Backend

FastAPI backend component of a multi-layer browser automation system.
It sits between the Browser Extension / local perception+privacy layer and
the server-side AI/LLM.

**Privacy contract:** this backend never accepts raw screenshots. It only
accepts screenshots that have already been sanitized/redacted locally, via
the `sanitized_screenshot` multipart field. There is no `/raw-screenshot`
endpoint and there never should be.

## Project structure

```
backend/
├── main.py
├── requirements.txt
├── api/
│   ├── health.py        # GET /health
│   ├── sessions.py       # POST /sessions, .../context, .../next-action, .../latest-action
│   └── state.py          # POST/GET .../state, .../visual-context
├── models/
│   ├── session.py
│   ├── ui.py
│   ├── page.py
│   ├── visual_context.py
│   ├── agent_context.py
│   └── action.py
├── services/
│   ├── session_service.py
│   ├── state_service.py
│   ├── visual_context_service.py
│   ├── context_service.py
│   ├── agent_service.py     # <-- swap the mock for the real AI here
│   └── action_service.py
├── storage/
│   └── memory_store.py      # <-- swap in-memory dict for a DB here later
└── uploads/
    └── sanitized_screenshots/   # local temp storage for sanitized images
```

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`. Interactive docs at
`http://127.0.0.1:8000/docs`.

## Example requests

### 1. Root / health

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

### 2. Create a session (session_id comes from the extension)

```bash
curl -X POST http://127.0.0.1:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "task": "Find a gaming laptop under 60000 INR"
      }'
```

Calling this again with the same `session_id` returns `409 Conflict`
instead of silently overwriting the session.

### 3. Send structured (sanitized) UI state

```bash
curl -X POST http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/state \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://example-shop.com/search",
        "title": "Example Shop",
        "elements": [
          {
            "id": "search_box",
            "type": "textbox",
            "text": "",
            "label": "Search products",
            "sensitive": false,
            "bbox": {"x": 100, "y": 50, "width": 400, "height": 40}
          },
          {
            "id": "search_button",
            "type": "button",
            "text": "Search",
            "label": "Search",
            "sensitive": false
          }
        ]
      }'
```

### 4. Upload a sanitized screenshot (multipart)

```bash
curl -X POST http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/visual-context \
  -F "sanitized_screenshot=@/path/to/sanitized_screenshot.png;type=image/png"
```

The field name **must** be `sanitized_screenshot`. Only image content
types (`image/png`, `image/jpeg`, `image/jpg`, `image/webp`) are accepted,
and the backend assumes the file has already been redacted locally.

### 5. Get metadata for the latest sanitized screenshot

```bash
curl http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/visual-context
```

### 6. Get the assembled AgentContext (debugging)

```bash
curl http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/context
```

### 7. Ask for the next action

```bash
curl -X POST http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/next-action
```

With the state from step 3, the mock agent will return something like:

```json
{
  "action": "TYPE",
  "target_id": "search_box",
  "value": "Find a gaming laptop under 60000 INR"
}
```

Calling it again after the textbox "contains" the task text will instead
return a `CLICK` on `search_button`.

### 8. Get the latest action

```bash
curl http://127.0.0.1:8000/sessions/550e8400-e29b-41d4-a716-446655440000/latest-action
```

## Integration contract

### Browser Extension team

- You generate `session_id` (a UUID) and own it for the whole task.
- Call `POST /sessions` once per new task with `{session_id, task}`.
- Push structured UI state via `POST /sessions/{id}/state` whenever the
  page/DOM changes meaningfully.
- Push sanitized screenshots via `POST /sessions/{id}/visual-context`
  (multipart, field name `sanitized_screenshot`) — **never** raw screenshots.
- Call `POST /sessions/{id}/next-action` to get the next `Action` to
  execute, or poll `GET /sessions/{id}/latest-action`.
- `Action.action` is one of `CLICK`, `TYPE`, `SCROLL`, `WAIT`, `STOP`; use
  `target_id` to look up the element in the last UI state you sent.

### Local perception / privacy team

- You own redaction. By the time anything reaches this backend, it must
  already be sanitized — the backend does not redact.
- Structured UI state (`PageState`/`UIElement`) should mark sensitive
  elements via `sensitive: true` if you want the backend/agent logic to
  treat them specially in the future.
- Screenshots must be uploaded only via the `visual-context` endpoint with
  the `sanitized_screenshot` field name; there is intentionally no
  generic/raw screenshot endpoint to send to.

### Server-side AI team

- Your integration point is `agent_service.decide_next_action(context: AgentContext) -> Action`
  in `services/agent_service.py`.
- `AgentContext` gives you `session_id`, `task`, `page_state` (URL, title,
  elements), and `visual_context` (metadata + `storage_ref` path to the
  sanitized image on disk, not raw bytes embedded in the request).
- Return a single `Action`. You don't need to worry about validation —
  `action_service.py` checks it against the current UI state before it
  reaches the extension, but do return something well-formed.
- No other file needs to change to swap the mock for your real
  implementation.

## Notes on the prototype

- Storage is a single in-memory dict, centralized in `storage/memory_store.py`.
  Swap it for a real database later by changing only that file.
- Sanitized screenshots are written to `uploads/sanitized_screenshots/` on
  local disk, one file per session (each new upload replaces the last).
  Swap for object storage later by changing only `visual_context_service.py`.
- The mock agent in `agent_service.py` is a simple heuristic, not real AI —
  it exists purely so the rest of the pipeline is testable end-to-end today.
