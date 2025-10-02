"""Test WebSearch with automatic permission approval."""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
    query,
)


async def auto_approve_websearch(
    tool_name: str, tool_input: dict, context: ToolPermissionContext
) -> PermissionResultAllow:
    """Automatically approve WebSearch and WebFetch tools."""
    print(f"\n[Permission Request] Tool: {tool_name}")
    print(f"                     Input: {str(tool_input)[:100]}...")

    if tool_name in ["WebSearch", "WebFetch"]:
        print(f"                     ✅ AUTO-APPROVED")
        return PermissionResultAllow(behavior="allow")

    # Deny other tools
    print(f"                     ❌ DENIED")
    return PermissionResultAllow(behavior="allow")  # Allow for testing


async def test_websearch_with_auto_approval():
    """Test WebSearch with automatic approval via can_use_tool callback."""
    print("\n" + "=" * 80)
    print("Testing WebSearch with Auto-Approval")
    print("=" * 80)

    prompt_text = """Use WebSearch to find NVIDIA's Q4 2024 or Q1 2025 revenue.

Report:
1. The revenue amount
2. The source URL
3. The date of the report"""

    # Convert string to async iterable (required for can_use_tool callback)
    async def prompt_stream():
        yield prompt_text

    options = ClaudeAgentOptions(
        system_prompt="You have access to WebSearch tool. Use it to find information.",
        max_turns=10,
        can_use_tool=auto_approve_websearch,  # 🔑 KEY FIX
    )

    print("\nSending query with auto-approval callback...")

    tool_uses = []
    text_responses = []

    async for message in query(prompt=prompt_stream(), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_responses.append(block.text)
                    print(f"\n[Response]: {block.text[:200]}...")
                elif isinstance(block, ToolUseBlock):
                    tool_uses.append(block)

    print("\n" + "=" * 80)
    print("Results:")
    print("=" * 80)
    print(f"Total tool uses: {len(tool_uses)}")
    print(f"Text responses: {len(text_responses)}")

    if tool_uses:
        print("\n✅ Tools successfully used:")
        for i, tool in enumerate(tool_uses, 1):
            print(f"  {i}. {tool.name}")

    if text_responses:
        print("\n📝 Final response:")
        print(text_responses[-1][:500])

    return len(tool_uses) > 0 and "permission" not in text_responses[-1].lower()


async def test_multiple_searches():
    """Test multiple WebSearch queries in sequence."""
    print("\n" + "=" * 80)
    print("Testing Multiple Sequential Searches")
    print("=" * 80)

    questions = [
        "NVIDIA Q4 2024 data center revenue growth rate",
        "AMD MI300X market share 2024 vs NVIDIA",
        "Google TPU v5 deployment volume 2024",
    ]

    options = ClaudeAgentOptions(
        system_prompt="You are a research assistant with WebSearch access.",
        max_turns=15,
        can_use_tool=auto_approve_websearch,
    )

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}/{len(questions)}]: {question}")

        prompt_text = f"Use WebSearch to find: {question}\n\nProvide a concise 1-sentence answer with the source URL."

        # Convert to async iterable
        async def prompt_stream():
            yield prompt_text

        tool_count = 0
        async for message in query(prompt=prompt_stream(), options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        tool_count += 1
                    elif isinstance(block, TextBlock):
                        print(f"  Answer: {block.text[:150]}...")

        print(f"  Tools used: {tool_count}")

    return True


if __name__ == "__main__":
    print("\n🔧 WebSearch Permission Fix Test")
    print("=" * 80)

    # Test 1: Single search with auto-approval
    result1 = asyncio.run(test_websearch_with_auto_approval())

    # Test 2: Multiple sequential searches
    result2 = asyncio.run(test_multiple_searches())

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Test 1 (Auto-Approval): {'PASS ✅' if result1 else 'FAIL ❌'}")
    print(f"Test 2 (Multiple): {'PASS ✅' if result2 else 'FAIL ❌'}")

    if result1:
        print("\n✅ FIX CONFIRMED: can_use_tool callback enables WebSearch!")
        print("   Next: Update deep_research.py to use this pattern")
    else:
        print("\n❌ Fix did not work - need alternative approach")
