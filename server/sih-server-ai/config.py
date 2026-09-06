"""Central configuration for the SIH26171 server AI."""

import os


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat",
)

MODEL = os.getenv(
    "MODEL",
    "qwen3-vl:2b-instruct-q4_K_M",
)

MAX_AGENT_TURNS = int(
    os.getenv("MAX_AGENT_TURNS", "15")
)

OLLAMA_TIMEOUT = float(
    os.getenv("OLLAMA_TIMEOUT", "120")
)

OLLAMA_MAX_CONCURRENT = int(
    os.getenv("OLLAMA_MAX_CONCURRENT", "4")
)

HOST = os.getenv(
    "HOST",
    "0.0.0.0",
)

PORT = int(
    os.getenv("PORT", "8000")
)

ACTION_TIMEOUT = float(
    os.getenv("ACTION_TIMEOUT", "30")
)

LOG_TIMINGS = os.getenv(
    "LOG_TIMINGS",
    "1",
).lower() not in {"0", "false", "no"}
