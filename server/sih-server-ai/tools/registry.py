class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(
        self,
        name,
        description,
        parameters,
        handler,
        category="other",
        state_effect="none",
        risk="safe",
    ):
        """
        Register a tool and its controller metadata.

        The metadata is used internally by the agent controller.
        It is not exposed to the LLM through schemas().
        """

        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,

            # Controller metadata
            "category": category,
            "state_effect": state_effect,
            "risk": risk,
        }

    def get(self, name):
        """Return a registered tool by name."""
        return self.tools.get(name)

    def schemas(self):
        """
        Return tool definitions in Ollama/OpenAI-compatible format.

        Only information required by the LLM is exposed here.
        Controller metadata remains internal.
        """

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in self.tools.values()
        ]

    def execute(self, name, arguments):
        """
        Execute a registered tool.
        """

        tool = self.get(name)

        if tool is None:
            raise ValueError(f"Unknown tool: {name}")

        return tool["handler"](**arguments)

    def metadata(self, name):
        """
        Return controller metadata for a tool.

        This is intentionally separate from schemas() so the LLM
        does not need to know about internal execution policy.
        """

        tool = self.get(name)

        if tool is None:
            raise ValueError(f"Unknown tool: {name}")

        return {
            "category": tool["category"],
            "state_effect": tool["state_effect"],
            "risk": tool["risk"],
        }
