# Competitive Analysis Process

**Version**: 1.0
**Date**: 2025-10-02
**Purpose**: Standardized workflow for analyzing alternative approaches and incorporating insights into roadmap

---

## Overview

As we hill-climb toward 90/100 capability, we regularly research alternative systems (GitHub repos, papers, commercial products) to extract best practices and avoid reinventing inferior solutions.

**Goals**:
1. Learn from others' technical decisions
2. Identify gaps in our current approach
3. Validate or challenge our architectural choices
4. Accelerate development by adopting proven patterns

---

## When to Conduct Competitive Analysis

### Trigger Conditions

**Quarterly Reviews** (Minimum):
- Q1, Q2, Q3, Q4: Survey landscape for new approaches

**Before Major Architectural Changes**:
- Adding new agent types (e.g., ContrarianAgent, ManagementQualityAgent)
- Changing core workflows (e.g., synthesis pattern, memory system)
- Adopting new frameworks or dependencies

**When Stuck on Hard Problems**:
- Cost optimization challenges
- Context management issues
- Agent coordination patterns
- Data acquisition strategies

**After Discovering Relevant Work**:
- New paper published (arXiv, conferences)
- Popular GitHub repo in similar space
- Commercial product announcement

---

## Analysis Process (5 Steps)

### Step 1: Scope Definition (30 minutes)

**Define what you're researching and why.**

Template:
```markdown
## Analysis Scope

**Target System**: [Name of framework/product]
**URL**: [GitHub/Paper/Website]
**Date Discovered**: YYYY-MM-DD
**Reason for Analysis**: [Why are we looking at this?]

**Key Questions**:
1. [Specific question about their approach]
2. [Another question]
3. ...

**Success Criteria**: What insights would make this analysis worthwhile?
```

**Example** (TradingAgents):
```markdown
## Analysis Scope

**Target System**: TradingAgents
**URL**: https://github.com/TauricResearch/TradingAgents
**Date Discovered**: 2025-10-02
**Reason for Analysis**: Multi-agent trading framework - want to compare agent architecture

**Key Questions**:
1. How do they coordinate multiple agents?
2. Do they have memory/learning systems?
3. What's their cost optimization strategy?

**Success Criteria**: Find at least 2 actionable improvements for our system.
```

---

### Step 2: Deep Research (2-4 hours)

**Use the competitor-alternatives-researcher agent** for thorough analysis.

```bash
# Launch specialized research agent
/agents  # Creates competitor-alternatives-researcher if needed

# Then provide detailed research prompt
```

**Research Checklist**:
- [ ] Read GitHub repository code (architecture, agents, coordination)
- [ ] Read paper(s) for conceptual framework
- [ ] Check issues/discussions for known problems
- [ ] Look for evaluation metrics or benchmarks
- [ ] Identify production-ready vs research prototype components
- [ ] Extract specific technical details (code patterns, algorithms)

**Deliverable**: Comprehensive markdown report (see template below)

---

### Step 3: Critical Synthesis (1 hour)

**Answer these questions explicitly:**

1. **What do they do better than us?**
   - Specific technical advantages
   - Proven at scale or theoretical?
   - Implementation complexity estimate

2. **What do we do better than them?**
   - Our architectural advantages
   - Why our approach is superior for our use case

3. **What should we adopt?**
   - Top 5 actionable insights (prioritized)
   - ROI estimate (how many points toward 90/100 goal)
   - Implementation effort (LOW/MED/HIGH)

4. **What should we avoid?**
   - Their approaches we should NOT copy
   - Reasoning for why our way is better

5. **Net assessment**
   - Overall: Is this system ahead, behind, or different?
   - Key takeaway in one sentence

---

### Step 4: Documentation (30 minutes)

**Save analysis report to standardized location:**

```
docs/competitive_analysis/
├── PROCESS.md (this file)
├── YYYY-MM-DD_[framework-name].md
└── YYYY-MM-DD_[another-framework].md
```

**Naming Convention**:
- `2025-10-02_TradingAgents.md`
- `2025-10-15_LangGraph.md`
- `2025-11-01_AutoGPT.md`

**Required Sections** (see template below):
1. Metadata (date, URL, reason for analysis)
2. Executive Summary
3. Detailed Architecture Comparison
4. Actionable Insights (prioritized)
5. Things to Avoid
6. Gap Analysis
7. Integration Roadmap (if adopting)

---

### Step 5: Roadmap Integration (1 hour)

**Update strategic documents:**

