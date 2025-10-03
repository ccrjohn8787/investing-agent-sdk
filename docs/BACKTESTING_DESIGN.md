# Backtesting Design: Avoiding Data Leakage

**Version**: 1.0
**Date**: 2025-10-02
**Status**: Strategic Design Specification
**Purpose**: Technical design for validating historical predictions without future information leakage

---

## The Challenge

**Core Problem**: How do we validate our system's predictions on historical data without accidentally using information that wasn't available at the time?

**Example Scenario**:
```
Backtest: Analyze NVDA as of January 15, 2020
Available to us in 2025:
- SEC filings from 2020-2025
- News articles from 2020-2025
- Web search with 2025 knowledge
- LLM training data through 2024

Risk: Our system could accidentally use:
- NVDA's Q3 2020 earnings (filed in Aug 2020) ❌
- News about AI boom in 2023 ❌
- Knowledge of COVID-19 impact (Feb 2020+) ❌
- Any restatements of 2019 financials made in 2021+ ❌

Valid data for Jan 15, 2020 analysis:
- SEC filings submitted BEFORE Jan 15, 2020 ✅
- Price data through Jan 14, 2020 ✅
- Macro data known as of Jan 15, 2020 ✅
```

**Why This Matters**: Invalid backtests create false confidence. If we use future data, we'll think our system is better than it actually is.

---

## Proposed Solution: "Frozen Fundamentals" Approach

### Philosophy

**Accept the limitation**: Backtesting will be **narrower** than live analysis, and that's OK.

**What we're testing**: Can our system analyze companies using **only fundamental data** available at a specific point in time?

**What we're NOT testing**: Web search quality, news sentiment timing, or real-time information gathering.

### Architecture

```python
┌─────────────────────────────────────────────────────────────┐
│                   Backtest Orchestrator                      │
│                  (Date-Aware Controller)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    ┌──────────────────┐    ┌──────────────────┐
    │   Data Guard     │    │  Analysis Engine │
    │ (Timestamp Check)│    │  (Normal Mode)   │
    └──────────────────┘    └──────────────────┘
                │                       │
                ▼                       ▼
    ┌──────────────────────────────────────────┐
    │         Time-Bounded Data Sources        │
    ├──────────────────────────────────────────┤
    │ ✅ SEC EDGAR (filing_date <= cutoff)     │
    │ ✅ Price Data (date <= cutoff)           │
    │ ✅ Financial Metrics (as-reported)       │
    │ ✅ Macro Data (known as of cutoff)       │
    │ ❌ Web Search (DISABLED)                 │
    │ ❌ News APIs (DISABLED)                  │
    │ ❌ Current Filings (may have restatements)│
    └──────────────────────────────────────────┘
```

---

## Technical Implementation

### 1. Data Guard Layer

**Purpose**: Prevent any data access beyond the cutoff date

```python
# src/backtesting/data_guard.py
from datetime import datetime
from typing import Optional, Any
import logging

class DataLeakageError(Exception):
    """Raised when data from after cutoff date is accessed"""
    pass

class BacktestDataGuard:
    """Enforces temporal boundaries on all data access"""

    def __init__(self, as_of_date: datetime):
        self.cutoff = as_of_date
        self.violations = []
        self.access_log = []

    def validate_data(self, data: Any, data_date: datetime, source: str) -> Any:
        """Validate data is from before cutoff date"""

        # Log all access attempts
        self.access_log.append({
            'source': source,
            'data_date': data_date,
            'cutoff': self.cutoff,
            'timestamp': datetime.now()
        })

        # Check temporal boundary
        if data_date > self.cutoff:
            violation = {
                'source': source,
                'data_date': data_date,
                'cutoff': self.cutoff,
                'message': f"Data from {data_date} > cutoff {self.cutoff}"
            }
            self.violations.append(violation)

            # HARD FAIL - do not allow leakage
            raise DataLeakageError(
                f"Temporal boundary violated: {source} data from {data_date} "
                f"is after cutoff {self.cutoff}"
            )

        return data

    def report_violations(self) -> dict:
        """Generate audit report of any violations"""
        return {
            'total_accesses': len(self.access_log),
            'violations': len(self.violations),
            'violation_details': self.violations,
            'status': 'CLEAN' if len(self.violations) == 0 else 'CONTAMINATED'
        }
```

---

