# Business Viability Assessment

**Date**: October 3, 2025
**Status**: Strategic Discussion - Tabled for Future
**Focus**: Replacing Junior Analyst Route

---

## Executive Summary

**Question**: Is this a business or a hobby?

**Answer**: Currently a **sophisticated hobby/personal tool**. After Phase 0+1 completion (10 weeks), could become a **viable small business** targeting the "junior analyst replacement" market.

**Strategic Direction**: Focus on **Small RIAs/Family Offices** segment - too big for DIY, too small for Bloomberg.

---

## Market Segment Analysis

### Target Customer: Small RIAs & Family Offices

**Profile**:
- Managing $10M-500M AUM
- 1-5 investment professionals
- Currently spending $80-150k/yr on junior analyst OR $2-5k/mo on outsourced research
- Too small for Bloomberg Terminal ($24k/seat)
- Too sophisticated for retail tools (Seeking Alpha, Motley Fool)

**Current Pain Points**:
1. Junior analysts expensive and slow (days for deep research)
2. Outsourced research lacks customization
3. Bloomberg overkill for their needs
4. Time-intensive to maintain research quality

**What They Need**:
- ✅ Institutional-grade reports (we're at B-level, targeting A-)
- ✅ Audit trail for compliance (we have)
- ✅ Fast turnaround (we have: 20min vs days)
- ✅ Deterministic valuation (we have: NumPy DCF)
- ❌ **Proven track record** (Gap: need backtesting results)
- ❌ **Consistent A-level quality** (Gap: currently B/84, need A-/90)
- ⚠️ White-label reports (could add easily)

**Willingness to Pay**: $500-2000/mo if we replace junior analyst workload

**Value Proposition**:
> "Replace your $150k junior analyst with $24k/yr AI that delivers institutional-grade equity research in 20 minutes, not 3 days"

---

## Business Model Economics

### Revenue Potential

**Pricing Tiers**:
- **Professional**: $500/mo (10 analyses/mo, scenarios, backtesting)
- **Premium**: $1,000/mo (unlimited analyses, white-label, priority support)
- **Enterprise**: $2,000/mo (API access, custom agents, dedicated support)

**Target Acquisition**:
- Year 1: 20-50 customers @ $500-1000/mo = $10k-50k MRR ($120k-600k ARR)
- Year 2: 100-200 customers @ $750-1500/mo = $75k-300k MRR ($900k-3.6M ARR)
- Year 3: 300-500 customers @ $1000-2000/mo = $300k-1M MRR ($3.6M-12M ARR)

**Unit Economics**:
- Cost per analysis: $3.35 (current, optimized)
- Marginal cost: ~$0.10/analysis (after Phase 1: $3.60)
- Gross margin: 98%+ (SaaS economics)
- CAC target: <3 months payback (direct outreach, no paid ads initially)

**TAM (Total Addressable Market)**:
- RIAs in US: ~15,000
- Family Offices: ~5,000
- Target (managing $10M-500M): ~5,000
- Conservative capture: 1-2% = 50-100 customers = $600k-2.4M ARR

---

## Critical Gaps for Business Viability

### Priority 0: Proof of Performance (BLOCKER)

**Gap**: No backtesting results, no track record
**Impact**: Cannot sell without proof
**Timeline**: 2-3 weeks (Phase 0 + initial backtest)

**Deliverable**:
- Run 50 historical analyses (2020-2024)
- Measure: Directional accuracy (>70%), correlation with returns (>0.5)
- Publish: "Our system identified X winners with Y% accuracy"
- Case studies: "Called NVDA at $120 in 2020 (now $450)"

**Why Critical**: Every investment product needs track record. "Trust me" ≠ "Here's proof"

---

### Priority 1: A-Level Quality Consistency (BLOCKER)

**Gap**: Currently B-level (84/100), inconsistent
**Impact**: Clients pay for A-level, not B
**Timeline**: 6-8 weeks (Phase 1)

**Current Quality Issues** (from META analysis B/84):
1. Valuation-recommendation mismatch (-10% downside → HOLD should be SELL)
2. Missing competitive moat analysis
3. Opaque hypothesis validation process
4. Timeline inconsistencies
5. Financial analysis not evaluated/summarized

**Target**: A- (90/100) on 80%+ of 30 test cases

---

### Priority 2: Missing Data Sources (QUALITY CEILING)

**Gap**: Using only free data (SEC filings + Brave search)
**Impact**: Stuck at B-level without richer data
**Timeline**: Ongoing (Phase 1.3 + 1.5)

**Current**: SEC Edgar + Yahoo Finance + Brave Search
**Needed**: 10-K MD&A parsing, trusted source scraper (SemiAnalysis, Damodaran)
**Future** (optional): Earnings call transcripts, alternative data

**Why Critical**: Bloomberg/FactSet competitive advantage is data access. We need sufficient data moat for A-level quality.

---

### Priority 3: Product Positioning (GO-TO-MARKET)

**Gap**: Too generic - "AI analyzes stocks"
**Impact**: No differentiation vs ChatGPT (free)
**Timeline**: Strategic decision (no dev time)

**Generic Positioning** (AVOID):
- "AI-powered stock analysis"
- "ChatGPT for investing"
- "Automated equity research"

**Winning Positioning** (PURSUE):
- "Replace your junior analyst with AI - $2k/mo vs $150k/yr"
- "Institutional-grade equity research in 20 minutes, not 3 days"
- "Deterministic DCF valuation with audit trail for compliance"

**Differentiation**:
1. **Speed**: 20min turnaround vs days (junior analyst) or weeks (research firms)
2. **Audit Trail**: Full transparency for compliance (Bloomberg lacks this)
3. **Deterministic Math**: NumPy DCF, not LLM hallucinations (provably correct)
4. **Cost**: $500-2k/mo vs $80-150k/yr junior analyst
5. **Quality**: A-level (90/100) institutional grade

---

## Go-to-Market Strategy

### Phase 1: Build Credibility (Months 1-3)

**Goal**: Establish track record, not revenue
**Target Revenue**: $0-5k/mo (friends/family beta)

**Actions**:
1. ✅ Complete Phase 0 (evaluation harness, baseline metrics)
2. ✅ Run 50 historical backtests (2020-2024)
3. ✅ Achieve A-level quality (90/100 on 80%+ of cases)
4. ✅ Publish results: Blog post, white paper, case studies
5. ✅ Beta with 5-10 RIAs (free, in exchange for testimonials)

**Success Metric**: 3-5 written testimonials from real RIAs

---

### Phase 2: Validate Willingness to Pay (Months 4-6)

**Goal**: Prove people actually pay, not just say they would
**Target Revenue**: $5k-25k MRR

**Actions**:
1. ✅ Launch Professional tier ($500/mo)
2. ✅ Direct outreach to RIAs (no paid ads yet)
3. ✅ Acquire 20-50 paying customers
4. ✅ Add white-label reports (for RIAs to share with clients)
5. ✅ Measure: Churn rate (<10%/mo), NPS (>50), feature requests

**Success Metric**: 20 paying customers at $500/mo = $10k MRR

---

### Phase 3: Scale What Works (Months 7-12)

**Goal**: Grow to sustainable business
**Target Revenue**: $50k-100k MRR

**Actions**:
1. ✅ Premium/Enterprise tiers ($1k-2k/mo)
2. ✅ Content marketing (blog, SEO, industry publications)
3. ✅ Conference presence (RIA conferences, family office summits)
4. ✅ Referral program (existing customers → new customers)
5. ✅ Consider fundraising (if needed for growth)

**Success Metric**: 100 customers, $75k MRR, <5% monthly churn

---

## Revenue Milestones & Timeline

| Milestone | Timeline | MRR | ARR | Customers |
|-----------|----------|-----|-----|-----------|
| **Beta Launch** | Month 3 | $0 | $0 | 5-10 (free) |
| **First Dollar** | Month 4 | $500 | $6k | 1 |
| **Proof of Concept** | Month 6 | $10k | $120k | 20 |
| **Sustainable** | Month 12 | $50k | $600k | 75-100 |
| **Scale** | Month 24 | $150k | $1.8M | 200-300 |

---

## Competitive Landscape

### Direct Competitors

**Bloomberg Terminal**:
- **Strengths**: Comprehensive data, real-time feeds, industry standard
- **Weaknesses**: $24k/seat (overkill for small RIAs), complex interface
- **Our Advantage**: 10x cheaper, faster research, compliance audit trail

**Junior Analyst**:
- **Strengths**: Custom research, deep dives, relationship building
- **Weaknesses**: $80-150k/yr, slow (days), human error, scalability limits
- **Our Advantage**: 95% cost savings, 20min turnaround, consistent quality

**Research Firms** (FactSet, Morningstar Direct):
- **Strengths**: Institutional quality, established reputation
- **Weaknesses**: $2-5k/mo, slow, limited customization
- **Our Advantage**: Faster, more customizable, audit trail

**ChatGPT / Free AI**:
- **Strengths**: Free, accessible, conversational
- **Weaknesses**: Hallucinations, no deterministic math, no compliance, no depth
- **Our Advantage**: Deterministic DCF, institutional quality, audit trail

---

### Positioning Map

```
                    High Quality
                         |
                         |
          Research Firms | Bloomberg
                         |
         Our Target -------- (A-level, $500-2k/mo)
                         |
              Junior     |
             Analyst     |
                         |
                    ChatGPT (Free)
                         |
                         |
      Low Cost -------- | -------- High Cost
```

**Sweet Spot**: High quality at medium cost (10x cheaper than Bloomberg, 50x cheaper than analyst)

---

## Risk Assessment

### Risk 1: Quality Ceiling (MEDIUM)

**Risk**: Stuck at B-level, can't reach A-level with current approach
**Mitigation**: Phase 0 evaluation harness validates improvements systematically
**Probability**: 20% (roadmap is well-validated via competitive research)

---

### Risk 2: No Willingness to Pay (MEDIUM-HIGH)

**Risk**: RIAs say they'd pay but don't actually when asked
**Mitigation**: Beta with 5-10 RIAs (free) → measure engagement before monetizing
**Probability**: 40% (untested market)

---

### Risk 3: Commoditization (LOW-MEDIUM)

**Risk**: Bloomberg/FactSet add AI features, make us obsolete
**Mitigation**: Build moat via memory/learning (Phase 3), move fast
**Probability**: 30% over 24 months

---

### Risk 4: Regulatory/Compliance (LOW)

**Risk**: Investment advice regulations require registration (RIA/broker-dealer)
**Mitigation**: Position as "research tool," not advice; consult securities lawyer
**Probability**: 10% (research tools generally exempt)

---

## Success Criteria

### 6-Month Validation Criteria

**Go/No-Go Decision** at Month 6:

**GO** (continue building business):
- ✅ 20+ paying customers at $500+/mo
- ✅ <10% monthly churn
- ✅ NPS >50 (customers recommend us)
- ✅ A-level quality (90/100) on 80%+ of analyses
- ✅ Backtesting shows >70% directional accuracy

**NO-GO** (keep as personal tool):
- ❌ <10 paying customers OR high churn (>15%/mo)
- ❌ Quality stuck at B-level (<85/100)
- ❌ Low engagement (customers don't use product)
- ❌ Backtesting shows <60% accuracy

---

## Financial Projections (Conservative)

### Year 1 (Months 1-12)

**Revenue**: $0 → $600k ARR
- Q1 (Months 1-3): $0 (beta, build credibility)
- Q2 (Months 4-6): $10k MRR ($120k ARR) - first customers
- Q3 (Months 7-9): $25k MRR ($300k ARR) - word of mouth
- Q4 (Months 10-12): $50k MRR ($600k ARR) - scaling

**Costs**:
- Development: $0 (solo founder, sweat equity)
- Infrastructure: $500-1k/mo (API costs, hosting)
- Sales/Marketing: $2-5k/mo (conferences, content)
- **Total Y1 Costs**: ~$50k

**Profit**: $600k ARR - $50k costs = **$550k net** (92% margin)

---

### Year 2 (Months 13-24)

**Revenue**: $600k → $1.8M ARR
- Assume: 100 → 200 customers, $750 avg/customer/mo

**Costs**:
- Infrastructure: $2-5k/mo (scaling)
- Sales/Marketing: $10-20k/mo (conferences, ads, content)
- Support: $5-10k/mo (part-time contractor)
- **Total Y2 Costs**: ~$200k

**Profit**: $1.8M ARR - $200k costs = **$1.6M net** (89% margin)

---

## Strategic Decision

**Current State**: Sophisticated personal tool (hobby)

**Recommended Path**: **Build Small Business** (junior analyst replacement route)

**Reasoning**:
1. ✅ Clear value proposition: $2k/mo vs $150k/yr
2. ✅ Proven market need (RIAs hiring analysts or outsourcing)
3. ✅ Achievable milestones (A-level quality in 10 weeks)
4. ✅ Low risk (validate in 6 months with <$50k investment)
5. ✅ High margin business (92%+ SaaS economics)

**Next Steps**:
1. **Complete Phase 0** (2 weeks): Evaluation harness, baseline
2. **Run backtests** (2 weeks): 50 historical analyses, publish results
3. **Achieve A-level** (6 weeks): Complete Phase 1 enhancements
4. **Beta launch** (Month 3): 5-10 free RIA partners
5. **First dollar** (Month 4): Launch Professional tier at $500/mo
6. **Go/No-Go** (Month 6): 20 customers OR pivot to personal tool

**Estimated Time Investment**: 10 weeks to market-ready, 6 months to validation

---

## Open Questions for Future Discussion

1. **Pricing**: Start at $500/mo or $1k/mo? Bundle vs usage-based?
2. **White-label**: Priority feature or nice-to-have?
3. **Niche**: Generalist or specialize (small-cap tech, biotech, etc.)?
4. **Sales motion**: Pure self-serve or high-touch for first 20 customers?
5. **Fundraising**: Bootstrap or raise seed round to accelerate?
6. **Legal**: Securities lawyer review for compliance (investment advice regulations)?

---

## Appendix: Customer Segment Comparison

### Why RIAs/Family Offices (not Retail or Hedge Funds)?

| Segment | TAM | WTP | Fit | Reason for Deprioritization |
|---------|-----|-----|-----|----------------------------|
| **Retail Investors** | 50M+ | $30-100/mo | ⚠️ Low | ChatGPT is "good enough" and free |
| **RIAs/Family Offices** | 5k | $500-2k/mo | ✅ High | **BEST FIT** - clear ROI vs junior analyst |
| **Hedge Funds** | 2k | $2k-10k/mo | ⚠️ Medium | Already have Bloomberg + teams, need unique edge |
| **Corporate Dev** | 10k+ | $2k-10k/mo | ✅ High | Different use case (M&A, comp intel), could explore later |

**Winner**: RIAs/Family Offices - clear pain (expensive analyst), clear ROI ($500/mo vs $150k/yr), accessible market

---

**Document Status**: Strategic discussion documented, tabled for future
**Next Review**: After Phase 0 completion (2 weeks)
**Decision**: Focus on completing Phase 0+1 (foundation), then reassess business path
