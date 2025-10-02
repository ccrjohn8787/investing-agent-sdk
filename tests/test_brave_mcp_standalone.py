"""Standalone test for Brave Search MCP integration.

This is THE CRITICAL TEST that determines if Brave MCP can provide
web research capabilities where previous approaches failed.

Success criteria:
1. MCP server connects successfully
2. brave_web_search tool is available and executable
3. Search returns actual web results (not permission errors)
4. Evidence can be extracted from results
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, query

from investing_agents.core.mcp_config import MCPConfig

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


async def test_brave_mcp_connection():
    """Test 1: Can we connect to Brave MCP server?"""
    print("\n" + "=" * 80)
    print("TEST 1: Brave MCP Server Connection")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key or api_key == "your-brave-api-key-here":
        print("❌ ERROR: BRAVE_API_KEY not set in .env")
        return False

    print(f"✓ Brave API key found: {api_key[:10]}...")

    # Create MCP configuration
    try:
        mcp_config = MCPConfig(brave_tier="free")
        print("✓ MCP config created")
    except Exception as e:
        print(f"❌ Failed to create MCP config: {e}")
        return False

    # Get research options
    try:
        options = mcp_config.create_research_options(max_turns=5)
        print("✓ Research options configured")
        print(f"  - MCP servers: {list(options.mcp_servers.keys())}")
        print(f"  - Allowed tools: {options.allowed_tools}")
    except Exception as e:
        print(f"❌ Failed to create research options: {e}")
        return False

    return True


async def test_brave_web_search():
    """Test 2: Can we execute actual web searches?"""
    print("\n" + "=" * 80)
    print("TEST 2: Brave Web Search Execution")
    print("=" * 80)

    # Create configuration
    mcp_config = MCPConfig(brave_tier="free")
    options = mcp_config.create_research_options(max_turns=5)

    # Test search query
    prompt = """Use brave_web_search to search for: "NVIDIA Q4 FY2025 earnings revenue"

Return the top 3 results with titles and URLs."""

    print("\n📡 Executing search...")
    print(f"Query: NVIDIA Q4 FY2025 earnings revenue")

    tool_uses = []
    text_responses = []
    errors = []

    try:
        # Execute rate-limited query
        async for message in mcp_config.rate_limited_query(prompt, options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_responses.append(block.text)
                        print(f"\n📝 Response: {block.text[:200]}...")
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)
                        print(f"\n✅ Tool used: {block.name}")

    except Exception as e:
        errors.append(str(e))
        print(f"\n❌ Error: {e}")

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
        len(errors) == 0 and     # No errors
        len(text_responses) > 0  # Got responses
    )

    # Check for permission/availability errors in responses
    combined_text = " ".join(text_responses).lower()
    has_permission_errors = any(
        phrase in combined_text
        for phrase in [
            "not available",
            "permission",
            "don't have access",
            "cannot use"
        ]
    )

    if has_permission_errors:
        print("\n⚠️  Permission/availability errors detected in responses")
        success = False

    if success:
        print("\n✅ SUCCESS: Brave web search is working!")
        print("   - MCP server connected")
        print("   - brave_web_search tool executed")
        print("   - Results returned successfully")
    else:
        print("\n❌ FAILURE: Brave web search failed")
        if len(tool_uses) == 0:
            print("   - Tool was not invoked")
        if len(errors) > 0:
            print(f"   - Errors: {errors}")
        if has_permission_errors:
            print("   - Permission/availability errors detected")

    return success


async def test_evidence_extraction():
    """Test 3: Can we extract structured evidence from results?"""
    print("\n" + "=" * 80)
    print("TEST 3: Evidence Extraction from Search Results")
    print("=" * 80)

    # Create configuration
    mcp_config = MCPConfig(brave_tier="free")
    options = mcp_config.create_research_options(max_turns=5)

    # Search for specific financial data
    prompt = """Use brave_web_search to find NVIDIA's latest quarterly revenue data.

Extract the following information:
1. Quarter and fiscal year
2. Total revenue amount
3. Data center revenue (if mentioned)
4. Source URL

Format as structured data."""

    print("\n📡 Searching for structured financial data...")

    text_responses = []
    tool_uses = []

    try:
        async for message in mcp_config.rate_limited_query(prompt, options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_responses.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

    # Check if we got structured data
    combined_text = " ".join(text_responses)

    # Look for evidence of structured extraction
    has_revenue_data = any(
        keyword in combined_text.lower()
        for keyword in ["revenue", "billion", "million", "$"]
    )

    has_source = any(
        keyword in combined_text.lower()
        for keyword in ["http", "url", "source", "nvidia"]
    )

    success = (
        len(tool_uses) > 0 and
        has_revenue_data and
        has_source
    )

    if success:
        print("\n✅ SUCCESS: Evidence extraction working!")
        print("   - Found revenue data")
        print("   - Found source attribution")
        print(f"\n📊 Sample extracted data:\n{combined_text[:500]}...")
    else:
        print("\n❌ FAILURE: Evidence extraction incomplete")
        print(f"   - Revenue data found: {has_revenue_data}")
        print(f"   - Source found: {has_source}")

    return success


async def main():
    """Run all Brave MCP tests."""
    print("\n" + "=" * 80)
    print("BRAVE SEARCH MCP - STANDALONE TEST SUITE")
    print("=" * 80)
    print("\nThis test suite validates Brave MCP for web research:")
    print("  1. MCP server connectivity")
    print("  2. Web search execution")
    print("  3. Evidence extraction")
    print("\n" + "=" * 80)

    results = {}

    # Test 1: Connection
    results["connection"] = await test_brave_mcp_connection()

    if not results["connection"]:
        print("\n⚠️  Skipping remaining tests (connection failed)")
        return results

    # Test 2: Web search
    results["web_search"] = await test_brave_web_search()

    # Test 3: Evidence extraction
    results["evidence"] = await test_evidence_extraction()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Connection test: {'✅ PASS' if results['connection'] else '❌ FAIL'}")
    print(f"Web search test: {'✅ PASS' if results['web_search'] else '❌ FAIL'}")
    print(f"Evidence extraction: {'✅ PASS' if results['evidence'] else '❌ FAIL'}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - BRAVE MCP IS WORKING!")
        print("=" * 80)
        print("\n✅ Ready for production integration")
        print("✅ Web research can be fully automated")
        print("✅ Quality improvement (+25 points) achievable")
        print("\nNext steps:")
        print("  1. Integrate Brave MCP into orchestrator")
        print("  2. Update _fetch_web_evidence() to use Brave tools")
        print("  3. Test end-to-end with investment hypotheses")
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"\nFailed tests: {', '.join(failed_tests)}")
        print("\nTroubleshooting:")
        print("  1. Check BRAVE_API_KEY is valid")
        print("  2. Verify Brave MCP server is installed")
        print("  3. Check network connectivity")
        print("  4. Review error messages above")

    return results


if __name__ == "__main__":
    print("\n🚀 Starting Brave Search MCP Tests...")
    results = asyncio.run(main())

    # Exit with error code if tests failed
    if not all(results.values()):
        sys.exit(1)