### 2. Time-Bounded Data Sources

#### 2.1 SEC EDGAR Filings (ALLOWED - Strict Time Bounds)

```python
# src/backtesting/data_sources/edgar.py
from datetime import datetime
from typing import List, Optional

class HistoricalEdgarClient:
    """Fetch SEC filings with temporal constraints"""

    def __init__(self, data_guard: BacktestDataGuard):
        self.guard = data_guard

    def get_filings(self, ticker: str, form_type: str,
                    as_of_date: datetime) -> List[dict]:
        """
        Get SEC filings submitted BEFORE as_of_date

        Example:
            as_of_date = 2020-01-15
            Returns: All 10-Ks, 10-Qs filed before Jan 15, 2020
        """

        # EDGAR has exact filing timestamps
        filings = self._fetch_from_edgar(ticker, form_type)

        # Filter to only filings before cutoff
        valid_filings = []
        for filing in filings:
            filing_date = filing['filing_date']

            # Data Guard validates
            try:
                self.guard.validate_data(filing, filing_date, 'SEC_EDGAR')
                valid_filings.append(filing)
            except DataLeakageError:
                # Skip filings after cutoff
                continue

        return valid_filings

    def get_latest_10k(self, ticker: str, as_of_date: datetime) -> Optional[dict]:
        """Get most recent 10-K filed before as_of_date"""
        filings = self.get_filings(ticker, '10-K', as_of_date)
        return filings[0] if filings else None
```

**Why This Works**:
- SEC filings have precise `filing_date` metadata
- No ambiguity about when information became public
- We can reconstruct exactly what was known on any historical date

---

#### 2.2 Price Data (ALLOWED - Clean Time Series)

```python
# src/backtesting/data_sources/prices.py
import pandas as pd
from datetime import datetime

class HistoricalPriceData:
    """Historical OHLCV data with temporal constraints"""

    def __init__(self, data_guard: BacktestDataGuard):
        self.guard = data_guard

    def get_prices(self, ticker: str, start_date: datetime,
                   end_date: datetime) -> pd.DataFrame:
        """
        Get price data between start and end dates

        Validates: end_date <= backtest cutoff
        """

        # Validate temporal boundary
        self.guard.validate_data(
            data=None,  # Not checking specific data point
            data_date=end_date,
            source='PRICE_DATA'
        )

        # Fetch from yfinance or similar
        prices = self._fetch_historical_prices(ticker, start_date, end_date)

        return prices
```

**Why This Works**:
- Price data is a clean time series (no restatements)
- OHLCV data has exact timestamps
- Easy to enforce temporal boundaries

---

#### 2.3 Financial Metrics (ALLOWED - As-Reported Only)

```python
# src/backtesting/data_sources/financials.py
from datetime import datetime
from typing import Dict

class HistoricalFinancialMetrics:
    """Financial data as reported at specific point in time"""

    def __init__(self, data_guard: BacktestDataGuard):
        self.guard = data_guard

    def get_metrics(self, ticker: str, as_of_date: datetime) -> Dict:
        """
        Get financial metrics using data available as of as_of_date

        Critical: Use AS-REPORTED values, NOT as-restated

        Example:
            NVDA 2019 revenue as of Jan 2020: Use Q4 2019 10-K
            NVDA 2019 revenue as of Jan 2021: Might be restated - DON'T USE
        """

        # Get latest 10-K before cutoff
        latest_10k = self._get_latest_filing(ticker, '10-K', as_of_date)
        latest_10q = self._get_latest_filing(ticker, '10-Q', as_of_date)

        # Extract metrics from filings
        metrics = self._extract_metrics(latest_10k, latest_10q)

        # Validate each metric's reporting date
        for metric_name, metric_value in metrics.items():
            reporting_date = latest_10k['filing_date']
            self.guard.validate_data(
                data=metric_value,
                data_date=reporting_date,
                source=f'FINANCIAL_METRIC_{metric_name}'
            )

        return metrics
```

**Critical Issue: Restatements**
```
Problem: Companies sometimes restate historical financials

Example:
- 2019 revenue reported in 2020 10-K: $10.0B
- 2019 revenue restated in 2021 10-K: $10.2B (restated)

For backtest as of Jan 2020:
  ✅ Use: $10.0B (what was known then)
  ❌ Don't use: $10.2B (known only in 2021)

Solution: Always use the filing FROM that time period, not later restatements
```

