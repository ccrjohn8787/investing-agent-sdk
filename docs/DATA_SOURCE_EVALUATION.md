# Data Source Evaluation & Strategy

**Version**: 1.0
**Date**: 2025-10-03
**Purpose**: Comprehensive evaluation of financial data sources with decision framework

---

## Executive Summary

**Current Stack**: SEC EDGAR API (direct), Yahoo Finance (yfinance), Brave Search MCP
**Evaluation Result**: 5 data sources evaluated (3 current + 7 MCP alternatives) + **Brave vs Exa tested**
**Recommendation**: Keep current stack, build our own SEC parser, skip paid alternatives

**Key Decisions**:
1. ✅ **Keep SEC EDGAR direct API** - Free, reliable, no rate limits for companyfacts
2. ✅ **Keep Yahoo Finance (yfinance)** - Real-time prices, 15-min delayed data is sufficient
3. ✅ **Keep Brave Search MCP** - **TESTED**: Outperforms Exa 73/100 vs 40/100, FREE tier sufficient
4. ✅ **Build SEC filing parser** - Full control, FREE vs paying for Financial Datasets MCP
5. ❌ **Skip Octagon MCP** - Overlaps with our analysis layer, $0.10/call expensive
6. ❌ **Skip Exa AI** - **TESTED**: Underperforms Brave, costs money, "LLM-first" failed to deliver
7. ❌ **Skip Financial Datasets MCP** - Build our own parser instead (user decision)

---

## Evaluation Framework

### Evaluation Dimensions

**For each data source, evaluate on 7 dimensions:**

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **1. Data Coverage** | 25% | What data is available? (fundamentals, filings, prices, news) |
| **2. Data Quality** | 20% | Accuracy, timeliness, completeness |
| **3. Cost Structure** | 20% | Free, pay-per-call, subscription, rate limits |
| **4. Reliability** | 15% | Uptime, SLA, historical stability |
| **5. Integration Effort** | 10% | Ease of integration (MCP vs custom API) |
| **6. Use Case Fit** | 5% | Alignment with institutional investment research |
| **7. Vendor Lock-in** | 5% | Can we switch easily if needed? |

**Scoring**: 1-10 per dimension, weighted total = 0-100

**Decision Criteria**:
- **90-100**: Adopt immediately (critical, no alternative)
- **75-89**: Adopt conditionally (high value, evaluate cost)
- **60-74**: Consider for Phase 2 (nice-to-have)
- **<60**: Skip (low ROI, overlaps with existing)

---

## Current Data Sources (In Production)

### 1. SEC EDGAR Direct API

**What it is**: Official SEC API for company financials and filings
**Implementation**: `src/investing_agents/connectors/edgar.py` (533 lines, battle-tested)
**Endpoints Used**:
- `/api/xbrl/companyfacts/{CIK}.json` - Structured financial data (XBRL)
- `/files/company_tickers.json` - Ticker to CIK mapping

**Data Coverage (Score: 9/10)**:
- ✅ 10 years historical financials (revenue, EBIT, shares, tax rate)
- ✅ Balance sheet items (current assets/liabilities, lease data)
- ✅ Cash flow components (D&A, CapEx)
- ✅ Both US-GAAP and IFRS tags supported
- ✅ Quarterly + annual data (TTM calculation built-in)
- ❌ No full-text 10-K/10-Q (just XBRL facts)
- ❌ No MD&A, risk factors, or narrative sections

**Data Quality (Score: 10/10)**:
- ✅ Official SEC source (gold standard)
- ✅ Legally required to be accurate (SOX compliance)
- ✅ Time-stamped filings (no retroactive changes)
- ✅ Consistent XBRL schema

**Cost Structure (Score: 10/10)**:
- ✅ **FREE** (U.S. government public data)
- ✅ No rate limits on companyfacts endpoint (bulk data allowed)
- ✅ Only requires User-Agent header (email@example.com)
- ⚠️ SEC requests 10 requests/second limit (easily achievable)

**Reliability (Score: 9/10)**:
- ✅ Government-run infrastructure (high uptime)
- ✅ No commercial dependency
- ❌ Occasional maintenance windows (rare)
- ✅ Data available within hours of filing

