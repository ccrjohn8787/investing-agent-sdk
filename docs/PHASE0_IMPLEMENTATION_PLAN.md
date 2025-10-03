# Phase 0: Evaluation Infrastructure - Implementation Plan

**Status**: In Progress (Started Oct 3, 2025)
**Timeline**: 2 weeks
**Purpose**: Build evaluation harness BEFORE enhancements

---

## Overview

**Why Phase 0 First**: Cannot improve what we cannot measure. Need baseline to validate each enhancement and prevent overfitting to single examples (insight from Tauric competitive analysis).

**Success Criteria**:
- ✅ 30 test cases scored and tracked
- ✅ ChromaDB operational with 3 collections
- ✅ Baseline established: Current agent performance documented
- ✅ Data sources: All integrations working

---

## Deliverable 1: 3-Tier Evaluation Corpus

**Purpose**: 30 historical test cases (2020-2023) spanning difficulty spectrum

### Tier 1: Easy (10 companies)
**Characteristics**: Stable, predictable, low volatility
- KO (Coca-Cola)
- JNJ (Johnson & Johnson)
- PG (Procter & Gamble)
- WMT (Walmart)
- PEP (PepsiCo)
- MMM (3M)
- CAT (Caterpillar)
- HD (Home Depot)
- LOW (Lowe's)
- TGT (Target)

**Why**: Baseline accuracy - agent should perform well on stable businesses

### Tier 2: Medium (10 companies)
**Characteristics**: Moderate complexity, growing markets, some volatility
- AAPL (Apple)
- NVDA (NVIDIA)
- TSLA (Tesla)
- META (Meta/Facebook)
- GOOGL (Alphabet)
- MSFT (Microsoft)
- AMZN (Amazon)
- NFLX (Netflix)
- SHOP (Shopify)
- SQ (Block/Square)

**Why**: Real-world complexity - growth vs profitability tradeoffs

### Tier 3: Hard (10 companies)
**Characteristics**: High uncertainty, turnarounds, distressed, IPO-era
- UBER (Uber) - Pre-profitability
- LYFT (Lyft) - Competitive pressure
- BYND (Beyond Meat) - Demand collapse
- PTON (Peloton) - COVID boom-bust
- ZM (Zoom) - Post-COVID normalization
- DASH (DoorDash) - Unit economics questions
- ABNB (Airbnb) - Travel recovery
- RIVN (Rivian) - Pre-revenue/early production
- LCID (Lucid Motors) - Early stage EV
- PLTR (Palantir) - Complex business model

**Why**: Edge cases - highest value-add for AI analyst

### Historical Snapshots

**Analysis Dates** (frozen in time):
- Q4 2020 (Post-COVID initial shock, pre-vaccine)
- Q4 2021 (Growth peak, inflation starting)
- Q4 2022 (Rate hikes, tech selloff)
- Q4 2023 (AI boom, recovery)

**Data Freeze**: Each analysis uses ONLY data available as of that quarter

### Implementation

```bash
# Create test case corpus
mkdir -p data/evaluation_corpus

# Generate test case manifest
cat > data/evaluation_corpus/manifest.json <<EOF
{
  "version": "1.0",
  "created": "2025-10-03",
  "test_cases": [
    {
      "ticker": "KO",
      "company": "Coca-Cola",
      "tier": 1,
      "difficulty": "easy",
      "snapshots": [
        {"date": "2020-12-31", "description": "Post-COVID stability"},
        {"date": "2021-12-31", "description": "Reopening recovery"},
        {"date": "2022-12-31", "description": "Inflation pressure"},
        {"date": "2023-12-31", "description": "Steady state"}
      ]
    },
    // ... (repeat for all 30 tickers)
  ]
}
EOF
```

**Deliverable**: `data/evaluation_corpus/manifest.json` with all 30 companies × 4 snapshots = 120 test cases

---

## Deliverable 2: ChromaDB Memory System

**Purpose**: 3 collections for long-term learning and knowledge storage

### Collection 1: `analysis_memory`
**Purpose**: Store every analysis with outcomes for pattern learning

**Schema**:
```python
{
    "id": "META_2024-10-03_12345",
    "ticker": "META",
    "company": "Meta Platforms",
    "analysis_date": "2024-10-03",
    "report": {/* full report JSON */},
    "valuation": {
        "fair_value": 650.0,
        "current_price": 580.0,
        "upside_pct": 12.1
    },
    "recommendation": "BUY",
    "conviction": "HIGH",
    "hypotheses": [
        "AI monetization drives 20%+ revenue growth",
        "Margin expansion to 45% by 2026"
    ],
    "outcomes": {
        "3mo": {"price": 620.0, "return_pct": 6.9, "validation": null},
        "6mo": {"price": 680.0, "return_pct": 17.2, "validation": "partial"},
        "1yr": {"price": 750.0, "return_pct": 29.3, "validation": "validated"},
        "3yr": {"price": null, "return_pct": null, "validation": null}
    },
    "metadata": {
        "pm_score": 84,
        "pm_grade": "B",
        "cost": 3.35,
        "iterations": 12,
        "model": "claude-sonnet-3-5"
    }
}
```

**Queries**:
- "Find companies similar to NVDA in 2020" (embedding search)
- "Show analyses where margin expansion thesis validated" (filter)
- "What did we get wrong about growth stocks in 2022?" (reflection)

### Collection 2: `personal_knowledge`
**Purpose**: Import Notion notes, investment memos, personal insights

**Schema**:
```python
{
    "id": "notion_page_12345",
    "source": "notion",
    "title": "Why SaaS Multiples Compressed in 2022",
    "content": "...",
    "tags": ["saas", "valuation", "macro"],
    "created": "2023-01-15",
    "updated": "2023-03-20",
    "metadata": {
        "author": "user",
        "type": "investment_memo"
    }
}
```

**Usage**:
- Pre-populate hypothesis generation with personal frameworks
- "I've written about this before - here's my prior thinking..."

### Collection 3: `trusted_sources`
**Purpose**: Curated expert content (SemiAnalysis, Damodaran, etc.)

**Schema**:
```python
{
    "id": "semianalysis_20240915",
    "source": "semianalysis",
    "author": "Dylan Patel",
    "title": "NVDA Hopper Demand Update",
    "content": "...",
    "published": "2024-09-15",
    "url": "https://...",
    "tags": ["nvda", "datacenter", "ai_infra"],
    "summary": "H200 demand exceeding supply, GB200 pre-orders strong"
}
```

**Sources** (prioritized):
1. SemiAnalysis (Dylan Patel) - Semiconductor/AI infrastructure
2. Stratechery (Ben Thompson) - Tech strategy
3. Damodaran Blog - Valuation frameworks
4. Not Boring (Packy McCormick) - Growth companies
5. NetInterest (Marc Rubinstein) - Finance/banking

### Implementation

```bash
# Install ChromaDB
pip install chromadb

# Create setup script
cat > scripts/setup_chromadb.py <<'EOF'
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./data/chromadb"
))

# Collection 1: Analysis Memory
analysis_memory = client.create_collection(
    name="analysis_memory",
    metadata={"description": "All investment analyses with outcomes"},
    embedding_function=chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),  # Use Claude embeddings
        model_name="claude-3-5-sonnet-20241022"
    )
)

# Collection 2: Personal Knowledge
personal_knowledge = client.create_collection(
    name="personal_knowledge",
    metadata={"description": "Notion notes and personal memos"}
)

# Collection 3: Trusted Sources
trusted_sources = client.create_collection(
    name="trusted_sources",
    metadata={"description": "Expert commentary from curated sources"}
)

print("✅ ChromaDB initialized with 3 collections")
EOF

python scripts/setup_chromadb.py
```

**Deliverable**: ChromaDB operational at `./data/chromadb` with 3 collections

---

## Deliverable 3: Baseline Metrics Tracking

**Purpose**: Establish current agent performance (58/100 → target 90/100)

### Metrics to Track

**Process Quality** (PM Evaluation):
- Average PM score across 30 test cases
- Grade distribution (A, A-, B+, B, B-, C+, C, etc.)
- Score by tier (easy vs medium vs hard)
- Consistency (std dev of scores)

**Output Quality**:
- Report completeness (% with all required sections)
- Scenario presence (% with bull/base/bear)
- Entry/exit conditions specificity
- Methodology depth (avg character count, keyword presence)

**Outcome Accuracy** (long-term, backfill):
- Directional accuracy (% correct up/down/flat)
- Correlation with returns (Spearman r)
- Calibration (predicted vs actual returns)
- Thesis validation rate (% of hypotheses that materialized)

**Cost & Efficiency**:
- Average cost per analysis
- Token usage by agent
- Runtime by phase
- Cache hit rate (when implemented)

### Implementation

```python
# src/investing_agents/evaluation/benchmark.py

from dataclasses import dataclass
from typing import List, Dict, Any
import json
from pathlib import Path

@dataclass
class BenchmarkResult:
    """Single test case result."""
    ticker: str
    tier: int
    pm_score: int
    pm_grade: str
    report_complete: bool
    has_scenarios: bool
    cost: float
    runtime_seconds: float
    timestamp: str

@dataclass
class BenchmarkSummary:
    """Aggregate metrics across all test cases."""
    total_cases: int
    avg_pm_score: float
    median_pm_score: float
    grade_distribution: Dict[str, int]
    tier_scores: Dict[int, float]  # {1: 92.5, 2: 78.3, 3: 64.2}
    avg_cost: float
    avg_runtime: float
    completeness_pct: float
    scenario_pct: float

def run_baseline_benchmark(test_cases: List[Dict[str, Any]]) -> BenchmarkSummary:
    """Run current agent on all test cases, return aggregate metrics."""
    results = []

    for case in test_cases:
        # Run analysis
        report = analyze_company(case["ticker"], case["snapshot_date"])

        # Evaluate
        pm_result = pm_evaluate(report)

        # Track result
        results.append(BenchmarkResult(
            ticker=case["ticker"],
            tier=case["tier"],
            pm_score=pm_result.score,
            pm_grade=pm_result.grade,
            report_complete=validate_report_structure(report).is_valid,
            has_scenarios=bool(report.get("valuation", {}).get("scenarios")),
            cost=calculate_cost(report),
            runtime_seconds=report["metadata"]["runtime"],
            timestamp=datetime.now().isoformat()
        ))

    # Aggregate
    return BenchmarkSummary(
        total_cases=len(results),
        avg_pm_score=statistics.mean(r.pm_score for r in results),
        median_pm_score=statistics.median(r.pm_score for r in results),
        grade_distribution=Counter(r.pm_grade for r in results),
        tier_scores={
            1: statistics.mean(r.pm_score for r in results if r.tier == 1),
            2: statistics.mean(r.pm_score for r in results if r.tier == 2),
            3: statistics.mean(r.pm_score for r in results if r.tier == 3),
        },
        avg_cost=statistics.mean(r.cost for r in results),
        avg_runtime=statistics.mean(r.runtime_seconds for r in results),
        completeness_pct=sum(r.report_complete for r in results) / len(results) * 100,
        scenario_pct=sum(r.has_scenarios for r in results) / len(results) * 100,
    )
```

**CLI**:
```bash
# Run baseline benchmark
investing-agents benchmark --corpus data/evaluation_corpus/manifest.json --output data/baseline_metrics.json

# Expected output:
# ================================================================================
# BASELINE BENCHMARK RESULTS
# ================================================================================
# Total Cases: 30
# Average PM Score: 58.3 (B-)
# Median PM Score: 60.0
#
# Grade Distribution:
#   A-: 0 (0%)
#   B+: 2 (7%)
#   B:  5 (17%)
#   B-: 12 (40%)
#   C+: 8 (27%)
#   C:  3 (10%)
#
# Scores by Tier:
#   Tier 1 (Easy): 72.5 (B-)
#   Tier 2 (Medium): 58.2 (B-)
#   Tier 3 (Hard): 44.1 (C+)
#
# Report Quality:
#   Completeness: 65% (structural validation passed)
#   Scenarios Present: 40% (missing in 60% of reports)
#
# Cost & Efficiency:
#   Average Cost: $3.35 per analysis
#   Average Runtime: 18.5 minutes
# ================================================================================
```

**Deliverable**: `data/baseline_metrics.json` with current agent performance

---

## Deliverable 4: Data Source Stack Finalized

**Purpose**: Ensure all data integrations working for Phase 1

### Current Stack (Operational)
✅ **SEC EDGAR Direct API** - Fundamentals
✅ **Yahoo Finance** - Real-time prices
✅ **Brave Search MCP** - Web research

### Phase 0 Additions
🔨 **SEC Filing Full-Text Parser** - Extract 10-K MD&A sections
🔨 **Trusted Source Scraper** - RSS/YouTube integration

### SEC Filing Parser

**Purpose**: Extract Management Discussion & Analysis (MD&A) from 10-Ks

```python
# src/investing_agents/connectors/sec_filing_parser.py

import re
from typing import Dict, Any, Optional

class SECFilingParser:
    """Parse SEC 10-K filings for structured data extraction."""

    def extract_mda(self, filing_text: str) -> Optional[str]:
        """Extract Item 7: Management's Discussion & Analysis.

        Returns:
            MD&A section text, or None if not found
        """
        # Item 7 pattern
        mda_pattern = r"Item\s+7\.?\s*Management'?s?\s+Discussion\s+and\s+Analysis(.*?)(?=Item\s+8|Item\s+7A)"

        match = re.search(mda_pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def extract_risk_factors(self, filing_text: str) -> Optional[str]:
        """Extract Item 1A: Risk Factors."""
        risk_pattern = r"Item\s+1A\.?\s*Risk\s+Factors(.*?)(?=Item\s+1B|Item\s+2)"

        match = re.search(risk_pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def parse_filing(self, filing_url: str) -> Dict[str, Any]:
        """Fetch and parse full 10-K filing.

        Args:
            filing_url: URL to SEC EDGAR filing

        Returns:
            Parsed filing with MD&A, risks, business description
        """
        # Fetch filing text
        response = httpx.get(filing_url)
        filing_text = response.text

        return {
            "mda": self.extract_mda(filing_text),
            "risk_factors": self.extract_risk_factors(filing_text),
            "business_description": self.extract_business_description(filing_text),
            "source_url": filing_url,
        }
```

**Test**:
```python
parser = SECFilingParser()
result = parser.parse_filing("https://www.sec.gov/cgi-bin/viewer?action=view&cik=1318605&accession_number=0001564590-24-000026&xbrl_type=v")

print(f"MD&A Length: {len(result['mda'])} characters")
print(f"Risk Factors: {len(result['risk_factors'])} characters")
```

### Trusted Source Scraper

**Purpose**: Daily scraping of expert content into ChromaDB

```python
# src/investing_agents/research/trusted_source_scraper.py

import feedparser
from datetime import datetime, timedelta

class TrustedSourceScraper:
    """Scrape RSS feeds and YouTube channels for expert content."""

    SOURCES = {
        "semianalysis": {
            "type": "substack",
            "rss": "https://semianalysis.substack.com/feed",
            "author": "Dylan Patel",
            "tags": ["semiconductors", "ai_infrastructure"],
        },
        "stratechery": {
            "type": "blog",
            "rss": "https://stratechery.com/feed/",
            "author": "Ben Thompson",
            "tags": ["tech_strategy", "platforms"],
        },
        "damodaran": {
            "type": "blog",
            "rss": "https://aswathdamodaran.blogspot.com/feeds/posts/default",
            "author": "Aswath Damodaran",
            "tags": ["valuation", "finance"],
        },
    }

    def scrape_all_sources(self, days_lookback: int = 7) -> List[Dict[str, Any]]:
        """Scrape all sources for recent content.

        Args:
            days_lookback: How many days of history to fetch

        Returns:
            List of articles with content, metadata, embeddings
        """
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        articles = []

        for source_id, config in self.SOURCES.items():
            feed = feedparser.parse(config["rss"])

            for entry in feed.entries:
                pub_date = datetime(*entry.published_parsed[:6])

                if pub_date >= cutoff_date:
                    articles.append({
                        "id": f"{source_id}_{entry.id}",
                        "source": source_id,
                        "author": config["author"],
                        "title": entry.title,
                        "content": entry.summary,  # or entry.content
                        "published": pub_date.isoformat(),
                        "url": entry.link,
                        "tags": config["tags"],
                    })

        return articles

    def store_to_chromadb(self, articles: List[Dict[str, Any]]):
        """Store articles in ChromaDB trusted_sources collection."""
        collection = chromadb_client.get_collection("trusted_sources")

        collection.add(
            documents=[a["content"] for a in articles],
            metadatas=[{k: v for k, v in a.items() if k != "content"} for a in articles],
            ids=[a["id"] for a in articles],
        )

        print(f"✅ Stored {len(articles)} articles to ChromaDB")
```

**Cron Job** (daily scraping):
```bash
# scripts/daily_scrape.sh
#!/bin/bash
source .venv/bin/activate
python -m investing_agents.research.trusted_source_scraper --days 1
```

**Deliverable**: SEC parser + Trusted source scraper operational

---

## Implementation Timeline

### Week 1 (Oct 3-10)

**Days 1-2**: Test Case Corpus
- [ ] Define 30 companies (10 per tier)
- [ ] Create manifest.json with 120 snapshots
- [ ] Validate data availability for all snapshots

**Days 3-4**: ChromaDB Setup
- [ ] Install ChromaDB
- [ ] Create 3 collections
- [ ] Test embedding + retrieval
- [ ] Import seed data (10 sample analyses)

**Days 5-7**: Baseline Benchmark
- [ ] Implement benchmark.py
- [ ] Run current agent on 30 test cases (may take 10-15 hours)
- [ ] Generate baseline_metrics.json
- [ ] Analyze results, document findings

### Week 2 (Oct 11-17)

**Days 8-10**: Data Source Stack
- [ ] Build SEC filing parser
- [ ] Test on 10 sample filings
- [ ] Build trusted source scraper
- [ ] Backfill 6 months of expert content

**Days 11-12**: Integration Testing
- [ ] Test ChromaDB queries in hypothesis generation
- [ ] Test SEC parser in financial analysis
- [ ] Test trusted source retrieval

**Days 13-14**: Documentation & Validation
- [ ] Document Phase 0 completion
- [ ] Run validation tests
- [ ] Prepare Phase 1 kickoff

---

## Success Metrics

**At Phase 0 Completion**:
- ✅ 30 test cases defined and validated
- ✅ ChromaDB operational with sample data
- ✅ Baseline metrics: Current agent = 58/100 (B-) documented
- ✅ SEC parser extracting MD&A successfully
- ✅ Trusted source scraper fetching expert content
- ✅ All tests passing: `pytest tests/test_phase0_readiness.py`

**Validation Command**:
```bash
pytest tests/test_phase0_readiness.py

# Expected output:
# ✅ 30 test cases loaded from manifest.json
# ✅ ChromaDB operational (3 collections)
# ✅ Baseline metrics: 58/100 average across 30 cases
# ✅ Data sources: SEC EDGAR + Yahoo + Brave + SEC Parser + Trusted Sources
# ✅ SEC parser: 10-K MD&A extraction functional (100% success on test filings)
# ============================= 10 passed in 5.2s ==============================
```

---

## Next Steps: Phase 1

After Phase 0 validation, proceed to Phase 1 with confidence:
1. **Scenario DCF**: Extend ginzu.py for bull/base/bear
2. **Backtesting Framework**: Run frozen fundamentals analysis
3. **Memory-Enhanced Hypotheses**: Query ChromaDB before generating
4. **Trusted Source Integration**: Surface expert insights

**Target**: 58 → 90 (A-) in 10-12 weeks

---

**Document Version**: 1.0
**Created**: October 3, 2025
**Status**: ✅ Plan Complete, Implementation Starting