---

#### 2.4 Web Search (DISABLED in Backtest Mode)

```python
# src/backtesting/data_sources/web_search.py

class BacktestWebSearch:
    """Web search is DISABLED for backtesting"""

    def __init__(self, data_guard: BacktestDataGuard):
        self.guard = data_guard

    def search(self, query: str) -> dict:
        """
        Web search is not allowed in backtest mode

        Reason: No reliable way to ensure time boundaries
        - Search results include current web pages
        - Archive.org has gaps, not comprehensive
        - LLM training data may include future knowledge
        """
        raise NotImplementedError(
            "Web search is DISABLED for backtesting to prevent data leakage. "
            "Use historical_mode='fundamentals_only' for backtesting."
        )
```

**Why Disabled**:
- Web search results reflect current web state, not historical
- Even with date filters, risk of leakage is too high
- Archive.org has gaps and is not comprehensive
- LLM training data may include information from after cutoff date

---

#### 2.5 News APIs (DISABLED in Backtest Mode)

```python
# src/backtesting/data_sources/news.py

class BacktestNewsAPI:
    """News APIs are DISABLED for backtesting"""

    def __init__(self, data_guard: BacktestDataGuard):
        self.guard = data_guard

    def get_news(self, ticker: str, start_date: datetime,
                 end_date: datetime) -> list:
        """
        News APIs are not allowed in backtest mode

        Reason: Difficult to enforce temporal boundaries accurately
        - News articles may be updated after publication
        - API date filters may not be precise
        - Sentiment analysis could use models trained on future data
        """
        raise NotImplementedError(
            "News APIs are DISABLED for backtesting. "
            "Use SEC filings and price data only."
        )
```

**Why Disabled**:
- News articles can be updated after publication (original vs current version)
- Hard to verify precise publication timestamps
- Sentiment models may be trained on future data

---

### 3. Backtest Orchestrator

```python
# src/backtesting/orchestrator.py
from datetime import datetime
from typing import Dict, Optional

class BacktestOrchestrator:
    """Coordinates backtesting with temporal constraints"""

    def __init__(self, config: dict):
        self.config = config

    def run_backtest(self, ticker: str, analysis_date: datetime,
                     holding_period: str = '6M') -> dict:
        """
        Run historical analysis with strict temporal boundaries

        Args:
            ticker: Stock ticker
            analysis_date: Date to analyze AS OF (e.g., 2020-01-15)
            holding_period: How long to hold (6M, 1Y, 3Y)

        Returns:
            dict with prediction, actual outcome, accuracy metrics
        """

        print(f"\n{'='*60}")
        print(f"BACKTEST: {ticker} as of {analysis_date}")
        print(f"Holding Period: {holding_period}")
        print(f"{'='*60}\n")

        # 1. Initialize Data Guard
        data_guard = BacktestDataGuard(as_of_date=analysis_date)

        # 2. Initialize time-bounded data sources
        data_sources = {
            'edgar': HistoricalEdgarClient(data_guard),
            'prices': HistoricalPriceData(data_guard),
            'financials': HistoricalFinancialMetrics(data_guard),
            # Web search and news are DISABLED
        }

        # 3. Run analysis in "historical simulation mode"
        try:
            prediction = self._run_historical_analysis(
                ticker=ticker,
                as_of_date=analysis_date,
                data_sources=data_sources
            )
        except DataLeakageError as e:
            return {
                'status': 'FAILED',
                'reason': f'Data leakage detected: {e}',
                'violations': data_guard.report_violations()
            }

        # 4. Get actual outcome (this uses future data, but that's OK)
        actual_outcome = self._get_actual_outcome(
            ticker=ticker,
            start_date=analysis_date,
            holding_period=holding_period
        )

        # 5. Compare prediction to actual
        accuracy_metrics = self._evaluate_prediction(prediction, actual_outcome)

        # 6. Generate audit report
        audit_report = data_guard.report_violations()

        return {
            'status': 'SUCCESS',
            'ticker': ticker,
            'analysis_date': analysis_date,
            'prediction': prediction,
            'actual_outcome': actual_outcome,
            'accuracy': accuracy_metrics,
            'audit': audit_report
        }

    def _run_historical_analysis(self, ticker: str, as_of_date: datetime,
                                 data_sources: dict) -> dict:
        """
        Run our normal analysis pipeline, but with time-bounded data

        This uses our existing agents (HypothesisGenerator, DeepResearch, etc.)
        but feeds them only historical data
        """

        # Initialize analysis state
        state = {
            'ticker': ticker,
            'analysis_date': as_of_date,
            'mode': 'backtest',
            'data_sources': data_sources
        }

        # Run our normal orchestrator, but with backtest-mode data sources
        # (Detailed implementation depends on our existing architecture)

        result = self.orchestrator.run_analysis(state)

        return {
            'fair_value': result['valuation']['value_per_share'],
            'recommendation': result['recommendation'],
            'hypotheses': result['hypotheses'],
            'confidence': result['confidence']
        }
```