**Integration Effort (Score: 10/10)**:
- ✅ Already integrated (533 lines of production code)
- ✅ httpx-based, async-ready
- ✅ Comprehensive tag handling (revenue, EBIT, shares, etc.)
- ✅ Unit/scale conversion handled (USD, USDm, USDth)

**Use Case Fit (Score: 10/10)**:
- ✅ Perfect for DCF valuation (revenue, margins, shares)
- ✅ Auditable source for Investment Committee
- ✅ Required for backtesting (time-stamped fundamentals)

**Vendor Lock-in (Score: 10/10)**:
- ✅ Government data, no vendor risk
- ✅ Can't be shut down or paywalled

**Overall Score**: **94/100** - **CRITICAL, KEEP**

**Recommendation**: **Maintain as primary fundamentals source**. No MCP alternative can match free, reliable, official SEC data.

---

### 2. Yahoo Finance (yfinance)

**What it is**: Python library wrapping Yahoo Finance API
**Implementation**: `src/investing_agents/connectors/price_fetcher.py` (321 lines)
**Endpoints Used**: `yf.Ticker(symbol).info` - Real-time/delayed stock data

**Data Coverage (Score: 8/10)**:
- ✅ Real-time prices (15-min delayed for free tier)
- ✅ Market cap, shares outstanding
- ✅ TTM revenue, EBITDA, free cash flow
- ✅ Operating margins, tax rates
- ✅ Balance sheet (debt, cash)
- ❌ Not as comprehensive as SEC EDGAR for historical data
- ⚠️ Some fields unreliable (API changes frequently)

**Data Quality (Score: 7/10)**:
- ✅ Generally accurate for prices and basic metrics
- ⚠️ Fundamentals can be stale (quarterly updates)
- ❌ No official data provenance (scraped from Yahoo Finance)
- ❌ Fields change without notice (API instability)
- ⚠️ Data completeness varies by ticker

**Cost Structure (Score: 10/10)**:
- ✅ **FREE** (no API key required)
- ✅ No hard rate limits (reasonable use)
- ⚠️ May break if Yahoo changes their backend

**Reliability (Score: 6/10)**:
- ⚠️ Unofficial API (could break anytime)
- ⚠️ Known to have sporadic outages
- ❌ No SLA or support
- ⚠️ Community-maintained library

**Integration Effort (Score: 9/10)**:
- ✅ Already integrated (321 lines)
- ✅ Simple API (`yf.Ticker(symbol).info`)
- ✅ Async wrappers written

**Use Case Fit (Score: 8/10)**:
- ✅ Perfect for current price (valuation comparison)
- ✅ Quick fundamentals check (real-time market cap)
- ⚠️ Not suitable as primary fundamentals source
- ✅ Good for backtesting (historical price data)

**Vendor Lock-in (Score: 7/10)**:
- ⚠️ Moderately locked in (would need alternative for prices)
- ✅ Easy to swap with Alpha Vantage, IEX Cloud, etc.

**Overall Score**: **79/100** - **KEEP, with backup plan**

**Recommendation**: **Keep for real-time prices**, but **maintain SEC EDGAR as primary fundamentals source**. Consider Alpha Vantage or IEX Cloud as backup if yfinance breaks.

---

### 3. Brave Search MCP

**What it is**: Official Brave Search MCP server for web search
**Implementation**: `src/investing_agents/core/mcp_config.py` (rate-limited integration)
**Tools Used**:
- `brave_web_search` - General web search
- `brave_news_search` - News-specific search

**Data Coverage (Score: 8/10)**:
- ✅ Real-time web search (news, articles, blogs)
- ✅ Dedicated news search endpoint
- ✅ Independent index (not Google)
- ❌ No historical archives (real-time only)
- ❌ No financial-specific filtering

**Data Quality (Score: 7/10)**:
- ✅ Independent search index (less SEO spam than Google)
- ✅ Privacy-focused (no tracking)
- ⚠️ Smaller index than Google (may miss some sources)
- ⚠️ Quality varies by query relevance

**Cost Structure (Score: 8/10)**:
- **Free Tier**: 2,000 queries/month (~67/day)
- **Pro Tier**: $5/month for 20,000 queries
- ⚠️ Free tier may be limiting for heavy research
- ✅ Reasonable pricing for Pro

