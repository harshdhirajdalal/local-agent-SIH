import base64
import json
import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import (
    SYSTEM_PROMPT,
    call_qwen,
)


app = FastAPI(
    title="SIH26171 Server AI"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "success": True,
        "service": "SIH26171 Server AI"
    }


@app.post("/v1/observe")
async def observe(
    metadata: str = Form(...),
    image: UploadFile = File(...)
):
    try:

        browser_state = json.loads(
            metadata
        )

        image_bytes =
            await image.read()

        image_base64 =
            base64.b64encode(
                image_bytes
            ).decode("utf-8")

        user_request =
            browser_state.get(
                "user_request",
                ""
            )

        page =
            browser_state.get(
                "page",
                {}
            )

        dom =
            browser_state.get(
                "dom",
                {}
            )

        redaction =
            browser_state.get(
                "redaction",
                {}
            )

        context_text = f"""
LIVE BROWSER CONTEXT
====================

USER REQUEST:
{user_request}

PAGE:
{json.dumps(page, indent=2)}

DOM:
{json.dumps(dom, indent=2)}

PRIVACY / REDACTION:
{json.dumps(redaction, indent=2)}

IMPORTANT:
The screenshot attached to this message has already
been sanitized locally by the browser extension.

Do NOT assume that hidden or redacted values are available.

Use the supplied DOM and screenshot as the current browser
state.
"""

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": context_text,
                "images": [
                    image_base64
                ]
            }
        ]

        assistant_message =
            call_qwen(
                messages,
                []
            )

        return {
            "success": True,
            "request_id": str(
                uuid.uuid4()
            ),
            "message":
                assistant_message
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }
