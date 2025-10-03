# Memory System Architecture

**Version**: 2.0
**Date**: 2025-10-02
**Status**: Design Specification

---

## Overview

Enhanced multi-source memory system combining:
1. **Analysis Memory**: Past analyses with tracked outcomes
2. **Personal Knowledge Base**: Your Notion notes and insights
3. **Trusted Sources**: Curated expert content (SemiAnalysis, Dylan Patel, etc.)

All queryable via vector similarity search + structured metadata retrieval.

---

## Architecture Design

### Three-Layer Memory Model

```
┌─────────────────────────────────────────────────────────────┐
│                  Memory Query Interface                      │
│            (Unified similarity search + filters)             │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Analysis   │    │   Personal   │    │   Trusted    │
│    Memory    │    │   Knowledge  │    │   Sources    │
│  (ChromaDB)  │    │  (ChromaDB)  │    │  (ChromaDB)  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 1. Analysis Memory (Existing + Enhanced)

**Purpose**: Store every analysis with outcomes for pattern recognition.

**Schema**:
```python
{
    "analysis_id": "NVDA_20251002_abc123",
    "ticker": "NVDA",
    "company": "NVIDIA Corporation",
    "date_analyzed": "2025-10-02",

    # Analysis content
    "hypotheses": [
        {"id": "h1", "title": "...", "confidence": 0.85, ...},
        ...
    ],
    "fair_value": 150.00,
    "recommendation": "BUY",
    "conviction": "HIGH",

    # Outcomes (filled in over time)
    "outcome_3mo": {
        "stock_return": 0.12,
        "hypothesis_validation": {"h1": True, "h2": False, ...},
        "prediction_accuracy": 0.75
    },
    "outcome_6mo": {...},
    "outcome_1yr": {...},
    "outcome_3yr": {...},

    # Lessons learned (from reflection)
    "lessons_learned": [
        "Data center demand was underestimated - check supply chain signals earlier",
        "Margin compression thesis was wrong - economies of scale dominated",
        ...
    ],

    # Metadata for filtering
    "metadata": {
        "sector": "Technology",
        "market_cap": "3.5T",
        "growth_profile": "high_growth",
        "margin_profile": "high_margin",
        "tags": ["AI", "semiconductors", "data_center"]
    }
}
```

**Storage**: ChromaDB collection `analysis_memory`

**Indexing**:
- Vector embedding of hypotheses + evidence summary
- Metadata filters: sector, market_cap, growth_profile, tags

---

### 2. Personal Knowledge Base (NEW)

**Purpose**: Import your Notion notes, insights, and company understanding.

**Data Sources**:
1. Notion exports (Markdown format)
2. Manual notes (structured text)
3. Custom insights and mental models

**Schema**:
```python
{
    "note_id": "notion_nvda_supply_chain_2025",
    "source": "notion",
    "ticker": "NVDA",  # Optional - can be multi-company or thematic
    "title": "NVIDIA Supply Chain Dynamics - My Understanding",
    "content": "...",  # Full markdown content

    # Structured insights (extracted or manually tagged)
    "insights": [
        {
            "topic": "supply_chain",
            "claim": "TSMC 3nm capacity is the real bottleneck, not NVIDIA's design",
            "confidence": "high",
            "date_observed": "2025-09-15",
            "supporting_sources": ["SemiAnalysis Oct 2024", "Dylan Patel interview"]
        },
        ...
    ],

    # Metadata
    "metadata": {
        "created_at": "2025-09-15",
        "updated_at": "2025-10-01",
        "tags": ["NVDA", "supply_chain", "TSMC", "manufacturing"],
        "importance": "high",  # high/medium/low
        "note_type": "company_deep_dive"  # Types: company_deep_dive, theme, mental_model, observation
    }
}
```

**Storage**: ChromaDB collection `personal_knowledge`

**Update Workflow**:
1. Export Notion notes to Markdown (manual or automated)
2. Parse Markdown → extract insights
3. Store in ChromaDB with metadata
4. Flag for agent attention: "New insights available for NVDA"

**Integration Points**:
- HypothesisGenerator: Query personal knowledge for company context before generating hypotheses
- DeepResearch: Cross-reference findings with your prior understanding
- NarrativeBuilder: Include your unique insights in reports (attributed)

---

### 3. Trusted Sources Memory (NEW)

**Purpose**: Continuously monitor and index content from expert sources.

**Curated Sources** (Initial List):
- **SemiAnalysis** (Dylan Patel): Semiconductor analysis
- **Dylan Patel Podcasts/YouTube**: Interviews and deep dives
- **Aswath Damodaran Blog**: Valuation frameworks
- **Stratechery** (Ben Thompson): Tech business models
- **ARK Invest Research**: Innovation trends
- _(Expandable list)_

**Schema**:
```python
{
    "source_id": "semianalysis_nvda_blackwell_20250915",
    "source": "SemiAnalysis",
    "author": "Dylan Patel",
    "url": "https://semianalysis.com/...",
    "title": "NVIDIA Blackwell Yields and Supply Chain Analysis",
    "published_date": "2025-09-15",
    "content": "...",  # Full article text

    # Extracted insights
    "key_insights": [
        {
            "topic": "manufacturing",
            "claim": "Blackwell yields improved from 60% to 85% in Q3",
            "evidence": "Supply chain checks with TSMC partners",
            "confidence": "high",
            "relevance_to": ["NVDA", "TSM"]
        },
        ...
    ],

    # Metadata
    "metadata": {
        "source_type": "expert_analysis",
        "credibility": "high",  # Based on track record
        "tickers_mentioned": ["NVDA", "TSM", "AMD"],
        "topics": ["semiconductors", "AI", "manufacturing"],
        "content_type": "deep_dive"  # Types: deep_dive, news, interview, research
    }
}
```

**Storage**: ChromaDB collection `trusted_sources`

**Ingestion Workflow** (Automated Agent):
1. **Monitor Sources**: RSS feeds, YouTube channels, website scraping
2. **Content Extraction**: Fetch full text, clean HTML, extract metadata
3. **Insight Extraction**: LLM extracts key claims, evidence, relevance
4. **Store in Memory**: ChromaDB with rich metadata
5. **Alert on Relevance**: "New SemiAnalysis article on NVDA - 3 new insights"

**Scraping Agent Specification** (see below)

---

## Unified Query Interface

**Purpose**: Query across all three memory layers with a single interface.

```python
class UnifiedMemorySystem:
    """Query interface for all memory layers."""

    def __init__(self):
        self.analysis_memory = ChromaDB(collection="analysis_memory")
        self.personal_knowledge = ChromaDB(collection="personal_knowledge")
        self.trusted_sources = ChromaDB(collection="trusted_sources")

    def query(
        self,
        query: str,
        filters: Optional[Dict] = None,
        sources: List[str] = ["analysis", "personal", "trusted"],
        n_results: int = 10
    ) -> Dict[str, List[Dict]]:
        """Query across specified memory sources.

        Args:
            query: Natural language query or embedding
            filters: Metadata filters (ticker, sector, tags, date_range, etc.)
            sources: Which memory layers to query
            n_results: Top N results per source

        Returns:
            {
                "analysis": [...],
                "personal": [...],
                "trusted": [...]
            }
        """
        results = {}

        if "analysis" in sources:
            results["analysis"] = self.analysis_memory.query(
                query_texts=[query],
                where=filters,
                n_results=n_results
            )

        if "personal" in sources:
            results["personal"] = self.personal_knowledge.query(
                query_texts=[query],
                where=filters,
                n_results=n_results
            )

        if "trusted" in sources:
            results["trusted"] = self.trusted_sources.query(
                query_texts=[query],
                where=filters,
                n_results=n_results
            )

        return results

    def get_company_context(self, ticker: str) -> Dict:
        """Get all relevant context for a company across all sources.

        Returns:
            {
                "past_analyses": [...],  # Previous analyses of this ticker
                "personal_insights": [...],  # Your notes on this company
                "expert_insights": [...],  # Recent expert commentary
                "related_patterns": [...]  # Similar companies from memory
            }
        """
        return {
            "past_analyses": self.analysis_memory.query(
                where={"ticker": ticker},
                n_results=5
            ),
            "personal_insights": self.personal_knowledge.query(
                where={"ticker": ticker},
                n_results=10
            ),
            "expert_insights": self.trusted_sources.query(
                where={"tickers_mentioned": {"$contains": ticker}},
                n_results=10,
                order_by="published_date DESC"
            ),
            "related_patterns": self._find_similar_companies(ticker)
        }