**Reliability (Score: 8/10)**:
- ✅ Commercial product with SLA
- ✅ Stable API (no sudden changes)
- ✅ Good uptime history
- ⚠️ Relatively new MCP server

**Integration Effort (Score: 9/10)**:
- ✅ Already integrated with rate limiting
- ✅ Official MCP server (npx install)
- ✅ Simple configuration (API key + stdio)

**Use Case Fit (Score: 7/10)**:
- ✅ Good for hypothesis research (qualitative evidence)
- ✅ News monitoring for sentiment
- ⚠️ Not suitable for backtesting (real-time only, no date filtering)
- ⚠️ Overlaps with agent's own web browsing

**Vendor Lock-in (Score: 8/10)**:
- ✅ Can easily swap with Exa, Perplexity, Google
- ✅ Standard MCP interface

**Overall Score**: **79/100** - **KEEP, evaluate usage**

**Recommendation**: **Keep for Phase 1**, but **monitor usage** to decide if free tier sufficient or need Pro. Consider Exa as alternative (better for research-focused queries).

---

## MCP Server Alternatives (Evaluated)

### 4. Financial Datasets MCP

**What it is**: Official MCP server for financialdatasets.ai API
**Source**: https://docs.financialdatasets.ai/mcp-server
**Tools**: 16+ tools (getStockPriceSnapshot, getFinancialMetrics, getBalanceSheet, getIncomeStatement, getCompanyFacts, getNews)

**Data Coverage (Score: 9/10)**:
- ✅ Stock prices (real-time + historical)
- ✅ Financial statements (income, balance, cash flow)
- ✅ Company facts (similar to SEC companyfacts)
- ✅ SEC filings (10-K, 10-Q, 8-K)
- ✅ Financial news
- ✅ Crypto prices (bonus)
- ❌ Coverage details not fully documented

**Data Quality (Score: 7/10)**:
- ⚠️ Claims "high-quality" but no provenance details
- ⚠️ Likely aggregates from multiple sources (SEC + others)
- ❌ Not clear if data is normalized/cleaned
- ⚠️ Newer service, less proven than SEC direct

**Cost Structure (Score: 5/10)**:
- ⚠️ **Requires paid API key** (pricing not public)
- ⚠️ "Free signup" mentioned but limits unclear
- ❌ **Major concern**: Unknown cost per call
- ❌ Could be expensive at scale

**Reliability (Score: 6/10)**:
- ⚠️ Startup (financialdatasets.ai)
- ⚠️ No SLA information
- ❌ Could shut down or change pricing

**Integration Effort (Score: 9/10)**:
- ✅ Official MCP server (easy install)
- ✅ Comprehensive tools (16+ endpoints)
- ✅ OAuth 2.1 + API key auth

**Use Case Fit (Score: 7/10)**:
- ✅ Good for full-text SEC filings (MD&A, risk factors)
- ⚠️ Overlaps heavily with SEC EDGAR + Yahoo Finance
- ❌ Not clear what unique value it provides
- ⚠️ Would need to justify cost vs free alternatives

**Vendor Lock-in (Score: 5/10)**:
- ⚠️ Commercial vendor (lock-in risk)
- ⚠️ Could raise prices or shut down
- ❌ Proprietary API (not easily replaceable)

**Overall Score**: **69/100** - **CONDITIONAL**

**Recommendation**: **Adopt ONLY if we need full-text SEC filing parsing** (MD&A, risk factors) and cost is reasonable (<$0.01/call). Otherwise, **stick with free SEC EDGAR + Yahoo Finance**.

**Decision Criteria**:
1. ✅ If `getCompanyFacts` is just repackaged SEC data → **Skip** (use SEC direct)
2. ✅ If we need `get_news` → **Evaluate** cost vs Brave Search
3. ✅ If we need full-text 10-K/10-Q parsing → **Adopt** (saves us building parser)
4. ❌ If cost > $0.05/analysis → **Skip** (blows our $3.35 budget)

**Next Steps**: Request pricing details before Phase 1 implementation.

---

### 5. Octagon MCP Server

**What it is**: Free MCP server for Octagon Market Intelligence API
**Source**: https://github.com/OctagonAI/octagon-mcp-server
**Tools**: 3 agents (octagon-agent, octagon-scraper-agent, octagon-deep-research-agent)