---

## Validation Strategy: Three Layers

### Layer 1: Automated Temporal Guards

**What**: Code-level enforcement (DataGuard class above)

**How**: Every data fetch goes through `validate_data()` check

**Pass Criteria**: Zero violations in automated checks

**Output**:
```json
{
  "total_accesses": 47,
  "violations": 0,
  "status": "CLEAN"
}
```

---

### Layer 2: Manual Spot Checks

**What**: Human review of random data points

**How**: For each backtest, randomly sample 5 data points and verify manually

**Process**:
```
1. Run backtest for NVDA (Jan 15, 2020)
2. Randomly sample 5 data points:
   - Revenue from Q4 2019 10-K
   - Price as of Jan 14, 2020
   - Debt from most recent 10-Q
   - WACC assumption
   - Hypothesis: "Data center growth will sustain 40%+ YoY"

3. For each data point, ask: "Could an analyst on Jan 15, 2020 have known this?"
   - Check filing dates
   - Verify no future information
   - Document in audit trail

4. Pass: 5/5 checks pass
   Fail: Any check fails → investigate entire backtest
```

**Pass Criteria**: 100% of spot checks pass (zero tolerance for leakage)

---

### Layer 3: Out-of-Sample Statistical Validation

**What**: Compare backtest accuracy to live analysis accuracy

**Logic**:
- If backtest accuracy >> live accuracy → likely data leakage
- If backtest accuracy ≈ live accuracy → no leakage (expected)
- If backtest accuracy < live accuracy → our system is improving (good!)

**Example**:
```
Live analysis (2025):
- Directional accuracy: 65%
- Correlation: r = 0.35

Backtest (2020-2024):
- Directional accuracy: 85%  ← SUSPICIOUS (too high)
- Correlation: r = 0.65       ← SUSPICIOUS (too high)

Conclusion: Likely data leakage, investigate
```

**Pass Criteria**: Backtest accuracy within ±10% of live analysis

---

## Acceptance Criteria: Four-Tier Evaluation

### Tier 1: Directional Accuracy (Most Important) 🎯

**Metric**: Did we get the direction right?

```python
def evaluate_direction(prediction: dict, actual: dict) -> bool:
    """
    Compare recommendation to actual performance

    BUY → stock outperformed market = CORRECT
    SELL → stock underperformed market = CORRECT
    HOLD → stock matched market ±5% = CORRECT
    """

    rec = prediction['recommendation']
    actual_return = actual['6M_return']
    market_return = actual['SPY_return']
    relative = actual_return - market_return

    if rec == 'BUY' and relative > 5:
        return True  # Correct
    elif rec == 'SELL' and relative < -5:
        return True  # Correct
    elif rec == 'HOLD' and abs(relative) <= 5:
        return True  # Correct
    else:
        return False  # Incorrect
```

**Success Criteria**: >70% directional accuracy

**Benchmarks**:
- Coin flip: 50%
- Junior analyst: 60%
- Senior analyst: 75%
- Our target: 70% (competitive with junior analyst)

---

### Tier 2: Magnitude Correlation (Important) 📊

**Metric**: Does our fair value estimate correlate with actual returns?

```python
def evaluate_correlation(predictions: List[dict], actuals: List[dict]) -> float:
    """
    Pearson correlation between (Fair Value - Price) and (Actual Return)

    Theory: Higher implied upside → Higher actual returns
    """

    upside_estimates = []
    actual_returns = []

    for pred, actual in zip(predictions, actuals):
        upside = (pred['fair_value'] - pred['current_price']) / pred['current_price']
        upside_estimates.append(upside)
        actual_returns.append(actual['6M_return'])

    correlation = pearsonr(upside_estimates, actual_returns)
    return correlation.r
```

