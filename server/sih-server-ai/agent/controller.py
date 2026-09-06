import json


class AgentController:
    """
    Controls the interaction between the LLM and the tool registry.

    Responsibilities:
    - Validate tool calls
    - Execute tools
    - Record execution results
    - Track possible browser-state changes
    - Prevent infinite agent loops
    """

    def __init__(
        self,
        registry,
        max_turns=10,
        state_refresh=None,
    ):
        self.registry = registry
        self.max_turns = max_turns
        self.state_refresh = state_refresh
        self.max_observation_streak = 4

    def execute_tool_call(self, tool_call):
        """
        Execute one Ollama/OpenAI-style tool call.

        Expected format:

        {
            "id": "call_123",
            "function": {
                "name": "find_elements",
                "arguments": {
                    "query": "search box"
                }
            }
        }
        """

        function = tool_call.get("function", {})

        tool_name = function.get("name")
        arguments = function.get("arguments", {})

        if not tool_name:
            return {
                "success": False,
                "error": "Tool call is missing a function name."
            }

        # Ollama may return arguments as a JSON string.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": (
                        f"Invalid JSON arguments for tool "
                        f"'{tool_name}'."
                    )
                }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": (
                    f"Arguments for '{tool_name}' "
                    f"must be an object."
                )
            }

        # Make sure the tool exists.
        tool = self.registry.get(tool_name)

        if tool is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        try:
            result = self.registry.execute(
                tool_name,
                arguments,
            )

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "metadata": self.registry.metadata(tool_name),
            }

        except TypeError as error:
            return {
                "success": False,
                "tool": tool_name,
                "error": (
                    f"Invalid arguments for "
                    f"'{tool_name}': {error}"
                ),
            }

        except Exception as error:
            return {
                "success": False,
                "tool": tool_name,
                "error": (
                    f"Tool execution failed: {error}"
                ),
            }

    def execute_tool_calls(self, tool_calls):
        """
        Execute all tool calls returned by the model.

        Multiple tool calls are allowed in one model response.
        We do NOT force one action per model response.
        """

        results = []

        for tool_call in tool_calls:
            result = self.execute_tool_call(tool_call)
            results.append(result)

        return results

    def state_may_have_changed(self, results):
        """
        Determine whether a tool execution may have changed
        browser state.

        This is intentionally conservative for now.

        Later, individual tools can return explicit information
        such as:

            state_changed=True
            requires_refresh=True

        so the controller can make smarter decisions.
        """

        for result in results:
            if not result.get("success"):
                continue

            metadata = result.get("metadata", {})

            if metadata.get("state_effect") in {
                "may_change",
                "navigation",
                "viewport",
            }:
                return True

        return False

    def build_tool_messages(self, tool_calls, results):
        """
        Convert tool execution results into messages that can
        be appended to the Ollama conversation.
        """

        messages = []

        for tool_call, result in zip(tool_calls, results):

            function = tool_call.get("function", {})

            messages.append({
                "role": "tool",
                "tool_name": function.get("name", ""),
                "content": json.dumps(result),
            })

        return messages

    def run(self, messages, model_call):
        """
        Run the complete LLM <-> tool loop.

        model_call(messages, tools) must return an
        Ollama-style assistant message.

        Returns:

        {
            "messages": [...],
            "final_message": {...},
            "turns": int
        }
        """

        turns = 0
        observation_streak = 0

        while turns < self.max_turns:
            turns += 1

            print(
                f"\n[Controller] Requesting model "
                f"decision (turn {turns})..."
            )

            # Ask the model what to do.
            assistant_message = model_call(
                messages,
                self.registry.schemas(),
            )

            if not isinstance(assistant_message, dict):
                assistant_message = {
                    "role": "assistant",
                    "content": str(assistant_message),
                }

            # Record Qwen's response.
            messages.append({
                "role": "assistant",
                **assistant_message,
            })

            tool_calls = assistant_message.get(
                "tool_calls",
                [],
            )

            # No tool calls means the model has finished.
            if not tool_calls:

                print(
                    "[Controller] Model returned final response."
                )

                return {
                    "messages": messages,
                    "final_message": assistant_message,
                    "turns": turns,
                }

            print(
                f"[Controller] Received "
                f"{len(tool_calls)} tool call(s)."
            )

            # Execute all tool calls from this response.
            results = self.execute_tool_calls(tool_calls)

            # Print execution information.
            for tool_call, result in zip(
                tool_calls,
                results,
            ):
                tool_name = (
                    tool_call
                    .get("function", {})
                    .get("name", "unknown")
                )

                if result.get("success"):
                    print(
                        f"[Controller] {tool_name} -> OK"
                    )
                else:
                    print(
                        f"[Controller] {tool_name} -> ERROR: "
                        f"{result.get('error', 'unknown error')}"
                    )

            # Determine whether browser state may have changed.
            state_changed = self.state_may_have_changed(
                results
            )

            if state_changed:
                observation_streak = 0

                print(
                    "[Controller] Browser state changed; "
                    "requesting fresh state..."
                )

                if self.state_refresh is not None:
                    try:
                        refreshed_state = self.state_refresh()

                        messages.append({
                            "role": "system",
                            "content": (
                                "FRESH BROWSER STATE:\n"
                                + json.dumps(
                                    refreshed_state,
                                    ensure_ascii=False,
                                )
                            ),
                        })

                        print(
                            "[Controller] Fresh browser state received."
                        )

                    except Exception as error:
                        print(
                            "[Controller] State refresh failed: "
                            f"{error}"
                        )

                        messages.append({
                            "role": "system",
                            "content": (
                                "BROWSER STATE REFRESH FAILED: "
                                + str(error)
                            ),
                        })

            else:
                successful_results = [
                    result
                    for result in results
                    if result.get("success")
                ]

                observation_only = (
                    bool(successful_results)
                    and all(
                        result.get("metadata", {}).get("category")
                        in {"inspection", "perception"}
                        and result.get("metadata", {}).get("state_effect")
                        == "none"
                        for result in successful_results
                    )
                    and len(successful_results) == len(results)
                )

                if observation_only:
                    observation_streak += 1
                else:
                    observation_streak = 0

                if observation_streak >= self.max_observation_streak:
                    print(
                        "[Controller] Agent appears stuck in "
                        "repeated observation."
                    )

                    final_message = {
                        "role": "assistant",
                        "content": (
                            "Agent stopped because it repeatedly "
                            "inspected the same browser state without "
                            "making progress."
                        ),
                    }

                    messages.append(final_message)

                    return {
                        "messages": messages,
                        "final_message": final_message,
                        "turns": turns,
                        "error": "observation_loop",
                    }

            # Give tool results back to the model.
            messages.extend(
                self.build_tool_messages(
                    tool_calls,
                    results,
                )
            )

            # IMPORTANT:
            #
            # We do not automatically call get_page_info()
            # or get_visual_context() here.
            #
            # Qwen can request the information it needs.
            #
            # Later we will add browser state/version tracking
            # so the controller can intelligently refresh state
            # only when necessary.

        print(
            f"[Controller] Maximum turns reached "
            f"({self.max_turns})."
        )

        final_message = {
            "role": "assistant",
            "content": (
                "Agent stopped because the maximum "
                "number of turns was reached."
            ),
        }

        messages.append(final_message)

        return {
            "messages": messages,
            "final_message": final_message,
            "turns": turns,
            "error": "max_turns_exceeded",
        }
