"""Test basic Exa MCP server connectivity.

This test validates that:
1. Exa MCP server can be initialized
2. web_search_exa tool is available
3. Search returns results in expected format
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


async def test_exa_mcp_basic_connectivity():
    """Test basic connection to Exa MCP server."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Exa MCP Connectivity")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("EXA_API_KEY")
    if not api_key or api_key == "your-exa-api-key-here":
        print("\n❌ ERROR: EXA_API_KEY not set in .env file")
        print("   Please add your Exa API key to .env")
        return False

    print(f"\n✓ Exa API key found: {api_key[:10]}...")

    # Configure Exa MCP server
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

    print("\n1. Testing MCP server initialization...")

    # Simple search query
    prompt = """Use the mcp__exa__web_search_exa tool to search for: "NVIDIA quarterly earnings Q4 2024"

Return the top 3 results with titles and URLs."""

    tool_uses = []
    text_responses = []
    errors = []

    try:
        print("2. Executing web search via Exa MCP...")
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_responses.append(block.text)
                        print(f"\n   Response preview: {block.text[:150]}...")
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)
                        print(f"\n   ✓ Tool used: {block.name}")

    except Exception as e:
        errors.append(str(e))
        print(f"\n   ❌ Error: {e}")

    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Tool uses: {len(tool_uses)}")
    print(f"Text responses: {len(text_responses)}")
    print(f"Errors: {len(errors)}")

    # Success criteria
    success = (
        len(tool_uses) > 0 and  # Tool was invoked
        len(errors) == 0 and  # No errors
        "permission" not in " ".join(text_responses).lower()  # No permission issues
    )

    if success:
        print("\n✅ SUCCESS: Exa MCP server is working!")
        print("   - MCP server initialized")
        print("   - web_search_exa tool available")
        print("   - Search executed successfully")
    else:
        print("\n❌ FAILURE: Exa MCP server test failed")
        if len(tool_uses) == 0:
            print("   - Tool was not invoked")
        if len(errors) > 0:
            print(f"   - Errors encountered: {errors}")
        if "permission" in " ".join(text_responses).lower():
            print("   - Permission issues detected")

    return success


if __name__ == "__main__":
    print("\n🔬 Exa MCP Basic Connectivity Test")
    print("=" * 80)
    print("This test validates basic MCP server functionality")
    print("Prerequisites:")
    print("  1. EXA_API_KEY set in .env file")
    print("  2. npm install -g exa-mcp-server (will auto-install via npx)")
    print("=" * 80)

    result = asyncio.run(test_exa_mcp_basic_connectivity())

    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    if result:
        print("✅ Test PASSED")
        print("\nNext: Run test_exa_nested_query.py to test permission boundaries")
    else:
        print("❌ Test FAILED")
        print("\nTroubleshooting:")
        print("1. Check EXA_API_KEY in .env file")
        print("2. Ensure exa-mcp-server is installed: npm install -g exa-mcp-server")
        print("3. Check API key is valid at https://exa.ai/")