```

---

## Integration with Agents

### HypothesisGeneratorAgent Enhancement

**Before** (baseline):
```python
hypotheses = await self.hypothesis_agent.generate(
    company=company_name,
    ticker=ticker,
    context={"sector": "Technology"}  # Minimal context
)
```

**After** (memory-enhanced):
```python
# 1. Query memory for company context
memory_context = self.memory.get_company_context(ticker)

# 2. Enrich context with personal insights + expert insights
enriched_context = {
    "sector": "Technology",
    "your_prior_understanding": memory_context["personal_insights"][:5],
    "recent_expert_insights": memory_context["expert_insights"][:5],
    "similar_companies_analyzed": memory_context["related_patterns"][:3],
    "past_hypotheses_tested": [
        h for analysis in memory_context["past_analyses"]
        for h in analysis["hypotheses"]
    ][:5]
}

# 3. Generate hypotheses with enriched context
hypotheses = await self.hypothesis_agent.generate(
    company=company_name,
    ticker=ticker,
    context=enriched_context
)
```

**Impact**: Hypotheses are informed by:
- Your prior thinking (avoid duplicating insights you already have)
- Expert perspectives (build on Dylan Patel's analysis, don't ignore it)
- Past patterns (learn from similar companies)

---

### DeepResearchAgent Enhancement

**Before**: Research from scratch using SEC filings + web search

**After**: Cross-reference with memory before deep research

```python
# 1. Check what you already know
prior_knowledge = self.memory.query(
    query=hypothesis["title"],
    filters={"ticker": ticker},
    sources=["personal", "trusted"],
    n_results=5
)