**Success Criteria**: r > 0.3 (statistically significant)

**Benchmarks**:
- Random: r ≈ 0
- Academic studies (fundamental analysis): r = 0.2-0.4
- Our target: r > 0.3

---

### Tier 3: Risk Assessment Quality (Valuable) ⚠️

**Metric**: Did we identify the material risk that actually materialized?

```python
def evaluate_risk_assessment(prediction: dict, actual: dict) -> bool:
    """
    If stock underperformed, did we flag the reason in our risks?

    Example:
      Stock: NVDA underperformed by -30%
      Reason: Export controls to China
      Our risks: Did we mention "China regulatory risk"?
    """

    if actual['performance'] == 'underperformed':
        actual_risk = actual['primary_risk']  # What actually happened
        predicted_risks = prediction['top_5_risks']

        # Did we identify this risk?
        return actual_risk in predicted_risks

    # If stock performed well, risk assessment not tested
    return True  # N/A
```

**Success Criteria**: >60% of material risks correctly identified

**Benchmarks**:
- Human analysts miss ~50% of tail risks
- Our target: 60% (slightly better than human)

---

### Tier 4: Hypothesis Validation (Learning) 📚

**Metric**: Which hypotheses were validated? Which were wrong?

**Purpose**: Not pass/fail, but **continuous learning**

```python
def extract_lessons(predictions: List[dict], actuals: List[dict]) -> dict:
    """
    Analyze which types of hypotheses tend to be correct vs wrong

    Example insights:
      - "Revenue growth hypotheses overestimate by 15% on average"
      - "Margin expansion hypotheses correct 80% of time"
      - "China risk hypotheses validated in 3/5 cases"
    """

    lessons = {
        'hypothesis_accuracy': {},
        'systematic_biases': [],
        'best_predictors': [],
        'worst_predictors': []
    }

    for pred, actual in zip(predictions, actuals):
        for hyp in pred['hypotheses']:
            # Was this hypothesis validated?
            validated = check_hypothesis_validation(hyp, actual)

            # Track accuracy by hypothesis type
            hyp_type = hyp['type']  # e.g., 'revenue_growth', 'margin_expansion'
            if hyp_type not in lessons['hypothesis_accuracy']:
                lessons['hypothesis_accuracy'][hyp_type] = {'correct': 0, 'total': 0}

            lessons['hypothesis_accuracy'][hyp_type]['total'] += 1
            if validated:
                lessons['hypothesis_accuracy'][hyp_type]['correct'] += 1

    # Extract actionable lessons
    for hyp_type, stats in lessons['hypothesis_accuracy'].items():
        accuracy = stats['correct'] / stats['total']
        if accuracy < 0.5:
            lessons['worst_predictors'].append(f"{hyp_type}: {accuracy:.1%} accuracy")
        elif accuracy > 0.8:
            lessons['best_predictors'].append(f"{hyp_type}: {accuracy:.1%} accuracy")

    return lessons
```

**Success Criteria**: Generate >3 actionable lessons per 10 backtests

**Examples of Lessons**:
- "We consistently overestimate revenue growth for high-growth tech companies"
- "Margin compression hypotheses are highly predictive (85% accuracy)"
- "Geopolitical risk hypotheses are underweighted in our analysis"

---

## Overall Passing Grade

**Pass 3 out of 4 tiers** → Backtest validates our system ✅

**Pass 2 out of 4** → Directionally correct, needs improvement ⚠️

**Pass 1 or 0** → Fundamental issues, redesign needed ❌

---

## Implementation Roadmap

### Week 1: Infrastructure
- [ ] Build `BacktestDataGuard` class with temporal validation
- [ ] Implement `HistoricalEdgarClient` with time-bounded filings
- [ ] Implement `HistoricalPriceData` with cutoff enforcement
- [ ] Write unit tests for data guard (simulate leakage attempts)

### Week 2: Orchestration
- [ ] Build `BacktestOrchestrator` that wraps existing analysis pipeline
- [ ] Integrate time-bounded data sources with our agents
- [ ] Add "backtest mode" flag to disable web search/news
- [ ] Implement audit logging for all data accesses

### Week 3: Evaluation
- [ ] Build evaluation metrics (4-tier system)
- [ ] Implement manual spot check workflow
- [ ] Create statistical validation comparing backtest vs live
- [ ] Generate comprehensive backtest reports

