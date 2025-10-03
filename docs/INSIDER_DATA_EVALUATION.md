# Insider Trading Data: Signal vs Noise

**Version**: 1.0
**Date**: 2025-10-02
**Status**: Strategic Evaluation
**Decision**: DEPRIORITIZED to Tier 2 (not Tier 1)

---

## Executive Summary

**Question**: Is insider trading data relevant for long-term (6-24 month) investment research?

**Short Answer**: Yes, but only **high-conviction signals** (clusters, CEO buys, sustained patterns). Most insider activity is **noise** for long-term research.

**Priority**: **Tier 2** (after memory, backtesting, scenario DCF)
- **Estimated ROI**: +5 points (downgraded from +15)
- **Rationale**: Supplementary signal for long-term research, not primary driver

---

## The Critical Distinction

### Short-Term Trading (Tauric, ai-hedge-fund Use Case)
- **Timeframe**: Days to weeks
- **Insider signal relevance**: HIGH (immediate information advantage)
- **Usage**: Primary signal for buy/sell decisions
- **ROI for them**: +15 points (critical alpha source)

### Long-Term Investment Research (Our Use Case)
- **Timeframe**: 6-24 months
- **Insider signal relevance**: MEDIUM (supplementary confirmation)
- **Usage**: Context for thesis validation, not primary driver
- **ROI for us**: +5 points (helpful but not critical)

**Key Insight**: We were initially influenced by trading-focused systems (Tauric, ai-hedge-fund) where insider data is critical. For our long-term research focus, it's much less important.

---

## Academic Research: What the Data Says

### Study 1: Insider Purchases Predict Long-Term Returns

**Source**: Jeng, Metrick, Zeckhauser (2003) "Estimating the Returns to Insider Trading"

**Findings**:
- Insider **purchases** predict 12+ month abnormal returns
- Average abnormal return: **~8% per year**
- **But**: Effect concentrated in small purchases by CEOs, not broad-based

**Implication**: Not all insider activity is predictive. Need to filter for high-conviction signals.

---

### Study 2: Cluster Buying is More Predictive

**Source**: Cohen, Malloy, Pomorski (2012) "Decoding Inside Information"

**Findings**:
- **Cluster buys** (3+ executives buying in same period): 15% annual alpha
- **Single executive buys**: 3% annual alpha (barely significant)
- **Insider sells**: No predictive power (usually diversification)

**Implication**: Focus on clusters, not individual transactions.

---

### Study 3: CEO Buys vs Other Executives

**Source**: Lakonishok, Lee (2001) "Are Insider Trades Informative?"

**Findings**:
- **CEO purchases** (especially large): Predict returns
- **CFO purchases**: Some predictive power
- **Other executives**: Little to no predictive power
- **All sells**: Weak or no predictive power

**Implication**: Filter by role (CEO >> CFO >> others) and transaction size.

---

### Study 4: Timing Matters

**Source**: Seyhun (1986) "Insiders' Profits, Costs of Trading"

**Findings**:
- Insider buying predicts 3-24 month returns (yes)
- **But**: Most alpha accrues in first 6 months
- After 12 months: Effect weakens significantly

**Implication**: For 6-24 month research horizon, insider data is relevant but not as strong as for short-term trading.

---

## Signal vs Noise Framework

### HIGH-CONVICTION SIGNALS (Use These)

#### Signal 1: Cluster Buying ✅
**Definition**: 3+ executives buy stock within same 90-day period

**Example**:
```
NVDA Q2 2024:
- CEO buys $2M
- CFO buys $500K
- 2 Board members buy $300K each
Total: $3.1M cluster buy
```

**Predictive Power**: High (15% annual alpha per academic studies)

**Interpretation**: Strong consensus among insiders about future prospects

**Use in Our System**: Flag as "High insider confidence" in hypothesis generation

---

#### Signal 2: CEO Large Purchases ✅
**Definition**: CEO buys >$1M or >10% of current holdings

**Example**:
```
AAPL CEO buys $5M in open market
Current holdings: $40M
Purchase: 12.5% of holdings (significant)
```

**Predictive Power**: High (CEO has superior information)

**Interpretation**: CEO betting own money on company's future (not just options/RSUs)

**Use in Our System**: Strong confirmation signal for bull thesis

---

