"""Test WebSearch directly in Claude Code parent context."""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)


async def test_direct_websearch():
    """Test if WebSearch works when called from parent Claude Code context."""
    print("\n" + "=" * 80)
    print("Direct WebSearch Test (Parent Context)")
    print("=" * 80)

    prompt = """Use WebSearch to find NVIDIA's Q4 2024 or Q1 2025 data center revenue.

Return the information in this JSON format:
{
  "revenue": "amount you found",
  "source": "URL",
  "quarter": "Q4 2024 or Q1 2025"
}"""

    options = ClaudeAgentOptions(
        system_prompt="You have WebSearch access. Use it to find information.",
        max_turns=5,
    )

    print("\nSending query...")

    tool_uses = []
    text_responses = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_responses.append(block.text)
                    print(f"\nText: {block.text[:200]}...")
                elif isinstance(block, ToolUseBlock):
                    tool_uses.append(block)
                    print(f"\nTool: {block.name}")
                    print(f"  Input: {str(block.input)[:100]}...")

    print("\n" + "=" * 80)
    print("Results:")
    print("=" * 80)
    print(f"Tool uses: {len(tool_uses)}")
    print(f"Text responses: {len(text_responses)}")

    if tool_uses:
        print("\n✅ WebSearch WAS used")
        for t in tool_uses:
            print(f"  - {t.name}")
    else:
        print("\n❌ WebSearch was NOT used")

    if text_responses:
        print("\n📝 Final response:")
        print(text_responses[-1][:300])

    return len(tool_uses) > 0


if __name__ == "__main__":
    result = asyncio.run(test_direct_websearch())

    print("\n" + "=" * 80)
    if result:
        print("✅ WebSearch WORKS in parent context!")
        print("   The orchestrator approach should work.")
    else:
        print("❌ WebSearch FAILED even in parent context")
        print("   Need to investigate further...")