### Week 4: Validation
- [ ] Run 10 backtests (Tier 1: easy companies)
- [ ] Manual review of all data accesses
- [ ] Fix any data leakage issues discovered
- [ ] Refine acceptance criteria based on results

---

## Test Cases (Minimum Viable Backtest)

### Test Case 1: AAPL (Jan 2020) - Stable Company
- **Analysis Date**: 2020-01-15
- **Latest Filing**: 10-K for FY2019 (filed Oct 2019)
- **Price**: ~$80 (pre-COVID)
- **Outcome**: 6M return = +15% (outperformed due to COVID recovery)
- **Expected**: Our system should recommend HOLD/BUY based on fundamentals

### Test Case 2: NVDA (Jan 2020) - Growth Company
- **Analysis Date**: 2020-01-15
- **Latest Filing**: 10-Q for Q3 FY2020 (filed Nov 2019)
- **Price**: ~$60 (pre-AI boom)
- **Outcome**: 6M return = +40% (strong data center growth)
- **Expected**: Our system should recommend BUY if we identify data center growth thesis

### Test Case 3: UBER (Jan 2020) - High Uncertainty
- **Analysis Date**: 2020-01-15
- **Latest Filing**: 10-Q for Q3 2019 (filed Nov 2019)
- **Price**: ~$35 (post-IPO volatility)
- **Outcome**: 6M return = -40% (COVID destroyed ridesharing)
- **Expected**: Our system should identify execution risk, regulatory risk

---

## Success Metrics

**Phase 1 (10 backtests - Easy tier)**:
- Directional accuracy: >60%
- Correlation: r > 0.2
- Risk identification: >50%
- Zero data leakage violations

**Phase 2 (20 backtests - Medium tier)**:
- Directional accuracy: >65%
- Correlation: r > 0.25
- Risk identification: >55%
- Zero data leakage violations

**Phase 3 (30 backtests - All tiers)**:
- Directional accuracy: >70%
- Correlation: r > 0.3
- Risk identification: >60%
- Zero data leakage violations

**Overall Goal**: Validate that our system achieves 70%+ directional accuracy on historical data with NO data leakage.

---

## Open Questions

1. **Restatements**: How do we handle companies that restated financials?
   - Proposed: Always use filing from original time period, not restated version
   - Need to verify: Can we access original filings vs current versions?

2. **Macro Data**: What macro data can we use?
   - Interest rates: Yes (Fed publishes historical)
   - GDP: Yes (BEA publishes historical)
   - Sentiment indicators: Maybe (if clearly timestamped)

3. **Model Training Data**: Could our LLM have seen future data?
   - Risk: Claude trained on data through early 2024
   - Mitigation: For backtests before 2024, this is acceptable
   - For backtests 2024+, need to consider training cutoff

4. **How often to run backtests?**
   - During development: After each major change
   - In production: Monthly or quarterly to track system degradation

---

## Appendix: Data Leakage Examples (What NOT to Do)

### Example 1: Accidental Future Filing ❌
```python
# BAD: Uses current 10-K which may include restatements
filing = edgar.get_latest_10k(ticker='NVDA')  # Gets 2024 filing

# GOOD: Use filing from specific time period
filing = edgar.get_filing_as_of(ticker='NVDA', date='2020-01-15')
```

### Example 2: Web Search Leakage ❌
```python
# BAD: Web search returns current results
results = brave_search(f"{ticker} data center growth")
# Returns 2024 articles about AI boom!

# GOOD: Disable web search in backtest mode
if mode == 'backtest':
    raise NotImplementedError("Web search disabled in backtest")
```

### Example 3: News Date Filter Insufficient ❌
```python
# BAD: Date filter alone isn't enough
news = newsapi.get_news(ticker, start='2020-01-01', end='2020-01-15')
# Articles may have been updated after publication!

# GOOD: Disable news APIs entirely for backtesting
if mode == 'backtest':
    raise NotImplementedError("News APIs disabled in backtest")
```

---

**Document Status**: ✅ Design Complete
**Next Steps**:
1. Review and approve design
2. Build evaluation harness (10 companies, Tier 1)
3. Run validation backtests
4. Iterate based on results

**Last Updated**: 2025-10-02
**Version**: 1.0
