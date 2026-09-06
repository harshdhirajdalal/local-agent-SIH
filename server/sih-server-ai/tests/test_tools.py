import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.registry import ToolRegistry
from tools.browser_state import register_tools as register_state_tools
from tools.browser_actions import register_tools as register_action_tools


registry = ToolRegistry()

register_state_tools(registry)
register_action_tools(registry)


print("\n===== AVAILABLE TOOLS =====")

for tool in registry.schemas():
    print(tool["function"]["name"])


print("\n===== FIND SEARCH =====")

result = registry.execute(
    "find_elements",
    {
        "query": "search"
    }
)

for element in result:
    print(element)


print("\n===== CLICK SEARCH BUTTON =====")

result = registry.execute(
    "click",
    {
        "element_id": "search-button"
    }
)

print(result)


print("\n===== TYPE INTO SEARCH =====")

result = registry.execute(
    "type_text",
    {
        "element_id": "search",
        "text": "ASUS TUF laptops"
    }
)

print(result)


print("\n===== SCROLL =====")

result = registry.execute(
    "scroll",
    {
        "direction": "down",
        "amount": 500
    }
)

print(result)


print("\n===== PRESS ENTER =====")

result = registry.execute(
    "press_key",
    {
        "key": "ENTER"
    }
)

print(result)


print("\n===== NAVIGATE =====")

result = registry.execute(
    "navigate",
    {
        "url": "https://example.com"
    }
)

print(result)


print("\n===== WAIT =====")

result = registry.execute(
    "wait",
    {
        "milliseconds": 1000
    }
)

print(result)


print("\n===== SENSITIVE FIELD TEST =====")

result = registry.execute(
    "type_text",
    {
        "element_id": "password",
        "text": "super-secret-password"
    }
)

print(result)