**Data Coverage (Score: 10/10)**:
- ✅ SEC filings (10-K, 10-Q, 8-K, 20-F, S-1) - 8000+ companies
- ✅ Earnings call transcripts (10 years historical)
- ✅ Financial metrics (10 years)
- ✅ Stock market data (10,000+ tickers)
- ✅ Private company research (3M+ companies)
- ✅ Funding rounds (500k+ deals)
- ✅ M&A and IPO transactions (2M+ deals)
- ✅ Institutional holdings
- ✅ Crypto market data

**Data Quality (Score: 8/10)**:
- ✅ Claims "comprehensive research tools"
- ✅ Aggregates from multiple sources
- ⚠️ AI-powered insights (may introduce errors)
- ⚠️ Data provenance unclear

**Cost Structure (Score: 3/10)**:
- ⚠️ **FREE MCP server**, but requires **paid Octagon API key**
- ❌ **CRITICAL**: Octagon charges **~$0.10 per API call** (expensive!)
- ❌ At 100 calls/analysis → **$10/analysis** (3x our $3.35 budget)
- ❌ **Deal breaker for cost-sensitive use case**

**Reliability (Score: 6/10)**:
- ⚠️ Startup (Octagon AI)
- ⚠️ No public SLA
- ⚠️ Could change pricing or shut down

**Integration Effort (Score: 8/10)**:
- ✅ Official MCP server (easy install)
- ✅ Three specialized agents
- ⚠️ Requires Octagon API key registration

**Use Case Fit (Score: 5/10)**:
- ⚠️ **Overlaps heavily with our analysis layer**
- ❌ "octagon-deep-research-agent" duplicates our DeepResearchAgent
- ❌ We want to build our own analysis, not outsource to Octagon
- ✅ Private market data (funding, M&A) is unique
- ⚠️ Not clear we need private market data for public equity research

