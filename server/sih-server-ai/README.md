# SIH26171 — Server AI

Server-side AI and browser-agent controller for **SIH26171: On-device Visual Perception for Light-weight Browser Agents**.

This project is the reasoning/orchestration component of the complete privacy-preserving browser agent. The browser extension performs local browser-state extraction, visual perception, and privacy filtering. This server receives sanitized browser state, reasons over it with a vision-language model, calls tools, and sends structured browser actions back to the extension.

---

## 1. Project Goal

SIH26171 requires a browser agent capable of using visual context while keeping sensitive screen information local.

The intended split is:

```text
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER CLIENT                       │
│                                                             │
│  DOM extraction                                             │
│  Screenshot capture                                         │
│  Local visual perception                                    │
│  OCR                                                       │
│  Sensitive-data detection                                  │
│  Screenshot redaction                                      │
│  Browser action execution                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    SANITIZED STATE
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       SERVER AI                             │
│                                                             │
│  Session management                                         │
│  Browser state                                              │
│  Agent controller                                           │
│  Qwen3-VL                                                  │
│  Tool calling                                               │
│  Web search                                                 │
│  URL extraction                                             │
│  Browser action generation                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                     BROWSER ACTION
                           │
                           ▼
                    Browser Extension
```

The server should know **what needs to happen**.

The extension should know **how to manipulate the browser**.

---

# 2. High-Level Architecture

The planned complete system is:

```text
                         USER
                           │
                           ▼
                  Firefox / Chrome
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
        DOM Extraction             Screenshot
             │                           │
             │                    Local Privacy
             │                       Filter
             │                           │
             │                    Local Vision
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                    Sanitized State
                           │
                           │ WebSocket
                           ▼
                  ┌─────────────────┐
                  │   FastAPI       │
                  │     Server      │
                  └────────┬────────┘
                           │
                    Browser Session
                           │
                           ▼
                  ┌─────────────────┐
                  │ Agent Controller│
                  └────────┬────────┘
                           │
                           ▼
                       Qwen3-VL
                           │
                           ▼
                     Tool Calls
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
         Browser        Browser        Web
         Actions         State         Tools
             │
             ▼
        Browser Extension
             │
             ▼
        Updated Browser
             │
             └──────────────► Fresh State
```

---

# 3. Current Repository Structure

```text
sih-server-ai/
│
├── main.py
├── config.py
├── server.py
├── requirements.txt
├── README.md
│
├── agent/
│   ├── __init__.py
│   └── controller.py
│
├── tools/
│   ├── __init__.py
│   ├── registry.py
│   ├── browser_state.py
│   ├── browser_actions.py
│   └── web.py
│
├── state/
│   └── demo/
│
├── test_data/
│   ├── website/
│   │   └── index.html
│   │
│   └── browser_state/
│       ├── dom.json
│       └── visual.json
│
└── tests/
    ├── test_tools.py
    └── test_controller.py
```

Some files are currently development scaffolding and will become more important as the real browser transport is connected.

---

# 4. File-by-File Description

## `main.py`

Current development entry point.

Responsibilities:

- Configure Ollama
- Select the Qwen model
- Initialize the tool registry
- Register all tools
- Build initial browser context
- Send requests to Ollama
- Run the agent controller
- Display model/agent timing information
- Provide a command-line development interface

The default model is:

```text
qwen3-vl:2b-instruct-q4_K_M
```

The model can be changed without editing the source:

```bash
MODEL=qwen3-vl:4b-instruct-q4_K_M python main.py
```

This is particularly useful for benchmarking different models.

---

## `config.py`

Configuration module.

Intended responsibilities include centralizing:

- Ollama URL
- Model name
- Maximum agent turns
- Server host/port
- WebSocket configuration
- Timeouts
- Session configuration
- Development/production settings

Some configuration is currently read directly by `main.py`; this can be consolidated here during future refactoring.

---

## `server.py`

Reserved/under-development server entry point.

The eventual production server should live here rather than relying on the CLI-oriented `main.py`.

Planned responsibilities:

- FastAPI application
- HTTP endpoints
- WebSocket endpoint
- Browser session management
- Connection lifecycle
- Request routing
- Health checks
- Integration with the agent controller

---

# 5. `agent/`

The agent reasoning layer.

## `agent/__init__.py`

Package initializer.

No major application logic is expected here.

---

## `agent/controller.py`

Core agent loop.

The controller sits between the model and the tool registry.

Conceptually:

```text
             Qwen3-VL
                 │
                 │ tool call
                 ▼
        ┌─────────────────┐
        │ AgentController  │
        └────────┬────────┘
                 │
                 ▼
           ToolRegistry
                 │
                 ▼
             Tool result
                 │
                 ▼
             Qwen3-VL
```

Responsibilities:

1. Request a model decision.
2. Detect tool calls.
3. Validate tool names.
4. Parse tool arguments.
5. Reject malformed arguments.
6. Execute tools.
7. Return tool results to the model.
8. Continue until the model produces a final answer.
9. Stop after the configured maximum number of turns.

The controller supports multiple tool calls in a model response.

It intentionally does not force exactly one action per model response.

---

# 6. `tools/`

The tool layer.

All capabilities available to the model are registered here.

---

## `tools/__init__.py`

Package initializer.

---

## `tools/registry.py`

Central tool registry.

Each registered tool contains:

```text
name
description
parameters
handler
category
state_effect
risk
```

Example conceptual representation:

```text
Tool
├── name
├── description
├── parameters
├── handler
├── category
├── state_effect
└── risk
```

The model receives:

- name
- description
- parameter schema

Internal metadata is not exposed to the model.

This lets the controller make implementation decisions about tools without polluting the model context.

### Tool metadata

`category` describes the type of capability.

Examples:

```text
browser_action
inspection
navigation
web
timing
```

`state_effect` describes whether a tool can change browser state.

Examples:

```text
none
may_change
navigation
viewport
```

`risk` is an internal safety classification.

Examples:

```text
safe
low
medium
```

---

# 7. Browser State Tools

Implemented in:

```text
tools/browser_state.py
```

These tools provide the model with information about the current browser.

---

## `get_page_info`

Returns page-level information such as:

```json
{
    "url": "https://example.com",
    "title": "Example"
}
```

Future versions should obtain this from the active browser session rather than demo JSON.

---

## `find_elements`

Searches the known DOM for relevant elements.

Example:

```text
find_elements("search box")
```

The current implementation supports semantic queries such as:

```text
search box
search field
input field
text field
input
dropdown
menu
```

It can also match:

- element ID
- type
- label
- placeholder
- visible text

The goal is to let the model identify elements without inventing IDs.

---

## `get_element`

Returns information about one known element.

The server should return structural information such as:

- ID
- role/type
- label
- bounding box
- visibility
- interactivity

It must not return sensitive field values.

---

## `get_interactive_elements`

Returns a compact list of visible, interactive DOM elements.

This is particularly useful for initial model context.

It reduces the need for the model to spend an additional inference cycle discovering basic page structure.

---

## `get_visual_context`

Provides visual-perception information.

The eventual production implementation will integrate the local vision pipeline.

Expected information may include:

```text
DOM elements
+
visual elements
+
OCR information
+
bounding boxes
+
screenshot metadata
```

The screenshot itself must already be sanitized before transmission.

---

# 8. Browser Action Tools

Implemented in:

```text
tools/browser_actions.py
```

Current actions:

```text
click
type_text
scroll
press_key
navigate
wait
```

---

## `click`

Preferred representation:

```json
{
    "element_id": "search-button"
}
```

DOM IDs are preferred over coordinates.

The extension ultimately performs the actual click.

---

## `type_text`

Example:

```json
{
    "element_id": "search",
    "text": "ASUS TUF Gaming laptop"
}
```

Sensitive fields must never be targeted.

The server should never intentionally request:

```text
type_text(password, ...)
```

The extension should independently enforce the same privacy restriction as a second layer of defense.

---

## `scroll`

Example:

```json
{
    "direction": "down",
    "amount": 600
}
```

---

## `press_key`

Example:

```json
{
    "key": "ENTER"
}
```

---

## `navigate`

Example:

```json
{
    "url": "https://example.com"
}
```

Navigation is classified as a state-changing operation.

---

## `wait`

Example:

```json
{
    "milliseconds": 1000
}
```

Useful when the browser needs time to load or update before new state is requested.

---

# 9. Web Tools

Implemented in:

```text
tools/web.py
```

Current tools:

```text
web_search
fetch_url
```

The intended implementation uses the `ddgs` package.

---

## `web_search`

Example:

```json
{
    "query": "best gaming laptops under 80000 INR"
}
```

Returns compact search results:

```text
title
url
snippet
```

The tool should remain compact because search results can otherwise consume a large amount of model context.

---

## `fetch_url`

Retrieves readable text from a URL.

Large pages are truncated to prevent excessive context sizes.

The server should return:

```text
url
content
```

rather than an entire raw HTML document whenever possible.

---

# 10. Demo Browser State

The repository currently contains development browser state:

```text
test_data/browser_state/
├── dom.json
└── visual.json
```

The demo state represents a fake shopping website.

It contains examples such as:

```text
search
search-button
cart
login
email
password
```

It also contains example products such as:

```text
ASUS TUF Gaming A15
Lenovo Legion 5
HP Victus 15
```

The demo state exists so the server AI can be developed before the real browser extension transport is complete.

It is not intended to be the production browser-state source.

---

# 11. Demo Website

Located at:

```text
test_data/website/index.html
```

This is a local fake website used for testing agent behavior.

It provides:

- Search field
- Search button
- Product cards
- Cart UI
- Login UI
- Sensitive fields

It allows the server-side agent to be tested without requiring a live browser connection.

---

# 12. Qwen3-VL / Ollama

The current model backend is Ollama.

Default endpoint:

```text
http://localhost:11434/api/chat
```

Default model:

```text
qwen3-vl:2b-instruct-q4_K_M
```

The model is configurable.

### Qwen3-VL 2B

```bash
MODEL=qwen3-vl:2b-instruct-q4_K_M python main.py
```

### Qwen3-VL 4B

```bash
MODEL=qwen3-vl:4b-instruct-q4_K_M python main.py
```

The same code can therefore be used to compare different model sizes.

---

# 13. Model Input

The model can receive:

```text
System instructions
+
User request
+
Current browser state
+
DOM information
+
Visual information
+
Tool results
```

A typical initial context looks conceptually like:

```text
CURRENT BROWSER STATE:

Page:
    URL: ...
    Title: ...

Interactive elements:
    search
    search-button
    cart
    ...
```

The model can then request additional information through tools.

---

# 14. Tool-Calling Agent Loop

The intended loop is:

```text
User request
     │
     ▼
Qwen3-VL
     │
     ├── final answer ──────────────► User
     │
     └── tool calls
             │
             ▼
        Tool Registry
             │
             ▼
        Tool execution
             │
             ▼
        Tool results
             │
             ▼
          Qwen3-VL
```

Example:

```text
User:
"Search for ASUS TUF laptops"
```

Possible sequence:

```text
Qwen
  ↓
find_elements("search box")
  ↓
Tool result
  ↓
Qwen
  ↓
type_text("search", "ASUS TUF laptops")
  ↓
press_key("ENTER")
  ↓
Browser changes
  ↓
Fresh browser state
  ↓
Qwen
  ↓
Final response
```

The exact number of inference cycles should be minimized.

---

# 15. Why the Agent Does Not Use One Action Per Response

A simplistic browser agent might do:

```text
Qwen
 ↓
one action
 ↓
Qwen
 ↓
one action
 ↓
Qwen
 ↓
one action
```

This can become extremely expensive when model inference takes several seconds per call.

This project therefore supports multiple tool calls where appropriate.

For example, independent observations can potentially be requested together:

```text
get_page_info
find_elements
get_visual_context
```

However, actions that change browser state can invalidate previous state.

