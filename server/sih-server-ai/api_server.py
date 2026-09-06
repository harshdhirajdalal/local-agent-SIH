import base64
import json
import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import SYSTEM_PROMPT, call_qwen


app = FastAPI(
    title="SIH26171 Server AI",
    version="0.1.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health
# ============================================================

@app.get("/health")
async def health():
    return {
        "success": True,
        "service": "SIH26171 Server AI",
    }


# ============================================================
# Observe
# ============================================================

@app.post("/v1/observe")
async def observe(
    metadata: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Receive a sanitized browser observation.

    The browser extension is responsible for:
      - DOM extraction
      - PII detection
      - local screenshot redaction
      - future local OmniParser inference

    This endpoint must NEVER receive the original unsanitized
    screenshot or sensitive field values.
    """

    request_id = str(uuid.uuid4())

    try:
        # ----------------------------------------------------
        # Parse browser metadata
        # ----------------------------------------------------

        try:
            browser_state = json.loads(metadata)
        except json.JSONDecodeError as error:
            return {
                "success": False,
                "request_id": request_id,
                "error": f"Invalid metadata JSON: {error}",
            }

        if not isinstance(browser_state, dict):
            return {
                "success": False,
                "request_id": request_id,
                "error": "Metadata must contain a JSON object.",
            }

        # ----------------------------------------------------
        # Read already-sanitized screenshot
        # ----------------------------------------------------

        image_bytes = await image.read()

        if not image_bytes:
            return {
                "success": False,
                "request_id": request_id,
                "error": "Uploaded image is empty.",
            }

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        # ----------------------------------------------------
        # Extract browser state
        # ----------------------------------------------------

        user_request = browser_state.get(
            "user_request",
            "",
        )

        page = browser_state.get(
            "page",
            {},
        )

        dom = browser_state.get(
            "dom",
            {},
        )

        redaction = browser_state.get(
            "redaction",
            {},
        )

        visual = browser_state.get(
            "visual",
            {},
        )

        # ----------------------------------------------------
        # Build model context
        # ----------------------------------------------------

        context_text = f"""
LIVE BROWSER CONTEXT
====================

USER REQUEST:
{user_request}

PAGE:
{json.dumps(page, indent=2)}

DOM:
{json.dumps(dom, indent=2)}

VISUAL PERCEPTION:
{json.dumps(visual, indent=2)}

PRIVACY / REDACTION:
{json.dumps(redaction, indent=2)}

IMPORTANT PRIVACY RULES
=======================

The screenshot attached to this message has already been
sanitized locally by the browser extension.

Sensitive information has been removed or redacted before
leaving the browser.

Do NOT:
- attempt to infer hidden/redacted values
- request passwords, credentials, payment information,
  personal identification numbers, or other sensitive values
- assume that a redacted region contains readable information

Use the supplied DOM, visual perception data, and sanitized
screenshot as the current browser state.

The visual perception data may contain locally generated
bounding boxes from the browser's vision model.
"""

        # ----------------------------------------------------
        # Construct Ollama messages
        # ----------------------------------------------------

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": context_text,
                "images": [
                    image_base64,
                ],
            },
        ]

        # ----------------------------------------------------
        # Ask Qwen
        # ----------------------------------------------------

        assistant_message = call_qwen(
            messages,
            [],
        )

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "success": True,
            "request_id": request_id,
            "message": assistant_message,
        }

    except Exception as error:
        return {
            "success": False,
            "request_id": request_id,
            "error": str(error),
        }


# ============================================================
# Development entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
    )
