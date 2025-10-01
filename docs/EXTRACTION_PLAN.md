# Legacy Code Extraction Plan

## Overview

Extract key components from the legacy codebase at `~/workspace/investing-agent` while removing framework dependencies, logging, and caching layers.

---

## Files to Extract

### 1. Valuation Kernel (PRESERVE EXACTLY)

**Source**: `~/workspace/investing-agent/investing_agent/kernels/ginzu.py`
**Destination**: `src/investing_agents/valuation/ginzu.py`

**Action**: Copy exactly as-is (DO NOT MODIFY)

**Reason**: This is the deterministic DCF engine. It's pure NumPy with no dependencies. Every calculation must be preserved for accuracy and auditability.

**Dependencies**: None (pure NumPy)

---

### 2. Core Schemas (ADAPT)

**Source Files**:
- `~/workspace/investing-agent/investing_agent/schemas/inputs.py`
- `~/workspace/investing-agent/investing_agent/schemas/valuation.py`
- `~/workspace/investing-agent/investing_agent/schemas/fundamentals.py`
- `~/workspace/investing-agent/investing_agent/schemas/evidence.py`

**Destination**: `src/investing_agents/schemas/`

**Actions**:
1. Copy Pydantic model definitions
2. **Remove**: Any logging, caching, or framework code
3. **Keep**: All validation logic, field definitions, methods
4. **Preserve**: Schema structure and contracts

**Example Changes**:
```python
# BEFORE (legacy)
from investing_agent.config import logger

class InputsI(BaseModel):
    # ... fields ...
    
    def validate(self):
        logger.info(f"Validating inputs for {self.ticker}")  # REMOVE THIS
        # validation logic stays
        
# AFTER (extracted)
class InputsI(BaseModel):
    # ... fields ...
    
    def validate(self):
        # validation logic stays
```

---

### 3. SEC Connector (ADAPT)

**Source**: `~/workspace/investing-agent/investing_agent/connectors/edgar.py`
**Destination**: `src/investing_agents/tools/edgar_connector.py`

