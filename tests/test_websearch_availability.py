"""Test WebSearch tool availability in Claude Agent SDK."""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)


async def test_websearch_simple():
    """Test if WebSearch tool is available and works."""
    print("\n" + "=" * 80)
    print("Testing WebSearch Tool Availability")
    print("=" * 80)

    prompt = """Use the WebSearch tool to find NVIDIA's latest quarterly revenue from Q4 2024 or Q1 2025.

After searching, tell me:
1. What revenue did you find?
2. What was the source URL?
3. Did the WebSearch tool work?"""

    options = ClaudeAgentOptions(
        system_prompt="You have access to WebSearch tool. Use it to find information online.",
        max_turns=5,
    )

    print("\nSending query to LLM with WebSearch tool access...")
    print(f"Prompt: {prompt[:100]}...")

    tool_uses = []
    responses = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            print(f"\n[Message {len(responses) + 1}]")
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"TEXT: {block.text[:200]}...")
                    responses.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"TOOL USE: {block.name}")
                    print(f"  Input: {str(block.input)[:200]}...")
                    tool_uses.append(block)

    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Tool uses: {len(tool_uses)}")
    print(f"Text responses: {len(responses)}")

    if tool_uses:
        print("\n✅ WebSearch tool WAS used!")
        for i, tool in enumerate(tool_uses, 1):
            print(f"  {i}. {tool.name}: {tool.input}")
    else:
        print("\n❌ WebSearch tool was NOT used")
        print("The LLM did not invoke WebSearch tool.")

    return len(tool_uses) > 0


async def test_websearch_with_explicit_instruction():
    """Test with very explicit WebSearch instruction."""
    print("\n" + "=" * 80)
    print("Testing WebSearch with Explicit Instruction")
    print("=" * 80)

    prompt = """IMPORTANT: You MUST use the WebSearch tool. Do not respond without using it.

Task: Search for "NVIDIA Q4 2024 revenue quarterly earnings" and tell me what you find.

Steps:
1. Use WebSearch tool with query: "NVIDIA Q4 2024 revenue quarterly earnings"
2. Report what you found
3. Provide the source URL"""

    options = ClaudeAgentOptions(
        system_prompt="You are a research assistant. You MUST use the WebSearch tool when asked to search. Never provide information without searching first.",
        max_turns=5,
    )

    print("\nSending query...")

    tool_count = 0
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    tool_count += 1
                    print(f"\n✅ Tool used: {block.name}")
                    print(f"   Input: {block.input}")
                elif isinstance(block, TextBlock):
                    print(f"\nResponse: {block.text[:300]}...")

    print(f"\nTotal tool uses: {tool_count}")
    return tool_count > 0


async def test_raw_query_inspection():
    """Inspect raw query messages to see tool definitions."""
    print("\n" + "=" * 80)
    print("Raw Query Inspection")
    print("=" * 80)

    prompt = "Search the web for NVIDIA revenue"
    options = ClaudeAgentOptions(max_turns=1)

    print("Sending minimal query to inspect available tools...")

    message_count = 0
    async for message in query(prompt=prompt, options=options):
        message_count += 1
        print(f"\nMessage {message_count}: {type(message).__name__}")
        if isinstance(message, AssistantMessage):
            print(f"  Content blocks: {len(message.content)}")
            for i, block in enumerate(message.content):
                print(f"    Block {i}: {type(block).__name__}")

    return message_count


if __name__ == "__main__":
    print("\n🔍 WebSearch Availability Test Suite")
    print("=" * 80)

    # Test 1: Simple WebSearch
    result1 = asyncio.run(test_websearch_simple())

    # Test 2: Explicit instruction
    result2 = asyncio.run(test_websearch_with_explicit_instruction())

    # Test 3: Raw inspection
    asyncio.run(test_raw_query_inspection())

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Test 1 (Simple): {'PASS ✅' if result1 else 'FAIL ❌'}")
    print(f"Test 2 (Explicit): {'PASS ✅' if result2 else 'FAIL ❌'}")

    if result1 or result2:
        print("\n✅ WebSearch IS available - implementation bug in deep_research.py")
    else:
        print("\n❌ WebSearch NOT available - need alternative approach")