# 2. If high-quality prior knowledge exists, use it
if prior_knowledge["personal"] or prior_knowledge["trusted"]:
    evidence.append({
        "source": "prior_knowledge",
        "claims": prior_knowledge,
        "confidence": "high",
        "note": "From your personal notes or trusted expert sources"
    })

# 3. Focus research on gaps
research_focus = [
    question for question in hypothesis["evidence_needed"]
    if question not in prior_knowledge  # Don't re-research what you know
]
```

**Impact**:
- Avoid redundant research (you already analyzed NVDA's supply chain)
- Surface contradictions (expert said X, but SEC filing shows Y)
- Build on existing knowledge rather than starting from zero

---

### NarrativeBuilderAgent Enhancement

**Insight Attribution**:

When personal insights or expert insights are used, attribute them:

```markdown
## Competitive Moat

NVIDIA's supply chain bottleneck is TSMC 3nm capacity, not internal design
constraints [personal insight: 2025-09-15]. This aligns with recent SemiAnalysis
research showing yields improved from 60% to 85% in Q3 [SemiAnalysis, Sep 2025].
```

---

## Trusted Source Scraping Agent

### Design Specification

**Agent**: `TrustedSourceScraperAgent`

**Responsibilities**:
1. Monitor RSS feeds / YouTube channels / website updates
2. Fetch new content when published
3. Extract insights using LLM
4. Store in trusted_sources memory
5. Alert analysts to relevant updates

**Implementation**:

```python
class TrustedSourceScraperAgent:
    """Automated agent for monitoring and indexing trusted sources."""

    SOURCES = {
        "semianalysis": {
            "url": "https://semianalysis.com/feed",
            "type": "rss",
            "credibility": "high",
            "topics": ["semiconductors", "AI", "supply_chain"]
        },
        "dylan_patel_youtube": {
            "url": "https://www.youtube.com/@SemiAnalysis/videos",
            "type": "youtube_channel",
            "credibility": "high",
            "topics": ["semiconductors", "AI"]
        },
        "damodaran_blog": {
            "url": "https://aswathdamodaran.blogspot.com/feeds/posts/default",
            "type": "rss",
            "credibility": "high",
            "topics": ["valuation", "investing"]
        },
        # Add more sources...
    }

    async def monitor_all_sources(self):
        """Check all sources for new content (run daily)."""
        for source_name, config in self.SOURCES.items():
            new_items = await self._check_for_updates(source_name, config)

            for item in new_items:
                # Extract and store
                insights = await self._extract_insights(item)
                await self.memory.trusted_sources.add(insights)

                # Alert if high relevance
                if insights["metadata"]["importance"] == "high":
                    self._alert_user(f"New {source_name} article: {item['title']}")

    async def _extract_insights(self, content: Dict) -> Dict:
        """Use LLM to extract key insights from content."""

        prompt = f"""Analyze this article and extract key investment insights.

ARTICLE: {content['title']}
URL: {content['url']}
CONTENT: {content['text']}

Extract:
1. Key claims (what is being argued?)
2. Evidence provided (how is it supported?)
3. Tickers mentioned (which companies are discussed?)
4. Topics (semiconductors, AI, valuation, etc.)
5. Actionable insights (what should investors do with this?)

Return structured JSON."""

        result = await query(prompt, options=ClaudeAgentOptions(max_turns=1))
        return self._parse_insights(result)
```

**Deployment**:
- Run as cron job (daily at 8am)
- Store new content in `trusted_sources` memory
- Send digest of new insights via email/Slack

---

## Notion Integration Workflow

### Export from Notion

**Manual Process** (Phase 1):
1. Export Notion workspace → Markdown & CSV
2. Place in `data/notion_exports/YYYY-MM-DD/`
3. Run import script: `python scripts/import_notion.py --date 2025-10-02`

**Automated Process** (Phase 2):
- Use Notion API to sync automatically (daily)
- Detect changes → update ChromaDB incrementally
- Track version history

### Import Script

```python
# scripts/import_notion.py
import argparse
from pathlib import Path
import frontmatter
from investing_agents.core.memory import UnifiedMemorySystem