#### Signal 3: Sustained Buying Patterns ✅
**Definition**: Consistent buying over 2+ consecutive quarters

**Example**:
```
MSFT insiders:
Q1 2024: 3 executives buy $2M total
Q2 2024: 4 executives buy $3M total
Q3 2024: 2 executives buy $1.5M total

Pattern: Sustained bullish sentiment
```

**Predictive Power**: Medium-High (pattern is more meaningful than single event)

**Interpretation**: Persistent insider confidence, not one-off opportunity

**Use in Our System**: Context for multi-quarter thesis validation

---

### NOISE SIGNALS (Filter These Out)

#### Noise 1: Single Executive Sells ❌
**Why it's noise**: Usually diversification, tax planning, not bearish view

**Example**:
```
CFO sells $200K (10% of holdings)
Reason: Likely personal financial planning
Predictive power: ~0%
```

**Action**: Ignore unless part of broader pattern

---

#### Noise 2: Option Exercises ❌
**Why it's noise**: Pre-planned compensation, not market timing

**Example**:
```
Executive exercises 10,000 options, sells shares
Type: "Sell to cover" taxes
Predictive power: 0%
```

**Action**: Filter out all option-related transactions

---

#### Noise 3: Small Trades (<$100K) ❌
**Why it's noise**: Routine, not material conviction

**Example**:
```
VP buys $50K (1% of holdings)
Interpretation: Routine, not high-conviction
```

**Action**: Filter to only large purchases (>$250K)

---

#### Noise 4: 10b5-1 Planned Sales ❌
**Why it's noise**: Pre-scheduled, no timing information

**Example**:
```
CEO sells $5M via 10b5-1 plan
Plan established: 6 months ago (pre-scheduled)
Predictive power: 0%
```

**Action**: Filter out all 10b5-1 transactions

---

## Implementation Design (If We Add This)

### Data Source: FinnHub API

```python
# src/tools/insider_sentiment.py
import requests
from datetime import datetime, timedelta
from typing import List, Optional

class InsiderSentimentTool:
    """
    Analyze insider trading patterns for long-term investment signals

    Focus: High-conviction signals only (clusters, CEO buys, sustained patterns)
    Filter: Noise (sells, small trades, option exercises, 10b5-1)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"

    def get_insider_sentiment(self, ticker: str, lookback_days: int = 180) -> dict:
        """
        Get high-conviction insider signals for past N days

        Returns only: Clusters, CEO large buys, sustained patterns
        Filters out: Sells, small trades, noise
        """

        # 1. Fetch raw insider transactions
        raw_transactions = self._fetch_transactions(ticker, lookback_days)

        # 2. Filter to buys only (ignore sells)
        buys_only = [t for t in raw_transactions if t['transaction_type'] == 'BUY']

        # 3. Filter out noise
        filtered_buys = self._filter_noise(buys_only)

        # 4. Detect high-conviction signals
        signals = {
            'cluster_buying': self._detect_clusters(filtered_buys),
            'ceo_large_purchases': self._detect_ceo_buys(filtered_buys),
            'sustained_patterns': self._detect_sustained_patterns(filtered_buys)
        }

        # 5. Aggregate into single sentiment score
        sentiment = self._aggregate_signals(signals)

        return {
            'overall_sentiment': sentiment['score'],  # -1 to +1
            'confidence': sentiment['confidence'],    # 0 to 1
            'signals': signals,
            'raw_transactions_count': len(raw_transactions),
            'filtered_signals_count': len(filtered_buys)
        }

    def _filter_noise(self, transactions: List[dict]) -> List[dict]:
        """Remove noisy transactions"""

        filtered = []
        for t in transactions:
            # Filter 1: Minimum size ($250K)
            if t['value'] < 250_000:
                continue

            # Filter 2: No option exercises
            if 'option' in t['transaction_code'].lower():
                continue

            # Filter 3: No 10b5-1 planned sales
            if t.get('is_10b5_1_plan', False):
                continue

            # Passed all filters
            filtered.append(t)

        return filtered

    def _detect_clusters(self, buys: List[dict]) -> dict:
        """Detect 3+ executives buying in 90-day window"""

        # Group by 90-day windows
        windows = self._create_time_windows(buys, window_days=90)

        clusters = []
        for window in windows:
            unique_executives = set(t['name'] for t in window['transactions'])

            if len(unique_executives) >= 3:
                clusters.append({
                    'start_date': window['start'],
                    'end_date': window['end'],
                    'executive_count': len(unique_executives),
                    'total_value': sum(t['value'] for t in window['transactions']),
                    'executives': list(unique_executives)
                })

        return {
            'detected': len(clusters) > 0,
            'count': len(clusters),
            'details': clusters
        }

    def _detect_ceo_buys(self, buys: List[dict]) -> dict:
        """Detect CEO purchases >$1M"""

        ceo_buys = [
            t for t in buys
            if t['title'].upper() in ['CEO', 'CHIEF EXECUTIVE OFFICER']
            and t['value'] > 1_000_000
        ]

        return {
            'detected': len(ceo_buys) > 0,
            'count': len(ceo_buys),
            'total_value': sum(t['value'] for t in ceo_buys),
            'details': ceo_buys
        }

    def _detect_sustained_patterns(self, buys: List[dict]) -> dict:
        """Detect buying in 2+ consecutive quarters"""

        # Group by quarter
        by_quarter = self._group_by_quarter(buys)

        # Check for consecutive quarters with buying
        consecutive_quarters = []
        current_streak = []

        for quarter in sorted(by_quarter.keys()):
            if by_quarter[quarter]:  # Has transactions this quarter
                current_streak.append(quarter)
            else:
                if len(current_streak) >= 2:
                    consecutive_quarters.append(current_streak)
                current_streak = []

        # Check final streak
        if len(current_streak) >= 2:
            consecutive_quarters.append(current_streak)

        return {
            'detected': len(consecutive_quarters) > 0,
            'longest_streak': max(len(s) for s in consecutive_quarters) if consecutive_quarters else 0,
            'details': consecutive_quarters
        }
```

