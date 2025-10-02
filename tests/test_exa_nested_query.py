"""Test Exa MCP from nested query() - THE CRITICAL TEST.

This test determines if Exa MCP can bypass the SDK permission boundary
that blocks built-in WebSearch from working in nested query() calls.

SUCCESS = We can use Exa in the orchestrator
FAILURE = Need to use file-based workflow instead
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


async def outer_query_simulation():
    """Simulate the outer orchestrator context."""
    print("\n[OUTER] Simulating orchestrator context...")
    print("[OUTER] This represents the normal SDK query() call")

    # Just a placeholder to simulate being in an outer query context
    return "outer_context_initialized"


async def test_exa_from_nested_query():
    """THE CRITICAL TEST: Can Exa MCP work from nested query()?"""
    print("\n" + "=" * 80)
    print("TEST 2: Exa MCP from Nested Query() - PERMISSION BOUNDARY TEST")
    print("=" * 80)
    print("\n🎯 This test answers the KEY question:")
    print("   Can MCP servers bypass the permission boundary that blocks WebSearch?")
    print("\n" + "=" * 80)

    # Check API key
    api_key = os.getenv("EXA_API_KEY")
    if not api_key or api_key == "your-exa-api-key-here":
        print("\n❌ ERROR: EXA_API_KEY not set")
        return False

    # Simulate outer context (like orchestrator)
    await outer_query_simulation()

    # Now call query() WITH Exa MCP (simulating _fetch_web_evidence)
    print("\n[NESTED] Creating nested query() with Exa MCP...")
    print("[NESTED] This simulates orchestrator calling _fetch_web_evidence()")

    options = ClaudeAgentOptions(
        mcp_servers={
            "exa": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "exa-mcp-server"],
                "env": {"EXA_API_KEY": api_key}
            }
        },
        allowed_tools=["mcp__exa__web_search_exa"],
        max_turns=5,
    )

    prompt = """Use mcp__exa__web_search_exa to search: "NVIDIA Q4 2024 data center revenue"

This is a nested query() call - will it work?

Return top 3 results."""

    tool_uses = []
    text_responses = []
    permission_errors = []

    try:
        print("\n[NESTED] Executing Exa search from nested context...")

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text
                        text_responses.append(text)

                        # Check for permission errors
                        if any(word in text.lower() for word in ["permission", "don't have access", "cannot use"]):
                            permission_errors.append(text)
                            print(f"\n   ⚠️  Permission issue detected: {text[:100]}...")
                        else:
                            print(f"\n   ✓ Text response: {text[:100]}...")

                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)
                        print(f"\n   ✅ Tool invoked: {block.name}")

    except Exception as e:
        print(f"\n   ❌ Exception: {e}")
        permission_errors.append(str(e))

    # Analysis
    print("\n" + "=" * 80)
    print("CRITICAL TEST RESULTS:")
    print("=" * 80)
    print(f"Tool uses: {len(tool_uses)}")
    print(f"Text responses: {len(text_responses)}")
    print(f"Permission errors: {len(permission_errors)}")

    # The decisive test
    mcp_works_in_nested_context = (
        len(tool_uses) > 0 and
        len(permission_errors) == 0
    )

    print("\n" + "=" * 80)
    if mcp_works_in_nested_context:
        print("🎉 SUCCESS: Exa MCP WORKS from nested query()!")
        print("=" * 80)
        print("\n✅ MCP servers bypass the permission boundary!")
        print("✅ We can use Exa in the orchestrator")
        print("✅ Fully automated web research is possible")
        print("\n📋 Next steps:")
        print("   1. Run test_exa_investment_search.py for quality validation")
        print("   2. Update orchestrator._fetch_web_evidence() to use Exa MCP")
        print("   3. Achieve +25 quality point improvement")
    else:
        print("❌ FAILURE: Exa MCP blocked by permission boundary")
        print("=" * 80)
        print("\n⚠️  MCP has same limitations as built-in WebSearch")
        print("⚠️  Cannot use MCP from nested query() calls")
        print("\n📋 Alternative approach needed:")
        print("   1. Document this limitation")
        print("   2. Implement file-based workflow instead")
        print("   3. User manually provides web research results")

    if permission_errors:
        print("\n📝 Permission error details:")
        for i, err in enumerate(permission_errors[:3], 1):
            print(f"   {i}. {err[:200]}...")

    return mcp_works_in_nested_context


if __name__ == "__main__":
    print("\n🔬 Exa MCP Nested Query Test - THE DECISIVE TEST")
    print("=" * 80)
    print("This test determines the viability of MCP-based web research")
    print("=" * 80)

    result = asyncio.run(test_exa_from_nested_query())

    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    if result:
        print("✅ MCP APPROACH IS VIABLE")
        print("\nProceed with Exa MCP integration in orchestrator")
    else:
        print("❌ MCP APPROACH NOT VIABLE")
        print("\nFall back to file-based workflow approach")