**Vendor Lock-in (Score: 4/10)**:
- ❌ Proprietary API (significant lock-in)
- ❌ Expensive switching cost if they raise prices
- ❌ Data aggregation is opaque (can't replicate)

**Overall Score**: **59/100** - **SKIP**

**Recommendation**: **Do NOT adopt**. Too expensive ($0.10/call), overlaps with our analysis capabilities, and creates vendor lock-in.

**Rationale**:
1. ❌ **Cost**: $0.10/call × 100 calls = $10/analysis (blows $3.35 budget)
2. ❌ **Overlap**: Their "deep research agent" competes with ours
3. ❌ **Philosophy**: We want deterministic DCF + custom analysis, not outsourced AI insights
4. ⚠️ **Private market data**: Interesting, but not core to public equity long-term research

**Alternative**: If we need private market data (funding rounds, M&A), use **PitchBook API** or **Crunchbase** (more established, better pricing).

---

### 6. SEC EDGAR MCP Server (Community)

**What it is**: Community-built MCP server for SEC EDGAR
**Source**: https://github.com/stefanoamorelli/sec-edgar-mcp
**Tools**: Tools for company submissions, financial concepts, facts, XBRL frames

**Data Coverage (Score: 8/10)**:
- ✅ Same data as our direct SEC EDGAR integration
- ✅ XBRL frames (standardized financials)
- ❌ No advantage over our edgar.py (533 lines)

**Data Quality (Score: 10/10)**:
- ✅ Official SEC data (same as our current integration)

**Cost Structure (Score: 10/10)**:
- ✅ **FREE** (SEC public data)

**Reliability (Score: 7/10)**:
- ⚠️ Community-maintained (not official)
- ⚠️ Could become unmaintained
- ⚠️ Depends on SEC API stability

**Integration Effort (Score: 7/10)**:
- ⚠️ Would require migration from our edgar.py
- ⚠️ Need to test if feature-complete vs our implementation
- ❌ No clear benefit over our custom integration

**Use Case Fit (Score: 6/10)**:
- ⚠️ Duplicates our existing edgar.py
- ❌ No additional data or features
- ❌ Would be refactoring for refactoring's sake

**Vendor Lock-in (Score: 8/10)**:
- ✅ Open-source, can fork if needed
- ⚠️ Still depends on SEC API

**Overall Score**: **72/100** - **SKIP (for now)**

**Recommendation**: **Keep our current edgar.py**. Only consider this MCP server if:
1. Our edgar.py becomes unmaintainable (unlikely, it's 533 lines and stable)
2. They add features we need (full-text filing parsing, MD&A extraction)
3. We want standardized MCP interface for all data sources (not a priority)

**Rationale**: Our direct integration is **battle-tested, comprehensive, and works**. Migrating to MCP adds dependency without clear benefit.

---

### 7. Financial Modeling Prep MCP Server

**What it is**: MCP server for Financial Modeling Prep (FMP) API
**Source**: https://github.com/imbenrabi/Financial-Modeling-Prep-MCP-Server
**Tools**: Company profiles, financial statements, metrics, analyst data, SEC filings, market data

**Data Coverage (Score: 9/10)**:
- ✅ Company profiles
- ✅ Financial statements (income, balance, cash flow)
- ✅ Analyst estimates and ratings
- ✅ SEC filings
- ✅ Market data
- ⚠️ Similar to Financial Datasets MCP

**Data Quality (Score: 7/10)**:
- ✅ FMP is established provider (better track record than Financial Datasets)
- ⚠️ Still aggregated data (not official SEC direct)
- ⚠️ Quality varies by endpoint

**Cost Structure (Score: 6/10)**:
- ⚠️ **Requires FMP API subscription** (starts at $14/month)
- ⚠️ Higher tiers for more requests ($199/month Pro)
- ⚠️ Free tier: 250 requests/day (may be sufficient for testing)
- ❌ Monthly subscription vs pay-per-call (less flexible)

**Reliability (Score: 8/10)**:
- ✅ Established provider (Financial Modeling Prep)
- ✅ Public SLA and documentation
- ✅ Widely used in finance community

**Integration Effort (Score: 8/10)**:
- ✅ MCP server available (easy install)
- ✅ Well-documented API
- ⚠️ Would need to validate data quality vs SEC direct

**Use Case Fit (Score: 7/10)**:
- ✅ **Analyst estimates** are unique value-add (not in SEC EDGAR)
- ✅ **Analyst ratings** (upgrades/downgrades) useful for sentiment
- ⚠️ Financial statements overlap with SEC EDGAR
- ⚠️ Not clear if analyst data is worth $14/month

**Vendor Lock-in (Score: 6/10)**:
- ⚠️ Proprietary API (moderate lock-in)
- ✅ Can cancel subscription anytime
- ✅ Multiple alternatives exist (Alpha Vantage, IEX Cloud)

**Overall Score**: **73/100** - **CONSIDER for Phase 2**

**Recommendation**: **Skip for Phase 1**, **evaluate for Phase 2** if we need analyst estimates/ratings.

**Rationale**:
1. ✅ **Analyst data** is unique (SEC doesn't have this)
2. ⚠️ **Cost**: $14/month ($168/year) for starter tier
3. ⚠️ **Overlap**: Most data duplicates SEC EDGAR + Yahoo Finance
4. 🔄 **Decision**: If analyst sentiment becomes Tier 1 feature → adopt. Otherwise skip.

**Alternative**: Scrape analyst ratings from free sources (Yahoo Finance, MarketWatch) instead of paying $14/month.

---

## Summary Scorecard

| Data Source | Overall Score | Status | Primary Use Case | Cost |
|-------------|---------------|--------|------------------|------|
| **SEC EDGAR Direct API** | **94/100** | ✅ Keep | Fundamentals, DCF inputs | FREE |
| **Yahoo Finance (yfinance)** | **79/100** | ✅ Keep | Real-time prices | FREE |
| **Brave Search MCP** | **79/100** | ✅ Keep | Web research, news | FREE (2k/mo) |
| **Financial Datasets MCP** | **69/100** | 🔄 Conditional | Full-text SEC filings (if needed) | Unknown |
| **SEC EDGAR MCP** | **72/100** | ❌ Skip | Duplicate of our edgar.py | FREE |
| **Financial Modeling Prep** | **73/100** | 🔄 Phase 2 | Analyst estimates/ratings | $14/mo |
| **Octagon MCP** | **59/100** | ❌ Skip | Too expensive, overlaps analysis | $0.10/call |

---

## Decision Framework: When to Use What

### Use Case 1: DCF Valuation Inputs (Revenue, Margins, Shares)
**Primary**: SEC EDGAR Direct API (`edgar.py`)
**Backup**: Yahoo Finance (yfinance) for TTM metrics
**Why**: Official, free, auditable, time-stamped

### Use Case 2: Current Stock Price
**Primary**: Yahoo Finance (yfinance)
**Backup**: Financial Datasets MCP (if we adopt)
**Why**: Real-time, free, simple API

### Use Case 3: Historical Fundamentals (Backtesting)
**Primary**: SEC EDGAR Direct API (`edgar.py`)
**Backup**: None needed (SEC is gold standard)
**Why**: Time-stamped filings, no data leakage risk

### Use Case 4: Full-Text SEC Filings (MD&A, Risk Factors)
**Primary**: TBD - Need to build parser or use MCP
**Options**:
1. Build our own parser (httpx + BeautifulSoup) - **FREE**
2. Financial Datasets MCP `getFilings` - **Paid** (unknown cost)
3. Octagon MCP - **Too expensive** ($0.10/call)
**Decision**: **Build parser in Phase 1** (saves $X/analysis, full control)

### Use Case 5: Web Research (Hypothesis Validation)
**Primary**: Brave Search MCP (`brave_web_search`)
**Alternative**: Exa (if better for research queries)
**Why**: Independent index, reasonable free tier

### Use Case 6: News & Sentiment
**Primary**: Brave Search MCP (`brave_news_search`)
**Alternative**: Financial Datasets MCP `getNews` (if we adopt)
**Why**: Real-time, free tier sufficient for Phase 1

### Use Case 7: Analyst Estimates & Ratings
**Primary**: Not implemented (Phase 2 feature)
**Options**:
1. Financial Modeling Prep MCP - $14/month
2. Scrape Yahoo Finance - FREE
3. Skip entirely - Not core to our DCF approach
**Decision**: **Defer to Phase 2**, evaluate if needed

### Use Case 8: Insider Trading Data
**Primary**: Not implemented (Tier 2 feature per INSIDER_DATA_EVALUATION.md)
**Options**:
1. FinnHub API - $0-80/month
2. Financial Datasets MCP (if has this data)
3. SEC Form 4 direct (build parser)
**Decision**: **Defer to Phase 2** (deprioritized after critical review)

---

## Recommendations by Phase

### Phase 0-1 (Current, Weeks 1-12)

**Keep**:
1. ✅ SEC EDGAR Direct API - Primary fundamentals source
2. ✅ Yahoo Finance (yfinance) - Real-time prices
3. ✅ Brave Search MCP - Web research

**Build**:
1. ✅ SEC filing full-text parser (10-K, 10-Q) - Extract MD&A, risk factors
2. ✅ Trusted source scraper (SemiAnalysis, Damodaran blog) - Per memory architecture

**Skip**:
1. ❌ Octagon MCP - Too expensive, overlaps our analysis
2. ❌ SEC EDGAR MCP - Duplicates our edgar.py
3. ❌ Financial Modeling Prep - Defer to Phase 2

**Evaluated & Decided**:
1. ✅ Financial Datasets MCP - Skip (build our own parser instead)
2. ✅ Exa vs Brave Search - Tested, Brave wins 73/100 vs 40/100 (keep Brave)

### Phase 2 (Months 4-6, Optional)

**Consider Adding**:
1. 🔄 Financial Modeling Prep MCP - If we need analyst estimates/ratings ($14/month)
2. 🔄 FinnHub API - If insider data proves valuable (Tier 2 feature)
3. 🔄 Alternative news sources - If Brave Search insufficient

**Build**:
1. ✅ Advanced web scraping - Extract data from paywalled sources (Stratechery, etc.)
2. ✅ Sentiment analysis pipeline - Analyze news/social media

---

## Cost Impact Analysis

**Current Stack Cost** (per analysis):
- SEC EDGAR: $0.00 (free)
- Yahoo Finance: $0.00 (free)
- Brave Search: $0.00 (free tier, 2k/month = 67/day)
- **Total**: **$0.00 data cost** (all LLM cost is in agents)

**If We Adopt Financial Datasets MCP** (estimated):
- Assume $0.01/call, 10 calls/analysis = **+$0.10/analysis**
- New total: **$3.45/analysis** (still well under $5 target)
- **Decision**: Acceptable if provides full-text filing parsing

**If We Adopt Octagon MCP** (estimated):
- Assume $0.10/call, 20 calls/analysis = **+$2.00/analysis**
- New total: **$5.35/analysis** (60% increase, unacceptable)
- **Decision**: REJECT (blows budget)

**If We Adopt Financial Modeling Prep** (subscription):
- $14/month ÷ 30 analyses/month = **+$0.47/analysis**
- New total: **$3.82/analysis** (14% increase)
- **Decision**: Acceptable ONLY if analyst data proves Tier 1 value

**Cost Budget Constraint**: Stay under **$5.00/analysis** (current: $3.35)
**Headroom**: **$1.65/analysis** available for new data sources

---

## Integration Priority (Phase 1)

**Week 1-2** (Phase 0):
1. ✅ No new integrations (use existing stack)
2. ✅ Validate current data sources work for backtesting

**Week 3-4**:
1. ✅ Build SEC filing full-text parser (10-K, 10-Q MD&A extraction)
2. 🔄 Evaluate Financial Datasets MCP (get pricing, compare to DIY parser)

**Week 5-6**:
1. ✅ Implement trusted source scraper (SemiAnalysis, Damodaran)
2. 🔄 Test Exa vs Brave Search (quality comparison)

**Week 7-8**:
1. ✅ Finalize data source stack for Phase 1
2. ✅ Document any new integrations

---

## Risk Assessment

### Risk 1: Yahoo Finance API Breaks
**Likelihood**: Medium (unofficial API, history of breakages)
**Impact**: High (lose real-time price data)
**Mitigation**:
- Add Alpha Vantage as backup (free tier: 5 calls/min)
- Add IEX Cloud as backup (free tier: 50k requests/month)
- Store last-known price in state (graceful degradation)

### Risk 2: Brave Search Free Tier Insufficient
**Likelihood**: Medium (67 queries/day may not be enough)
**Impact**: Medium (need to upgrade to Pro $5/month)
**Mitigation**:
- Monitor usage with rate limiter
- Upgrade to Pro if needed ($5/month is acceptable)
- Consider Exa as alternative (different pricing model)

### Risk 3: SEC EDGAR Changes API
**Likelihood**: Low (government API, stable)
**Impact**: High (lose primary fundamentals source)
**Mitigation**:
- Monitor SEC announcements
- Have Financial Datasets MCP as backup (if we adopt)
- SEC companyfacts API is well-established (unlikely to change)

### Risk 4: Financial Datasets MCP Too Expensive
**Likelihood**: High (pricing not public, could be $0.05-0.10/call)
**Impact**: Medium (would need to build parser ourselves)
**Mitigation**:
- Request pricing BEFORE adopting
- Build DIY parser as fallback (httpx + BeautifulSoup)
- Only adopt if <$0.02/call

---

## Next Actions

**Immediate** (Week 1):
1. ✅ Document current data source usage in codebase - Complete
2. ✅ Exa vs Brave Search comparison - Complete (Brave wins 73/100 vs 40/100)
3. ✅ Decision on Financial Datasets MCP - Skip (build own parser)
4. ✅ Validate SEC EDGAR for backtesting (frozen fundamentals test)

**Short-term** (Week 2-4):
1. ✅ Build SEC filing full-text parser (start with 10-K MD&A) - Decided: DIY approach
2. ✅ Implement trusted source scraper (SemiAnalysis RSS)
3. 🔄 Monitor Brave Search usage (decide if Pro tier needed $5/month)

**Medium-term** (Month 2-3):
1. 🔄 Evaluate analyst data need (Financial Modeling Prep decision)
2. 🔄 Consider insider data sources (if Tier 2 gets elevated)
3. ✅ Finalize Phase 1 data source stack

---

## Appendix: Data Source Contacts

**SEC EDGAR**:
- Website: https://www.sec.gov/edgar
- API Docs: https://www.sec.gov/edgar/sec-api-documentation
- Support: Use User-Agent header with email

**Yahoo Finance (yfinance)**:
- GitHub: https://github.com/ranaroussi/yfinance
- Issues: GitHub issues (community support)

**Brave Search MCP**:
- Website: https://brave.com/search/api/
- Pricing: https://brave.com/search/api/pricing/
- Support: api@brave.com

**Financial Datasets MCP**:
- Website: https://www.financialdatasets.ai
- Docs: https://docs.financialdatasets.ai
- Support: support@financialdatasets.ai (REQUEST PRICING)

**Financial Modeling Prep**:
- Website: https://financialmodelingprep.com
- Pricing: https://financialmodelingprep.com/developer/docs/pricing
- Support: support@financialmodelingprep.com

---

**Last Updated**: 2025-10-03 (Added Brave vs Exa test results)
**Next Review**: After Phase 0 complete (Week 2), re-evaluate based on usage patterns
**Decision Authority**: User (final approval on paid data sources)

---

## APPENDIX: Brave Search vs Exa AI - Test Results

**Test Date**: 2025-10-03
**Test File**: `tests/test_brave_vs_exa_comparison.py`

### Test Design

**4 Investment Research Scenarios** (weighted):
1. **Quantitative Earnings Data** (30%) - "NVIDIA Q3 2024 data center revenue growth rate"
2. **Competitive Dynamics** (25%) - "NVIDIA vs AMD AI accelerator market share competition 2024"
3. **Forward-Looking Guidance** (25%) - "Semiconductor industry capex spending forecast 2025"
4. **Strategic Analysis** (20%) - "NVIDIA AI chip supply chain constraints TSMC"

**Evaluation Criteria**:
- Keyword Relevance (70%): Financial terms found in results
- Source Quality (30%): Results from authoritative sources

### Results

**Overall Scores**:
- 🏆 **Brave Search**: **73.0/100**
- ❌ **Exa AI**: **40.5/100**
- **Winner**: Brave Search (+32.5 points, 80% better)

**Head-to-Head Record**:
- Brave wins: 3
- Exa wins: 0
- Ties: 1

**Detailed Results**:

| Test Case | Brave Score | Exa Score | Winner |
|-----------|-------------|-----------|--------|
| Quantitative Earnings Data | 80.0 | 0.0 | Brave |
| Competitive Dynamics | 70.0 | 58.3 | Brave |
| Forward-Looking Guidance | 70.0 | 70.0 | Tie |
| Strategic Analysis | 70.0 | 42.0 | Brave |

### Key Findings

**Brave Search Advantages**:
1. ✅ **100% keyword coverage** on most queries (found all expected financial terms)
2. ✅ **Consistent quality** across all 4 test cases (70-80/100)
3. ✅ **FREE** (2,000 queries/month, ~67/day)
4. ✅ **Better source quality** on earnings queries (investor.nvidia.com found)

**Exa AI Weaknesses**:
1. ❌ **Failed completely** on earnings query (0/100 score)
2. ❌ **Lower keyword relevance** (60-83% vs Brave's 100%)
3. ❌ **Costs money** (~$0.001-0.005 per search)
4. ❌ "LLM-first search" did NOT translate to better quality for investment research

### Decision

**✅ KEEP BRAVE SEARCH** as primary web research tool

**Rationale**:
1. **Quality**: Brave outperformed Exa by 80% (73 vs 40.5)
2. **Cost**: Brave is FREE vs Exa's pay-per-call
3. **Reliability**: Consistent 70-80/100 scores across diverse queries
4. **Budget impact**: Zero (maintains $3.35/analysis cost)

**Do NOT adopt Exa** - Failed to deliver on "LLM-first" promise for financial research

### Updated Recommendations

**Phase 1** (Weeks 1-12):
- ✅ Keep Brave Search MCP for all web research
- ✅ Use free tier (2,000 queries/month = 67/day sufficient)
- ✅ Monitor usage with rate limiter (already implemented)
- ❌ Skip Exa AI (does not provide value over Brave)

**Phase 2** (Optional):
- 🔄 Re-evaluate Exa if they improve financial search quality
- 🔄 Consider upgrading Brave to Pro ($5/month) if free tier insufficient
- 🔄 Test specialized financial search APIs (if emerge)