---

### Integration with Our Agents

**Where to integrate**: HypothesisGenerator context (not primary signal)

```python
# src/agents/hypothesis_generator.py

async def generate_hypotheses(self, ticker: str, company: str) -> List[dict]:
    """Generate investment hypotheses with insider context"""

    # 1. Gather fundamental data (primary)
    fundamentals = await self.get_fundamentals(ticker)

    # 2. Get insider sentiment (supplementary)
    insider_sentiment = await self.insider_tool.get_insider_sentiment(ticker)

    # 3. Add to context (not primary driver)
    context = {
        'fundamentals': fundamentals,
        'insider_context': self._format_insider_context(insider_sentiment)
    }

    # 4. Generate hypotheses (fundamentals-driven, insider as confirmation)
    hypotheses = await self.generate(context)

    return hypotheses

def _format_insider_context(self, sentiment: dict) -> str:
    """Format insider data for LLM context"""

    if sentiment['overall_sentiment'] < -0.2:
        return ""  # No insider activity or bearish (ignore)

    signals = sentiment['signals']
    context_parts = []

    if signals['cluster_buying']['detected']:
        cluster = signals['cluster_buying']
        context_parts.append(
            f"Note: {cluster['executive_count']} executives purchased "
            f"${cluster['total_value']/1e6:.1f}M in shares recently (cluster buying pattern)"
        )

    if signals['ceo_large_purchases']['detected']:
        ceo = signals['ceo_large_purchases']
        context_parts.append(
            f"Note: CEO purchased ${ceo['total_value']/1e6:.1f}M in open market "
            f"(high-conviction signal)"
        )

    if signals['sustained_patterns']['detected']:
        pattern = signals['sustained_patterns']
        context_parts.append(
            f"Note: Sustained insider buying over {pattern['longest_streak']} "
            f"consecutive quarters (persistent confidence)"
        )

    return "\n".join(context_parts) if context_parts else ""
```

---

## Usage Philosophy

### What Insider Data SHOULD Do

1. **Confirm existing fundamental thesis** ✅
   - Bull thesis + cluster buying = Higher confidence
   - Bull thesis + CEO large purchase = Confirmation

2. **Flag potential conflicts** ⚠️
   - Bull thesis + no insider buying = Worth investigating
   - Strong fundamentals + insider selling = Red flag

3. **Provide context** ℹ️
   - "Management has skin in the game (CEO bought $5M)"
   - "Insiders are voting with their wallets (cluster buying)"

### What Insider Data SHOULD NOT Do

