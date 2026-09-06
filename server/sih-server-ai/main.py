import time
import requests

from config import (
    MAX_AGENT_TURNS,
    MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)
from tools.registry import ToolRegistry
from tools.browser_state import register_tools as register_state_tools
from tools.browser_actions import register_tools as register_browser_tools
from tools.web import register_tools as register_web_tools

from agent.controller import AgentController


# ============================================================
# System prompt
# ============================================================

SYSTEM_PROMPT = """
You are a browser automation agent.

Your job is to accomplish the user's request by interacting
with the browser through the available tools.

IMPORTANT RULES:

1. The current browser state is provided to you before you
   make your first decision.

2. Prefer using the current browser page when it can accomplish
   the user's request.

3. If the current page contains an appropriate search field,
   form, button, link, or other UI for the user's request,
   interact with that UI instead of using web_search.

4. Use web_search only when:
   - the current page cannot accomplish the request, or
   - the user explicitly asks for a web search, or
   - external information is genuinely required.

5. Do not invent element IDs.
   If you need an element that is not already known, use
   find_elements.

6. Prefer DOM element IDs over visual coordinates.

7. Use get_page_info when you need information about the
   current page or URL.

8. Use get_visual_context when visual information is necessary.

9. Never expose or request values from sensitive fields.

10. Use the smallest number of tools necessary.

11. Multiple tool calls are allowed when useful and independent.

12. After an action that may change browser state, obtain fresh
    information if the next decision depends on the changed
    state.

13. When the user's task is complete, stop using tools and
    provide a concise final response.
"""


# ============================================================
# Tool registry
# ============================================================

registry = ToolRegistry()

register_state_tools(registry)
register_browser_tools(registry)
register_web_tools(registry)


# ============================================================
# Agent controller
# ============================================================

controller = AgentController(
    registry=registry,
    max_turns=MAX_AGENT_TURNS,
)


# ============================================================
# Initial browser context
# ============================================================

def build_initial_context():
    """
    Build compact browser context for the first model call.
    """

    try:

        page_info = registry.execute(
            "get_page_info",
            {},
        )

        interactive_elements = registry.execute(
            "get_interactive_elements",
            {},
        )

        return {
            "page": page_info,
            "interactive_elements": interactive_elements,
        }

    except Exception as error:

        print(
            "[Context] Failed to build browser context:",
            error,
        )

        return {
            "error": str(error),
        }


# ============================================================
# Qwen / Ollama
# ============================================================

def call_qwen(messages, tools):
    """
    Send the current conversation, tools, and optional
    screenshots to Ollama.

    Ollama accepts images through the "images" field
    inside a message.
    """

    start_time = time.perf_counter()

    # Copy messages so we don't modify the controller's
    # original conversation history.
    ollama_messages = []

    for message in messages:
        message_copy = dict(message)

        # "screenshot" is our internal field.
        # Ollama does not expect this field.
        screenshot = message_copy.pop("screenshot", None)

        if screenshot:
            message_copy["images"] = [screenshot]

        ollama_messages.append(message_copy)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": ollama_messages,
            "tools": tools,
            "stream": False,
            "think": False,
        },
        timeout=OLLAMA_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    elapsed = time.perf_counter() - start_time

    message = data.get("message")

    if not message:
        raise RuntimeError(
            "Ollama response did not contain a message."
        )

    message["_timing"] = {
        "model_wall_time_seconds": elapsed,
    }

    return message

# ============================================================
# Agent execution
# ============================================================

def run_agent(user_request):
    """
    Run the browser agent for one user request.

    Prints timing information for every model cycle and
    the overall agent execution.
    """

    agent_start = time.perf_counter()

    browser_context = build_initial_context()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": (
                "CURRENT BROWSER STATE:\n"
                + str(browser_context)
            ),
        },
        {
            "role": "user",
            "content": user_request,
        },
    ]

    print("\n" + "=" * 60)
    print("AGENT RUN")
    print("=" * 60)

    result = controller.run(
        messages=messages,
        model_call=call_qwen,
    )

    agent_elapsed = time.perf_counter() - agent_start

    print("\n" + "-" * 60)
    print("TIMING SUMMARY")
    print("-" * 60)

    print(
        f"Total agent time: "
        f"{agent_elapsed:.3f} s"
    )

    print(
        f"Model turns: "
        f"{result.get('turns', '?')}"
    )

    # Extract model timing from assistant messages.
    model_times = []

    for message in result.get("messages", []):

        if message.get("role") != "assistant":
            continue

        timing = message.get("_timing")

        if not timing:
            continue

        elapsed = timing.get(
            "model_wall_time_seconds"
        )

        if elapsed is not None:
            model_times.append(elapsed)

    if model_times:

        print(
            f"Total Qwen time: "
            f"{sum(model_times):.3f} s"
        )

        print(
            f"Average Qwen time/cycle: "
            f"{sum(model_times) / len(model_times):.3f} s"
        )

        print(
            f"Fastest Qwen cycle: "
            f"{min(model_times):.3f} s"
        )

        print(
            f"Slowest Qwen cycle: "
            f"{max(model_times):.3f} s"
        )

        print()

        for index, elapsed in enumerate(
            model_times,
            start=1,
        ):
            print(
                f"Qwen cycle {index}: "
                f"{elapsed:.3f} s"
            )

    print("-" * 60)

    return result


# ============================================================
# Command-line interface
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("SIH26171 Server AI")
    print("=" * 60)

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Ollama: {OLLAMA_URL}"
    )

    print(
        f"Max turns: {MAX_AGENT_TURNS}"
    )

    print("=" * 60)

    while True:

        try:

            user_request = input(
                "\nUser> "
            ).strip()

        except (KeyboardInterrupt, EOFError):

            print("\nExiting.")
            break

        if not user_request:
            continue

        if user_request.lower() in {
            "exit",
            "quit",
        }:

            print("Exiting.")
            break

        try:

            result = run_agent(
                user_request
            )

            final_message = result.get(
                "final_message",
                {},
            )

            content = final_message.get(
                "content",
                "",
            )

            print("\nAgent>")
            print(content)

            print(
                f"\n[Controller] Completed in "
                f"{result.get('turns', '?')} turn(s)."
            )

        except requests.RequestException as error:

            print(
                "\n[ERROR] Could not communicate "
                "with Ollama:"
            )

            print(error)

        except Exception as error:

            print("\n[ERROR]")
            print(error)
