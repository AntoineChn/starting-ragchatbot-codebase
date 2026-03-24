import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum number of sequential tool-use rounds per query
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- You may search up to **2 times** per query. Use a second search only if the first result was insufficient or revealed a need for a more specific follow-up.
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **Outline/syllabus/structure queries**: Use the `get_course_outline` tool; return the course title, course link (if available), and the complete numbered lesson list
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        if tools and tool_manager:
            messages = self._run_tool_rounds(messages, system_content, tools, tool_manager)

            # Short-circuit: if the last message is from the assistant with no tool_use,
            # Claude already produced a final text response — return it directly.
            last = messages[-1]
            if last["role"] == "assistant":
                content = last["content"]
                has_tool_use = any(
                    getattr(b, "type", None) == "tool_use" for b in content
                ) if not isinstance(content, str) else False
                if not has_tool_use:
                    text_block = next(
                        (b for b in content if getattr(b, "type", None) == "text"),
                        None
                    )
                    if text_block:
                        return text_block.text

        return self._get_final_response(messages, system_content)

    def _run_tool_rounds(self, messages: List, system: str, tools: List, tool_manager) -> List:
        """
        Run up to MAX_TOOL_ROUNDS of tool-use API calls, accumulating messages.

        Each round calls the API with tools enabled. If Claude requests tool use,
        the tools are executed and results appended before the next round.
        Terminates early if Claude stops requesting tools or if tool execution fails.

        Args:
            messages: Initial message list (user query)
            system: System prompt string
            tools: Tool definitions to pass to the API
            tool_manager: Manager to execute tools

        Returns:
            Accumulated messages list after all rounds
        """
        for _ in range(self.MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                **self.base_params,
                system=system,
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )

            # Append assistant response to history
            messages.append({"role": "assistant", "content": response.content})

            # Termination (b): Claude finished without requesting a tool
            if response.stop_reason != "tool_use":
                break

            # Execute all tool calls; collect results
            tool_results = []
            try:
                for block in response.content:
                    if block.type == "tool_use":
                        result = tool_manager.execute_tool(block.name, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
            except Exception as e:
                # Termination (c): tool execution raised an unexpected exception
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Tool execution error: {e}",
                    "is_error": True
                })
                messages.append({"role": "user", "content": tool_results})
                break

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        return messages

    def _get_final_response(self, messages: List, system: str) -> str:
        """
        Make a single synthesis API call without tools.

        Called after all tool rounds are complete to produce a clean text response.

        Args:
            messages: Full accumulated conversation including tool results
            system: System prompt string

        Returns:
            Final response text
        """
        response = self.client.messages.create(
            **self.base_params,
            system=system,
            messages=messages
        )
        return response.content[0].text