1. **Drive primary investment thesis** ❌
   - Don't build thesis around insider buying alone
   - Fundamentals must be primary driver

2. **Override fundamental analysis** ❌
   - Don't buy weak fundamentals because of insider buying
   - Insiders can be wrong (overconfidence, trapped in failing company)

3. **Create false urgency** ❌
   - Insider buying doesn't mean "buy now"
   - Long-term research requires patience

---

## Priority Reassessment

### Original Assessment (Influenced by Trading Systems)
- **Priority**: Tier 1 (CRITICAL)
- **ROI**: +15 points
- **Rationale**: Both Tauric and ai-hedge-fund use it heavily

### Revised Assessment (After Critical Review)
- **Priority**: Tier 2 (MEDIUM)
- **ROI**: +5 points
- **Rationale**: Useful supplementary signal for long-term research, not critical

### Why the Downgrade?

1. **Use Case Mismatch**:
   - They focus on trading (days-weeks): Insider data is critical
   - We focus on research (6-24 months): Fundamental analysis is critical

2. **Signal-to-Noise Ratio**:
   - For trading: High signal (timely information advantage)
   - For long-term: Lower signal (fundamentals matter more over 12-24 months)

3. **Risk of Distraction**:
   - Adding noisy short-term signals could degrade long-term analysis quality
   - Better to focus on memory, backtesting, scenario analysis first

---

## Updated Roadmap Priority

### Tier 1 (Weeks 1-3): Foundation - DO THESE FIRST
1. ✅ **Memory + Reflection** (+15 pts) - Enables learning
2. ✅ **Backtesting Framework** (+10 pts) - Enables measurement
3. ✅ **Scenario DCF** (+10 pts) - Quantifies uncertainty

**Impact**: 58 → 93 (+35 points) - **Exceeds 90/100 target**

### Tier 2 (Weeks 4-6): Enhancements - ONLY IF NEEDED
4. 🟡 **News Sentiment** (+5 pts) - Market psychology
5. 🟡 **Insider Patterns** (+5 pts) - High-conviction signals only
6. 🟡 **Investor Personas** (+8 pts) - Diverse perspectives

**Impact**: 93 → 103+ (capped at 100)

**Decision Rule**:
- If Tier 1 achieves 90+/100 on backtests → Tier 2 is optional
- If Tier 1 achieves 80-89/100 → Add selective Tier 2 enhancements
- If Tier 1 achieves <80/100 → Deeper issues, rethink approach

---

## Open Questions for Future Discussion

1. **Should we add insider data at all?**
   - Pro: Adds another data point, academic research shows it works
   - Con: Risk of adding noise, complexity, potential distraction

2. **If we add it, when?**
   - Option A: After Tier 1 validation (if backtests show we need more signals)
   - Option B: Never (focus purely on fundamental analysis)
   - Option C: Only for specific company types (growth companies where insiders have more information)

3. **What's the filtering threshold?**
   - Current design: Clusters (3+ execs), CEO >$1M, sustained (2+ quarters)
   - Alternative: Even stricter (clusters of 5+, CEO >$5M, sustained 3+ quarters)

4. **How to combine with fundamental analysis?**
   - Confirmation only (current design)
   - Weighted factor in confidence score
   - Red flag system (insider selling despite bull thesis)

---

## Conclusion

**Recommendation**: **DEPRIORITIZE** insider data to Tier 2 (after memory, backtesting, scenarios)

**Rationale**:
1. **Use case mismatch**: More relevant for trading than long-term research
2. **Signal-to-noise**: Most insider activity is noise for 6-24 month horizon
3. **Better priorities**: Memory, backtesting, scenarios have higher ROI for our use case
4. **Risk of distraction**: Adding short-term signals could degrade long-term analysis

**If we do add it** (Tier 2, after Tier 1 validation):
- Focus on high-conviction signals only (clusters, CEO buys, sustained patterns)
- Use as confirmation, not primary driver
- Filter aggressively to avoid noise
- Integrate with HypothesisGenerator context, not standalone signal

**Decision point**: After Tier 1 implementation and backtesting, reassess whether insider data adds measurable value.

---

**Document Status**: ✅ Evaluation Complete
**Decision**: Deprioritized to Tier 2
**Next Review**: After Tier 1 backtesting results (Week 4-5)

**Last Updated**: 2025-10-02
**Version**: 1.0