1. **VALUATION_AI_FRONTIER.md**:
   - Add insights to relevant sections (e.g., Phase 1 if data-related)
   - Update 6-factor model projections if significant
   - Cite competitive analysis as reference

2. **IMPLEMENTATION_ROADMAP.md** (if exists):
   - Add specific action items with timeline
   - Estimate resource requirements
   - Prioritize against existing roadmap

3. **CLAUDE.md**:
   - Update architectural principles if changed
   - Add new patterns to "Common Patterns" section
   - Reference analysis in relevant sections

**Create GitHub Issues** (if actionable):
```
Title: [From TradingAgents] Implement memory-based learning system
Labels: enhancement, competitive-insight
Priority: High
Estimated Effort: 2 weeks

Description:
Based on competitive analysis of TradingAgents (docs/competitive_analysis/2025-10-02_TradingAgents.md),
implement ChromaDB-based memory system for agents.

**Why**: +10 points toward 90/100 goal (Learning & Adaptation factor)
**What**: See Section 3.1 of analysis doc
**Acceptance Criteria**: [...]
```

---

## Analysis Report Template

**File**: `docs/competitive_analysis/YYYY-MM-DD_[Framework].md`

```markdown
# Competitive Analysis: [Framework Name]

**Date**: YYYY-MM-DD
**Analyzed By**: [Your name or "Claude Code"]
**Status**: [Draft / Final / Integrated into Roadmap]

---

## Metadata

**Target System**: [Name]
**Primary URL**: [GitHub/Paper/Website]
**Additional Resources**:
- Paper: [Link if exists]
- Demo: [Link if exists]
- Documentation: [Link]

**Reason for Analysis**: [Why we're looking at this - 1-2 sentences]

**Key Questions**:
1. [Question 1]
2. [Question 2]
3. ...

---

## Executive Summary (2-3 paragraphs)

[High-level comparison: What they do, how it differs from us, key takeaways]

**Key Strengths to Consider**:
- [Strength 1]
- [Strength 2]

**Key Weaknesses to Avoid**:
- [Weakness 1]
- [Weakness 2]

**Net Assessment**: [One sentence - Are they ahead/behind/different? What's the key insight?]

---

## Detailed Architecture Comparison

### 1. Agent Architecture

**Their Approach**:
[Description with code snippets if relevant]

**Our Approach**:
[Description]

**Comparison**:
- Strengths: [What they do better]
- Weaknesses: [What we do better]
- Neutral: [Different but not better/worse]

### 2. Data Pipeline

[Same structure as above]

### 3. Coordination Patterns

[Same structure]

### 4. Memory & Learning

[Same structure]

### 5. Cost Optimization

[Same structure]

### 6. Output Quality

[Same structure]

---

## Actionable Insights (Prioritized)

### 1. [Insight Title] - **Priority: HIGH/MED/LOW**

**What**: [Specific technical detail to adopt]

**Why**: [How this helps us reach 90/100 goal]

**Impact**: [ROI estimate - how many points this adds]

**Implementation**:
- Effort: [LOW/MED/HIGH - time estimate]
- Dependencies: [What needs to exist first]
- Integration Points: [Which agents/modules to modify]

**Code Example** (if applicable):
```python
# Example implementation
```

---

### 2. [Next Insight]

[Same structure]

---

## Things to Avoid

### 1. [Anti-pattern or approach to NOT adopt]

**What they do**:
[Description]

**Why we should avoid**:
[Reasoning - why our approach is better for our use case]

---

## Gap Analysis

### What They Have That We Lack (Prioritized)

| Capability | Their Score | Our Score | Gap | Adoptable? | Priority |
|------------|-------------|-----------|-----|------------|----------|
| Memory-based learning | 80 | 5 | 75 | Yes | High |
| Insider sentiment | 70 | 0 | 70 | Yes | Medium |
| ... | ... | ... | ... | ... | ... |

### What We Have That They Lack (Our Advantages)

| Capability | Our Score | Their Score | Advantage | Defensible? |
|------------|-----------|-------------|-----------|-------------|
| Deterministic DCF | 95 | 0 | 95 | Yes |
| Institutional reports | 90 | 20 | 70 | Yes |
| ... | ... | ... | ... | ... |

### Neutral Differences

| Aspect | Their Approach | Our Approach | Comment |
|--------|----------------|--------------|---------|
| Model choice | GPT-4 | Claude Sonnet | Both viable |
| ... | ... | ... | ... |

---

## Integration Roadmap (If Adopting Insights)

### Phase 1: Foundation (Week 1-2)
- [ ] Task 1
- [ ] Task 2

### Phase 2: Implementation (Week 3-4)
- [ ] Task 1
- [ ] Task 2

### Phase 3: Validation (Week 5-6)
- [ ] Task 1
- [ ] Task 2

**Expected Impact**: [Quantified improvement - e.g., "58 → 68, +10 points"]

**Success Metrics**:
- [ ] Metric 1
- [ ] Metric 2

---

## References

**Original Materials**:
- [Link 1: GitHub repo]
- [Link 2: Paper]
- [Link 3: Documentation]

**Related Analyses**:
- [Link to previous competitive analysis if relevant]

**Code Examples Extracted**:
- [Link to relevant code in their repo]

---

## Appendix: Detailed Technical Notes

[Any additional technical details, code snippets, architecture diagrams, etc.]

---

**Document Version**: 1.0
**Last Updated**: YYYY-MM-DD
**Integration Status**: [Not Started / In Progress / Completed]
```