def import_notion_export(export_dir: Path, memory: UnifiedMemorySystem):
    """Import Notion markdown exports into personal_knowledge memory."""

    markdown_files = export_dir.glob("**/*.md")

    for md_file in markdown_files:
        # Parse markdown with frontmatter
        with open(md_file) as f:
            post = frontmatter.load(f)

        # Extract metadata
        metadata = post.metadata
        content = post.content

        # Extract insights (simple heuristic or LLM-based)
        insights = extract_insights_from_markdown(content)

        # Store in memory
        memory.personal_knowledge.add({
            "note_id": f"notion_{md_file.stem}",
            "source": "notion",
            "ticker": metadata.get("ticker"),
            "title": metadata.get("title", md_file.stem),
            "content": content,
            "insights": insights,
            "metadata": {
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "tags": metadata.get("tags", []),
                "importance": metadata.get("importance", "medium"),
            }
        })

    print(f"Imported {len(list(markdown_files))} notes from Notion")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    export_dir = Path(f"data/notion_exports/{args.date}")
    memory = UnifiedMemorySystem()
    import_notion_export(export_dir, memory)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Week 1:**
- [ ] Set up ChromaDB with three collections (analysis_memory, personal_knowledge, trusted_sources)
- [ ] Implement `UnifiedMemorySystem` class
- [ ] Basic schema and indexing

**Week 2:**
- [ ] Build Notion import script
- [ ] Manual import of existing notes (test with 5-10 notes)
- [ ] Validate query interface works

### Phase 2: Trusted Sources (Week 3-4)

**Week 3:**
- [ ] Build `TrustedSourceScraperAgent`
- [ ] RSS integration (SemiAnalysis, Damodaran)
- [ ] YouTube integration (Dylan Patel channel)
- [ ] Test insight extraction

**Week 4:**
- [ ] Automated daily scraping
- [ ] Alert system for high-relevance content
- [ ] Backfill historical content (last 6 months)

### Phase 3: Agent Integration (Week 5-6)

**Week 5:**
- [ ] Enhance HypothesisGenerator with memory context
- [ ] Enhance DeepResearch with prior knowledge checks

**Week 6:**
- [ ] Enhance NarrativeBuilder with insight attribution
- [ ] Test end-to-end: Run NVDA analysis with full memory system
- [ ] Measure impact vs baseline

---

## Success Metrics

**Quantitative**:
- Memory query latency < 500ms
- Personal knowledge coverage: 20+ companies with deep notes
- Trusted sources: 100+ articles indexed per month
- Agent enhancement: +15 points to overall score (from 58 → 73)

**Qualitative**:
- Hypotheses reference your prior insights (attribution visible)
- Research doesn't duplicate what you already know
- Reports integrate expert perspectives (SemiAnalysis, Damodaran)
- "I've seen this before" insights appear in analysis

---

## Technical Stack

**Core**:
- ChromaDB (vector database)
- LangChain or LlamaIndex (optional, for advanced RAG)
- Anthropic Claude (for insight extraction)

**Data Ingestion**:
- feedparser (RSS)
- youtube-transcript-api (YouTube)
- BeautifulSoup (web scraping)
- notion-client (Notion API, Phase 2)

**Storage**:
- ChromaDB persisted to disk: `data/memory/chromadb/`
- Backups: Daily snapshot to S3 or equivalent

---

## Security & Privacy

**Considerations**:
- Personal knowledge may contain sensitive insights (proprietary thinking)
- Store locally (not cloud-synced) unless encrypted
- Access control: Only you can query personal_knowledge
- Trusted sources: Public data, safe to share

**Best Practices**:
- Encrypt ChromaDB database at rest
- API keys in environment variables
- No PII in memory (company-focused only)

---

## Future Enhancements

**Advanced Features** (Post Phase 3):
1. **Multi-modal Memory**: Store charts, images, PDFs (not just text)
2. **Temporal Reasoning**: "What was Dylan Patel saying about NVDA in 2023 vs now?"
3. **Conflict Detection**: Alert when expert views diverge from your analysis
4. **Knowledge Graph**: Link entities (NVDA → TSMC → supply chain → China risk)
5. **Collaborative Memory**: Share insights with team (if multi-user)

---

**Document Version**: 2.0
**Last Updated**: 2025-10-02
**Next Review**: After Phase 1 implementation (Week 2)
