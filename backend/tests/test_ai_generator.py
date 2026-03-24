"""
Tests for AIGenerator sequential tool calling behavior.

Verifies external-observable behavior: API call counts, tool execution counts,
message structure passed to the API, and return values.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers for building mock Anthropic response objects
# ---------------------------------------------------------------------------

def _text_block(text="Final answer."):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(tool_id="tool_1", name="search_course_content", input_data=None):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data or {"query": "test query"}
    return block


def _response(stop_reason="end_turn", content=None):
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content or [_text_block()]
    return resp


def _tool_use_response(tool_id="tool_1", name="search_course_content"):
    """Response where Claude requests a tool call."""
    return _response(
        stop_reason="tool_use",
        content=[_tool_use_block(tool_id=tool_id, name=name)]
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def generator():
    """AIGenerator with a mocked Anthropic client."""
    with patch("anthropic.Anthropic") as MockAnthropic:
        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen.client = MockAnthropic.return_value
        yield gen


@pytest.fixture
def tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "Search results here."
    return tm


@pytest.fixture
def tools():
    return [{"name": "search_course_content", "description": "search tool"}]


# ---------------------------------------------------------------------------
# Test 1: No tools provided — single API call, no tool execution
# ---------------------------------------------------------------------------

def test_no_tools_provided(generator):
    generator.client.messages.create.return_value = _response(content=[_text_block("Direct answer.")])

    result = generator.generate_response("What is Python?")

    assert generator.client.messages.create.call_count == 1
    assert result == "Direct answer."


# ---------------------------------------------------------------------------
# Test 2: Tools provided but Claude returns end_turn immediately (no tool use)
# ---------------------------------------------------------------------------

def test_claude_uses_no_tools(generator, tools, tool_manager):
    generator.client.messages.create.return_value = _response(content=[_text_block("Answer without search.")])

    result = generator.generate_response("What is 2+2?", tools=tools, tool_manager=tool_manager)

    # Short-circuit: assistant message appended with text-only content → return directly
    # No extra final synthesis call needed
    assert generator.client.messages.create.call_count == 1
    tool_manager.execute_tool.assert_not_called()
    assert result == "Answer without search."


# ---------------------------------------------------------------------------
# Test 3: Tool use in round 1, Claude finishes in round 2
# ---------------------------------------------------------------------------

def test_single_tool_round_then_done(generator, tools, tool_manager):
    round1 = _tool_use_response(tool_id="t1")
    round2 = _response(content=[_text_block("Answer after search.")])
    final = _response(content=[_text_block("Synthesized answer.")])

    generator.client.messages.create.side_effect = [round1, round2, final]

    result = generator.generate_response("Tell me about lesson 4.", tools=tools, tool_manager=tool_manager)

    # round 1 (tool_use), round 2 (end_turn → short-circuit), no final call needed
    assert generator.client.messages.create.call_count == 2
    tool_manager.execute_tool.assert_called_once()
    assert result == "Answer after search."


def test_single_tool_round_final_call_has_no_tools(generator, tools, tool_manager):
    """After tool rounds, _get_final_response must NOT pass tools to the API."""
    round1 = _tool_use_response(tool_id="t1")
    # Round 2: Claude requests another tool — but this exhausts MAX_TOOL_ROUNDS=2
    round2 = _tool_use_response(tool_id="t2")
    final = _response(content=[_text_block("Final synthesis.")])

    generator.client.messages.create.side_effect = [round1, round2, final]

    result = generator.generate_response("Complex query.", tools=tools, tool_manager=tool_manager)

    # 2 tool rounds + 1 final synthesis call
    assert generator.client.messages.create.call_count == 3

    # Final call must NOT contain 'tools' or 'tool_choice'
    final_call_kwargs = generator.client.messages.create.call_args_list[2].kwargs
    assert "tools" not in final_call_kwargs
    assert "tool_choice" not in final_call_kwargs
    assert result == "Final synthesis."


# ---------------------------------------------------------------------------
# Test 4: Tool use in both rounds (max rounds exhausted)
# ---------------------------------------------------------------------------

def test_two_tool_rounds_max_rounds_exhausted(generator, tools, tool_manager):
    round1 = _tool_use_response(tool_id="t1")
    round2 = _tool_use_response(tool_id="t2")
    final = _response(content=[_text_block("Synthesized from two searches.")])

    generator.client.messages.create.side_effect = [round1, round2, final]

    result = generator.generate_response(
        "Find a course covering the same topic as lesson 4 of course X.",
        tools=tools,
        tool_manager=tool_manager
    )

    assert generator.client.messages.create.call_count == 3
    assert tool_manager.execute_tool.call_count == 2
    assert result == "Synthesized from two searches."


def test_two_tool_rounds_message_structure(generator, tools, tool_manager):
    """Final synthesis call receives full 5-message history."""
    round1 = _tool_use_response(tool_id="t1")
    round2 = _tool_use_response(tool_id="t2")
    final = _response(content=[_text_block("Done.")])

    generator.client.messages.create.side_effect = [round1, round2, final]
    generator.generate_response("Query.", tools=tools, tool_manager=tool_manager)

    final_messages = generator.client.messages.create.call_args_list[2].kwargs["messages"]
    roles = [m["role"] for m in final_messages]
    # user, assistant (round1), user (tool_result1), assistant (round2), user (tool_result2)
    assert roles == ["user", "assistant", "user", "assistant", "user"]


# ---------------------------------------------------------------------------
# Test 5: Tool execution raises an exception
# ---------------------------------------------------------------------------

def test_tool_execution_exception(generator, tools, tool_manager):
    tool_manager.execute_tool.side_effect = RuntimeError("ChromaDB unavailable")

    round1 = _tool_use_response(tool_id="t1")
    final = _response(content=[_text_block("Graceful fallback.")])

    generator.client.messages.create.side_effect = [round1, final]

    result = generator.generate_response("Query.", tools=tools, tool_manager=tool_manager)

    # Loop breaks after exception; _get_final_response is still called
    assert generator.client.messages.create.call_count == 2
    assert result == "Graceful fallback."


def test_tool_execution_exception_appends_error_result(generator, tools, tool_manager):
    """Error tool_result must be in the messages sent to the final synthesis call."""
    tool_manager.execute_tool.side_effect = RuntimeError("DB error")

    round1 = _tool_use_response(tool_id="t1")
    final = _response(content=[_text_block("Done.")])

    generator.client.messages.create.side_effect = [round1, final]
    generator.generate_response("Query.", tools=tools, tool_manager=tool_manager)

    final_messages = generator.client.messages.create.call_args_list[1].kwargs["messages"]
    # Last message should be the user tool_result with is_error
    last_msg = final_messages[-1]
    assert last_msg["role"] == "user"
    assert last_msg["content"][0]["is_error"] is True


# ---------------------------------------------------------------------------
# Test 6: Conversation history is preserved in system prompt across all calls
# ---------------------------------------------------------------------------

def test_conversation_history_in_system_prompt(generator, tools, tool_manager):
    history = "User: hello\nAssistant: hi"
    round1 = _tool_use_response(tool_id="t1")
    final = _response(content=[_text_block("Answer.")])

    generator.client.messages.create.side_effect = [round1, final]

    generator.generate_response("Query.", conversation_history=history, tools=tools, tool_manager=tool_manager)

    for call_args in generator.client.messages.create.call_args_list:
        system_param = call_args.kwargs.get("system", "")
        assert history in system_param


# ---------------------------------------------------------------------------
# Test 7: Regression — SYSTEM_PROMPT no longer limits to one search
# ---------------------------------------------------------------------------

def test_system_prompt_allows_multiple_searches():
    from ai_generator import AIGenerator
    prompt = AIGenerator.SYSTEM_PROMPT.lower()
    assert "one search per query maximum" not in prompt
    assert "2 times" in prompt or "two times" in prompt or "up to 2" in prompt