---

## Tools & Automation

### Using the competitor-alternatives-researcher Agent

**Purpose**: Automate deep technical research of alternative systems.

**How to Use**:

1. **Create/verify agent exists**:
   ```bash
   /agents  # Creates competitor-alternatives-researcher if needed
   ```

2. **Provide detailed research prompt**:
   ```
   Research [Framework Name] and compare to our investing-agents system.

   URLs: [GitHub, Paper, etc.]

   Focus on:
   1. Agent architecture comparison
   2. Memory/learning systems
   3. Cost optimization strategies
   4. Novel techniques we don't have

   Deliverable: Comprehensive markdown report with actionable insights.
   ```

3. **Agent produces**:
   - Detailed technical analysis
   - Code snippets and examples
   - Prioritized recommendations
   - Report saved to `docs/competitive_analysis/`

### Maintaining a Research Queue

**File**: `docs/competitive_analysis/QUEUE.md`

```markdown
# Competitive Analysis Queue

## Planned Analyses

### Q4 2025
- [ ] LangGraph (agent orchestration patterns)
- [ ] AutoGPT (autonomous agents)
- [ ] Cognition AI (commercial investment AI)

### Q1 2026
- [ ] Bloomberg GPT (financial LLMs)
- [ ] AlphaResearch (AI stock research)
- [ ] ...

## Completed
- [x] 2025-10-02: TradingAgents - Memory systems, insider sentiment
```

---

## Integration with Main Roadmap

### Before Adding to Roadmap

**Validation Questions**:
1. Does this align with our North Star (90/100 capability)?
2. What's the ROI (points added vs effort required)?
3. Does this conflict with existing architecture?
4. Is there a proof-of-concept we can test first?

### Adding to VALUATION_AI_FRONTIER.md

**Example Integration**:

```markdown
## Phase 1: Data Moat (Months 1-3)

### 1.1 ManagementQualityAgent

**Enhanced Scope** (from TradingAgents analysis 2025-10-02):
- SEC Form 4 insider ownership
- Promise vs delivery tracker
- **NEW: FinnHub insider sentiment API**
  - Monthly share purchase ratios
  - Source: Competitive analysis showed this is a strong signal
  - Effort: 2-3 days
  - ROI: +5 points
```

### Creating GitHub Issues

**Template**:
```
Title: [Competitive Insight] [Brief description]

Labels: enhancement, competitive-analysis, priority-[high/med/low]

**Source**: docs/competitive_analysis/YYYY-MM-DD_[Framework].md (Section X.Y)

**Context**: [Why this matters for our 90/100 goal]

**Proposal**: [What to implement]

**Implementation Plan**:
- [ ] Step 1
- [ ] Step 2

**Success Criteria**: [How we'll know it works]

**Estimated Effort**: [X weeks]
**Expected Impact**: [+Y points toward 90/100]
```

---

## Success Metrics for This Process

**Quantitative**:
- Conduct ≥1 competitive analysis per month
- Adopt ≥2 actionable insights per quarter
- Document ≥80% of analyses using this template

**Qualitative**:
- Insights demonstrably improve our capability score
- Roadmap reflects latest industry best practices
- Avoid reimplementing inferior solutions

---

## Review & Iteration

**Quarterly Review** (Q1, Q2, Q3, Q4):
- Review all competitive analyses conducted
- Measure impact of adopted insights (A/B test against baseline)
- Update this process based on lessons learned

**Questions to Ask**:
1. Did we miss any major competitive developments?
2. Did adopted insights deliver expected ROI?
3. Should we adjust research priorities?

---

**Document Version**: 1.0
**Last Updated**: 2025-10-02
**Next Review**: Q1 2026 (January 2026)