**Actions**:
1. Copy SEC API interaction code
2. Copy parsing logic for companyfacts
3. **Remove**: HTTP caching layer (we'll implement fresh caching)
4. **Remove**: Logging statements
5. **Keep**: All parsing functions, tag mappings, data extraction

**Dependencies to Remove**:
- `http_cache.py` - we'll cache differently
- Any logging imports

**Dependencies to Keep**:
- `requests` - HTTP library
- `Fundamentals` schema - data structure

---

### 4. Schemas to Extract (Full List)

Copy these schemas with minimal changes:
- `inputs.py` - Valuation inputs
- `valuation.py` - Valuation outputs
- `fundamentals.py` - Financial data
- `evidence.py` - Evidence tracking
- `comparables.py` - Peer comparison (if needed)

**DO NOT Extract**:
- `chart_config.py` - UI-specific
- `writer_*.py` - Old narrative generation
- `router_telemetry.py` - Old framework
- `model_pr_log.py` - Old logging

---

## Extraction Steps

### Step 1: Copy Valuation Kernel

```bash
# Navigate to new project
cd ~/workspace/investing-agent-sdk

# Create directory
mkdir -p src/investing_agents/valuation

# Copy ginzu.py exactly
cp ~/workspace/investing-agent/investing_agent/kernels/ginzu.py \
   src/investing_agents/valuation/ginzu.py

# Verify no changes
diff ~/workspace/investing-agent/investing_agent/kernels/ginzu.py \
     src/investing_agents/valuation/ginzu.py
```

### Step 2: Extract Schemas

```bash
# Create schemas directory
mkdir -p src/investing_agents/schemas

# Copy schema files
for schema in inputs valuation fundamentals evidence; do
  cp ~/workspace/investing-agent/investing_agent/schemas/${schema}.py \
     src/investing_agents/schemas/${schema}.py
done

# Manual step: Edit each file to remove logging/caching
# (See removal checklist below)
```

### Step 3: Extract Edgar Connector

```bash
# Create tools directory
mkdir -p src/investing_agents/tools

# Copy edgar.py
cp ~/workspace/investing-agent/investing_agent/connectors/edgar.py \
   src/investing_agents/tools/edgar_connector.py

# Manual step: Remove caching, update imports
```

---

## Removal Checklist

For each extracted file, remove:

### Logging
```python
# REMOVE these patterns
from investing_agent.config import logger
logger.info(...)
logger.debug(...)
logger.error(...)
```

### Caching
```python
# REMOVE these patterns
from investing_agent.connectors.http_cache import CachedSession
@cache_result
@lru_cache
```

### Framework Dependencies
```python
# REMOVE these patterns
from investing_agent.config import ...
from investing_agent.storage import ...
from investing_agent.orchestration import ...
```

### Keep
```python
# KEEP these
from pydantic import BaseModel, Field
import numpy as np
import requests
from typing import ...
from datetime import ...
```

---

## Import Updates

After extraction, update imports:

### Before (Legacy)
```python
from investing_agent.schemas.inputs import InputsI
from investing_agent.kernels.ginzu import value
from investing_agent.connectors.edgar import fetch_companyfacts
```

### After (New)
```python
from investing_agents.schemas.inputs import InputsI
from investing_agents.valuation.ginzu import value
from investing_agents.tools.edgar_connector import fetch_companyfacts
```

---

## Testing After Extraction

### Test 1: Valuation Kernel

```python
# Test that ginzu.py works exactly as before
from investing_agents.schemas.inputs import InputsI
from investing_agents.valuation.ginzu import value

# Create test inputs
inputs = InputsI(
    company="Test Corp",
    ticker="TEST",
    shares_out=100.0,
    revenue_t0=1000.0,
    drivers={
        "sales_growth": [0.10, 0.10, 0.08, 0.08, 0.05],
        "oper_margin": [0.20, 0.22, 0.23, 0.24, 0.25],
        "stable_growth": 0.02,
        "stable_margin": 0.25
    },
    sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
    wacc=[0.10, 0.10, 0.10, 0.10, 0.10]
)

# Run valuation
result = value(inputs)

# Verify output structure
assert result.equity_value > 0
assert result.value_per_share > 0
```

### Test 2: Schemas

```python
# Test that schemas validate correctly
from investing_agents.schemas.inputs import InputsI
from investing_agents.schemas.fundamentals import Fundamentals

# Test InputsI validation
inputs = InputsI(...)
assert inputs.horizon() == 5

# Test Fundamentals
fund = Fundamentals(
    company="AAPL",
    ticker="AAPL",
    revenue={2021: 1000, 2022: 1100},
    ebit={2021: 200, 2022: 220}
)
assert fund.ticker == "AAPL"
```

### Test 3: Edgar Connector

```python
# Test SEC data fetching
from investing_agents.tools.edgar_connector import (
    fetch_companyfacts,
    parse_companyfacts_to_fundamentals
)

# Fetch data
cf, meta = fetch_companyfacts("AAPL", edgar_ua="test@example.com")

# Parse to fundamentals
fund = parse_companyfacts_to_fundamentals(cf, "AAPL")

# Verify data
assert fund.ticker == "AAPL"
assert len(fund.revenue) > 0
```

---

## Directory Structure After Extraction

```
src/investing_agents/
├── valuation/
│   ├── __init__.py
│   └── ginzu.py              # Extracted, UNCHANGED
├── schemas/
│   ├── __init__.py
│   ├── inputs.py             # Extracted, cleaned
│   ├── valuation.py          # Extracted, cleaned
│   ├── fundamentals.py       # Extracted, cleaned
│   └── evidence.py           # Extracted, cleaned
└── tools/
    ├── __init__.py
    └── edgar_connector.py    # Extracted, cleaned
```

---

## What NOT to Extract

DO NOT extract these components (we'll build fresh):

### Agents (Old Implementation)
- `agents/` directory - old single-pass agents
- We're building new multi-agent system

### Orchestration (Old Framework)
- `orchestration/` directory - old framework
- We're using Claude Agent SDK

### Evaluation (Old System)
- `evaluation/` directory - old evaluation
- We're building new evaluation framework

### UI/Reporting (Old System)
- `ui/` directory - HTML generation
- We're building markdown reports

### Storage/Caching (Old System)
- `storage/` directory - old caching layer
- We'll implement fresh file-based storage

---

## Extraction Verification

After extraction, verify:

- [ ] ginzu.py unchanged (byte-for-byte copy)
- [ ] All schemas validate correctly
- [ ] Edgar connector fetches data successfully
- [ ] No legacy framework imports remain
- [ ] All logging statements removed
- [ ] All caching decorators removed
- [ ] Tests pass for extracted components

---

## Timeline

**Day 1**: Extract and test valuation kernel
**Day 2**: Extract and clean schemas
**Day 3**: Extract and adapt edgar connector
**Day 4**: Integration testing, fix imports

---

**Document Version**: 1.0.0
**Last Updated**: 2024-09-30