Example:

```text
click
  ↓
page changes
  ↓
old DOM becomes stale
  ↓
fresh state required
```

The future controller should therefore become state-aware rather than blindly executing either:

```text
one tool only
```

or:

```text
everything at once
```

The goal is intelligent batching.

---

# 16. Timing and Performance Measurement

`main.py` includes timing instrumentation using:

```python
time.perf_counter()
```

The timer measures the wall-clock time of each Ollama request.

Example output:

```text
------------------------------------------------------------
TIMING SUMMARY
------------------------------------------------------------
Total agent time: 92.473 s
Model turns: 2
Total Qwen time: 92.472 s
Average Qwen time/cycle: 46.236 s
Fastest Qwen cycle: 14.189 s
Slowest Qwen cycle: 78.283 s

Qwen cycle 1: 78.283 s
Qwen cycle 2: 14.189 s
------------------------------------------------------------
```

This allows real server-machine measurements.

---

## Cold vs Warm Model Performance

The first model request can be much slower because Ollama may need to load the model into memory.

Therefore benchmarks should include several runs:

```text
Run 1 → cold start
Run 2 → warm
Run 3 → warm
Run 4 → warm
Run 5 → warm
```

For model comparisons, the warm average is generally more useful.

Example benchmark table:

```text
                    Qwen3-VL 2B       Qwen3-VL 4B
Cold start             ...               ...
Warm run 1             ...               ...
Warm run 2             ...               ...
Warm run 3             ...               ...
Warm run 4             ...               ...
Warm average           ...               ...
```

The benchmark should use:

- Same machine
- Same model quantization
- Same prompt
- Same browser state
- Same tool schemas
- Same number of agent turns

This makes the comparison meaningful.

---

# 17. What the Timing Measures

The Qwen timer surrounds the HTTP request to Ollama.

Therefore:

```text
Python
  │
  ▼
HTTP request
  │
  ▼
Ollama
  │
  ├── model loading if required
  ├── prompt processing
  ├── inference
  └── response generation
  │
  ▼
HTTP response
  │
  ▼
Python
```

The reported value is therefore **wall-clock model request latency**, not merely raw token-generation time.

This is useful for the SIH prototype because it represents the practical delay experienced by the agent.

---

# 18. Browser ↔ Server Protocol

The production extension/server connection is intended to use WebSocket.

The extension connects to the server.

The server does not create a client connection back to the extension.

---

## Server → Extension

Example:

```json
{
    "type": "browser_action",
    "session_id": "SESSION_UUID",
    "request_id": "REQUEST_UUID",
    "action": "click",
    "parameters": {
        "element_id": "search"
    }
}
```

Supported actions:

```text
click
type_text
press_key
scroll
navigate
wait
```

---

## Extension → Server

Successful action:

```json
{
    "type": "action_result",
    "session_id": "SESSION_UUID",
    "request_id": "REQUEST_UUID",
    "success": true,
    "action": "click",
    "state_changed": true
}
```

Failed action:

```json
{
    "type": "action_result",
    "session_id": "SESSION_UUID",
    "request_id": "REQUEST_UUID",
    "success": false,
    "action": "click",
    "error": "Element no longer exists."
}
```

`request_id` correlates commands with their results.

`session_id` isolates one browser session from another.

---

# 19. Browser State Protocol

The extension sends sanitized state to the server.

Example:

```json
{
    "type": "browser_state",
    "session_id": "SESSION_UUID",

    "page": {
        "url": "https://example.com",
        "title": "Example"
    },

    "viewport": {
        "width": 1904,
        "height": 948,
        "dpr": 1
    },

    "dom": {
        "elements": []
    },

    "visual": {
        "elements": []
    },

    "screenshot": "<SANITIZED_SCREENSHOT>"
}
```

The screenshot must be sanitized before transmission.

---

# 20. Privacy Boundary

Privacy filtering belongs on the client.

The intended pipeline is:

```text
Raw Browser
     │
     ├── DOM
     │
     └── Screenshot
             │
             ▼
      Local privacy analysis
             │
             ▼
      Sensitive regions
             │
             ▼
          Redaction
             │
             ▼
      Sanitized screenshot
             │
             ▼
          Server AI
```

Sensitive values must not be sent to the server.

Examples include:

- Passwords
- Authentication secrets
- Credit-card numbers
- CVV
- Personal information
- Other locally detected sensitive information

The server should primarily work with:

```text
element IDs
roles
labels
bounding boxes
page structure
visual information
sanitized screenshots
```

---

# 21. Defense in Depth

Privacy enforcement should exist on both sides.

### Client

The extension:

- Detects sensitive fields
- Redacts sensitive screenshot regions
- Refuses prohibited browser operations

### Server

The server:

- Does not request sensitive field values
- Does not return sensitive values to the model
- Refuses sensitive targets where possible

This means a failure in one layer should not automatically expose private information.

---

# 22. Session Architecture

The eventual server must support multiple browser clients.

Each browser should have its own:

```text
session_id
browser connection
browser state
conversation history
pending requests
request IDs
agent/controller state
```

Conceptually:

```text
                    FastAPI
                       │
              ┌────────┼────────┐
              │        │        │
              ▼        ▼        ▼
           Session A Session B Session C
              │        │        │
              ▼        ▼        ▼
           Browser  Browser  Browser
              A        B        C
```

One user's browser state must never be accidentally used for another user's session.

---

# 23. Planned Session Manager

A future session manager should handle:

- WebSocket connections
- Session creation
- Session lookup
- Session cleanup
- Browser-state storage
- Pending action queues
- Request correlation
- Per-session agent controllers
- Connection failures
- Reconnection

A session should be destroyed or expired when its browser disconnects and no longer needs to be retained.

---

# 24. Planned FastAPI Server

The production server should eventually expose something similar to:

```text
GET  /health
POST /session
GET  /session/{session_id}
WS   /ws/browser/{session_id}
```

The exact API can change during integration.

The important architectural rule is:

```text
Extension
    │
    │ WebSocket
    ▼
FastAPI
    │
    ▼
Session Manager
    │
    ▼
Agent Controller
    │
    ▼
Qwen3-VL
```

---

# 25. Current Features

## Implemented

- Tool registry
- Tool schemas
- Browser state tools
- Semantic element search
- Interactive-element extraction
- Browser action abstractions
- Sensitive-target protection
- Web search abstraction
- URL extraction abstraction
- Ollama integration
- Qwen3-VL integration
- Tool calling
- Agent controller
- Multiple tool calls per model response
- Unknown-tool rejection
- Invalid JSON handling
- Initial browser context
- Demo browser state
- Demo website
- Model selection through environment variable
- Qwen request timing
- Agent timing summary
- Development CLI
- Basic controller/tool tests

---

# 26. Features Currently Under Development

- Real browser WebSocket transport
- FastAPI application
- Browser session manager
- Real-time browser state
- Real action dispatch
- Action-result handling
- State refresh after browser changes
- Robust retry handling
- Timeout handling
- Connection failure handling
- Real visual-context integration
- Multi-session concurrency
- End-to-end browser-agent execution

---

# 27. Future Features

The following features are planned or possible future improvements.

## Browser Integration

- Real Firefox extension connection
- Real Chrome extension connection
- WebSocket session management
- Browser reconnection
- Tab management
- Active-tab tracking
- Navigation history
- Better browser-state synchronization

---

## Agent Improvements

- State-aware planning
- Intelligent tool batching
- Reduced redundant model calls
- Action dependency analysis
- Automatic state refresh
- Better error recovery
- Retry policies
- Loop detection
- Maximum task duration
- Task cancellation
- Agent memory/history

---

## Vision Integration

Integration with the local visual-perception pipeline:

```text
DOM
+
YOLOv9-E / OmniParser
+
OCR
+
Privacy redaction
+
Screenshot
```

The server should consume the resulting sanitized visual context rather than performing the expensive visual perception itself.

---

## Web Capabilities

Possible future tools:

```text
web_search
fetch_url
open_result
extract_text
```

Additional search providers may be added later.

---

## Browser Tools

Possible future tools:

```text
switch_tab
go_back
go_forward
get_tabs
focus_element
select_option
hover
drag
upload_file
download_file
```

These should only be added when required by actual tasks.

Keeping the initial tool set small reduces model-context overhead.

---

# 28. Tool Safety Model

Every tool has internal metadata describing:

```text
category
state_effect
risk
```

Example:

```text
click
category: browser_action
state_effect: may_change
risk: low
```

This metadata is currently used internally by the controller.

Future versions can use it for:

- Action batching
- Safety checks
- State refresh decisions
- Logging
- Rate limiting
- Audit trails

The model itself does not need to see all of this metadata.

---

# 29. State Change Model

Tools can be divided conceptually into:

### No state change

```text
get_page_info
find_elements
get_element
get_visual_context
web_search
fetch_url
```

### Possible browser state change

```text
click
type_text
press_key
```

### Navigation/state transition

```text
navigate
```

### Viewport change

```text
scroll
```

### Timing

```text
wait
```

This classification will eventually determine when fresh browser state is required.

---

# 30. Error Handling

The production system should handle at least:

```text
Unknown tool
Invalid arguments
Malformed JSON
Missing element
Stale element
Browser disconnected
WebSocket disconnected
Ollama unavailable
Model unavailable
Model timeout
Web search failure
URL extraction failure
Maximum agent turns exceeded
Agent loop detected
```

Errors should be returned as structured data whenever possible.

Example:

```json
{
    "success": false,
    "error": "Element no longer exists.",
    "retryable": true
}
```

This allows Qwen/controller logic to recover intelligently.

---

# 31. Scalability Considerations

LLM inference is the expensive component.

Tool execution is generally much cheaper.

Therefore the system should avoid unnecessary model calls.

Bad:

```text
Tool
 ↓
Qwen
 ↓
Tool
 ↓
Qwen
 ↓
Tool
 ↓
Qwen
```

when the actions could safely be grouped.

Better:

```text
Qwen
 ↓
Several independent tool calls
 ↓
Tool results
 ↓
Qwen only when new reasoning is required
```

For multiple users, the server should eventually support:

- Per-session queues
- Concurrent sessions
- Model request scheduling
- Timeouts
- Backpressure
- Resource limits
- Session cleanup

---

# 32. Performance Goals

The SIH evaluation includes end-to-end latency and client resource utilization.

The server should therefore track:

```text
Model inference time
Tool execution time
Browser communication time
State processing time
Total agent-cycle time
Total task time
```

Future instrumentation should expose these separately.

Example:

```text
Cycle 1
├── Qwen:           4.8 s
├── Tool execution: 0.02 s
└── Cycle total:    4.9 s

Cycle 2
├── Qwen:           3.9 s
├── Tool execution: 0.03 s
└── Cycle total:    4.0 s

Total task:
    8.9 s
```

---

# 33. Development Environment

The server is developed as a separate project from the browser-extension/vision components.

The Python environment is managed with `uv`.

Typical setup:

```bash
cd ~/sih-server-ai
source .venv/bin/activate
uv pip install -r requirements.txt
```

The exact Python version can depend on the machine running the server.

---

# 34. Dependencies

Current intended dependencies include:

```text
requests
ddgs
websocket-client
```

The dependency list should remain minimal.

The server should not unnecessarily install the large local-vision stack because visual perception is intended to run on the client.

---

# 35. Running the Development Agent

Start with the default model:

```bash
cd ~/sih-server-ai
source .venv/bin/activate
python main.py
```

Run with Qwen3-VL 2B:

```bash
MODEL=qwen3-vl:2b-instruct-q4_K_M python main.py
```

Run with Qwen3-VL 4B:

```bash
MODEL=qwen3-vl:4b-instruct-q4_K_M python main.py
```

---

# 36. Testing

Current tests are development scripts.

Run:

```bash
python tests/test_tools.py
```

and:

```bash
python tests/test_controller.py
```

The tests currently verify functionality such as:

- Tool registration
- Tool execution
- Semantic element lookup
- Multiple tool calls
- Unknown-tool rejection
- Invalid JSON rejection
- State-change detection

They are currently not a full production test suite.

---

# 37. Example Development Session

Example:

```text
============================================================
SIH26171 Server AI
============================================================
Model: qwen3-vl:2b-instruct-q4_K_M
Ollama: http://localhost:11434/api/chat
Max turns: 10
============================================================

User> Find the search box
```

Possible execution:

```text
[Controller] Requesting model decision (turn 1)...
[Controller] Received 1 tool call(s).
[Controller] find_elements -> OK

[Controller] Requesting model decision (turn 2)...
[Controller] Model returned final response.
```

Timing:

```text
------------------------------------------------------------
TIMING SUMMARY
------------------------------------------------------------
Total agent time: ...
Model turns: 2
Total Qwen time: ...
Average Qwen time/cycle: ...
Fastest Qwen cycle: ...
Slowest Qwen cycle: ...
------------------------------------------------------------
```

---

# 38. Current Limitations

The current project is still a development-stage server.

Important limitations:

1. Browser state currently uses demo data.
2. Browser actions are not yet fully connected to a real browser.
3. FastAPI/WebSocket integration is still under development.
4. Session management is not complete.
5. Visual context is not yet connected to the production local vision pipeline.
6. Agent state refresh is not yet fully automatic.
7. Error recovery is still being developed.
8. The current CLI is primarily for testing the reasoning layer.
9. Model latency can be high on CPU-only machines.
10. Web search depends on external network/search availability.

---

# 39. Integration With the Browser Extension

The extension team should not copy the entire server into the extension.

Instead, both sides should implement the shared protocol.

The extension owns:

```text
DOM extraction
Screenshot capture
Privacy filtering
Local visual perception
Browser APIs
Action execution
```

The server owns:

```text
Session management
Reasoning
Qwen3-VL
Tool selection
Web tools
Action generation
```

The shared interface is:

```text
JSON messages
+
session_id
+
request_id
```

---

# 40. Recommended Shared Contract

The project should eventually maintain a separate protocol specification:

```text
sih26171-contract/
├── README.md
├── action-schema.json
├── browser-state-schema.json
├── examples/
│   ├── click.json
│   ├── type_text.json
│   ├── action_result.json
│   └── browser_state.json
├── dom-example.json
└── visual-example.json
```

This prevents the extension and server from silently implementing different message formats.

---

# 41. End-to-End Target

The final prototype should support a task such as:

```text
User:
"Find ASUS TUF laptops and open the appropriate result."
```

The intended flow:

```text
1. User submits request
          │
          ▼
2. Extension provides browser state
          │
          ▼
3. Local privacy filter sanitizes screenshot
          │
          ▼
4. Server receives sanitized state
          │
          ▼
5. Qwen3-VL reasons about the request
          │
          ▼
6. Qwen selects browser tools
          │
          ▼
7. Server sends structured action
          │
          ▼
8. Extension executes action
          │
          ▼
9. Browser changes
          │
          ▼
10. Extension sends fresh state
          │
          ▼
11. Qwen reasons again if required
          │
          ▼
12. Task completes
```

---

# 42. SIH26171 Evaluation Alignment

The architecture is intended to address the major evaluation areas.

## Visual context accuracy

Local visual perception provides structured UI information.

Potential components:

```text
OmniParser / YOLOv9-E
OCR
DOM
Screenshot
```

---

## Sensitive/PII detection

Sensitive information is detected locally.

The extension can use:

```text
DOM attributes
field metadata
OCR
visual detection
```

to identify sensitive regions.

---

## Redaction precision

Sensitive regions are redacted locally before transmission.

The server therefore receives sanitized visual context.

---

## Client resource utilization

The expensive visual pipeline is kept local but lightweight.

The architecture is designed around browser-compatible inference technologies such as:

```text
WebAssembly
WebGPU
ONNX Runtime Web
```

where appropriate.

---

## End-to-end latency

The server measures:

```text
Qwen inference
+
tool execution
+
browser communication
+
agent cycles
```

so the complete system can be profiled.

---

# 43. Design Principles

## Privacy first

Sensitive information should remain on the client whenever possible.

## DOM first

Stable DOM element IDs are preferred over coordinates.

## Vision when needed

Visual perception complements DOM information.

## Small tool set

Do not expose dozens of unnecessary tools to the model.

Large tool schemas increase prompt size and can increase inference latency.

## Intelligent batching

Independent operations should be grouped when safe.

## Fresh state when necessary

State-changing browser actions can invalidate previous information.

## Defense in depth

Both server and extension should enforce privacy restrictions.

## Session isolation

Browser state must remain isolated between users.

## Measurable performance

Every expensive operation should eventually be measurable.

---

# 44. Roadmap

## Phase 1 — Core AI

- [x] Tool registry
- [x] Browser state abstractions
- [x] Browser action abstractions
- [x] Web tools
- [x] Ollama integration
- [x] Qwen3-VL integration
- [x] Agent controller
- [x] Initial context
- [x] Timing instrumentation

## Phase 2 — Browser Connection

- [ ] FastAPI server
- [ ] WebSocket endpoint
- [ ] Browser session manager
- [ ] Extension connection
- [ ] Live browser state
- [ ] Real action dispatch
- [ ] Action results

## Phase 3 — Vision Integration

- [ ] Receive local OmniParser output
- [ ] Receive OCR output
- [ ] Receive sanitized screenshots
- [ ] Merge DOM and visual context
- [ ] Improve visual grounding

## Phase 4 — Agent Optimization

- [ ] State-aware controller
- [ ] Intelligent action batching
- [ ] Reduce redundant observations
- [ ] Retry policies
- [ ] Error recovery
- [ ] Loop detection
- [ ] Latency profiling

## Phase 5 — Multi-user Server

- [ ] Concurrent sessions
- [ ] Session queues
- [ ] Model scheduling
- [ ] Resource limits
- [ ] Connection recovery
- [ ] Session cleanup

## Phase 6 — SIH Demo

- [ ] Complete end-to-end browser task
- [ ] Privacy demonstration
- [ ] Visual perception demonstration
- [ ] Latency measurements
- [ ] Resource measurements
- [ ] Failure/recovery demonstration
- [ ] Final documentation

---

# 45. Final Architecture

The intended final separation is:

```text
╔══════════════════════════════════════════════════════════╗
║                    BROWSER CLIENT                        ║
║                                                          ║
║  DOM ───────────────┐                                    ║
║                     ├──► Local Perception                ║
║  Screenshot ────────┘        │                           ║
║                              ▼                           ║
║                       Privacy Filter                    ║
║                              │                           ║
║                              ▼                           ║
║                       Sanitized State                   ║
║                              │                           ║
╚══════════════════════════════╪═══════════════════════════╝
                               │
                               │ WebSocket
                               ▼
╔══════════════════════════════════════════════════════════╗
║                       SERVER AI                          ║
║                                                          ║
║  Browser Session                                          ║
║        │                                                 ║
║        ▼                                                 ║
║  Agent Controller                                         ║
║        │                                                 ║
║        ▼                                                 ║
║     Qwen3-VL                                             ║
║        │                                                 ║
║        ▼                                                 ║
║  Tool Registry                                            ║
║     │        │        │                                  ║
║     ▼        ▼        ▼                                  ║
║  Browser   State     Web                                  ║
║  Actions   Tools     Tools                                ║
║                                                          ║
╚══════════════════════════════╪═══════════════════════════╝
                               │
                               │ Browser action
                               ▼
                        Browser Extension
                               │
                               ▼
                         Updated State
```

The core architectural rule is:

> **Perception and privacy stay local; reasoning and planning happen on the server; browser control remains with the extension.**

This separation allows the project to combine local privacy-preserving visual perception with a more capable server-side vision-language model while keeping the browser's sensitive information under local control.
