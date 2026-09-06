import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.registry import ToolRegistry
from tools.browser_state import register_tools as register_state_tools
from tools.browser_actions import register_tools as register_browser_tools
from tools.web import register_tools as register_web_tools

from agent.controller import AgentController


registry = ToolRegistry()

register_state_tools(registry)
register_browser_tools(registry)
register_web_tools(registry)

controller = AgentController(registry)


# --------------------------------------------------
# Test 1: normal tool call
# --------------------------------------------------

tool_call = {
    "id": "call_1",
    "function": {
        "name": "find_elements",
        "arguments": {
            "query": "search box"
        }
    }
}

result = controller.execute_tool_call(tool_call)

print("\n=== TEST 1 ===")
print(result)


# --------------------------------------------------
# Test 2: multiple tool calls
# --------------------------------------------------

tool_calls = [
    {
        "id": "call_2",
        "function": {
            "name": "find_elements",
            "arguments": {
                "query": "search box"
            }
        }
    },
    {
        "id": "call_3",
        "function": {
            "name": "get_page_info",
            "arguments": {}
        }
    }
]

results = controller.execute_tool_calls(tool_calls)

print("\n=== TEST 2 ===")

for result in results:
    print(result)


# --------------------------------------------------
# Test 3: unknown tool
# --------------------------------------------------

bad_call = {
    "id": "call_4",
    "function": {
        "name": "destroy_everything",
        "arguments": {}
    }
}

result = controller.execute_tool_call(bad_call)

print("\n=== TEST 3 ===")
print(result)


# --------------------------------------------------
# Test 4: malformed JSON arguments
# --------------------------------------------------

bad_json = {
    "id": "call_5",
    "function": {
        "name": "find_elements",
        "arguments": "{not valid json}"
    }
}

result = controller.execute_tool_call(bad_json)

print("\n=== TEST 4 ===")
print(result)


# --------------------------------------------------
# Test 5: state detection
# --------------------------------------------------

state_change_calls = [
    {
        "id": "call_6",
        "function": {
            "name": "click",
            "arguments": {
                "element_id": "search"
            }
        }
    }
]

results = controller.execute_tool_calls(state_change_calls)

print("\n=== TEST 5 ===")
print("State may have changed:",
      controller.state_may_have_changed(results))
