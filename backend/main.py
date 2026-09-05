"""
FastAPI backend entrypoint.

Run with:
    uvicorn main:app --reload
"""

from fastapi import FastAPI

from api import health, sessions, state

app = FastAPI(
    title="SIH Browser Agent Backend",
    description=(
        "Backend component of a multi-layer browser automation system. "
        "Accepts sanitized structured UI state and sanitized screenshots "
        "from the local perception/privacy layer, assembles agent context, "
        "and brokers actions between the server-side AI and the Browser "
        "Extension. This service never accepts raw/original screenshots."
    ),
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(state.router)


@app.get("/")
def root():
    return {"message": "Backend running"}
