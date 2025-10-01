from __future__ import annotations

import hashlib
import time
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple, List

import httpx

from investing_agents.schemas.fundamentals import Fundamentals


SEC_BASE = "https://data.sec.gov"
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


def _ua_headers(edgar_ua: Optional[str]) -> Dict[str, str]:
    ua = edgar_ua or "email@example.com Investing-Agent/0.1"
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ensure_cik10(cik: str | int) -> str:
    s = "".join(ch for ch in str(cik) if ch.isdigit())
    s = s.lstrip("0") or "0"
    return f"CIK{s.zfill(10)}"


def _load_ticker_map(edgar_ua: Optional[str] = None, client: Optional[httpx.Client] = None) -> Dict[str, int]:
    """
    Load SEC ticker->CIK map. Returns dict of TICKER (upper) -> CIK (int).
    Endpoint format is a JSON object keyed by string indices, each value like
    {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}.
    """
    use_client = client or httpx.Client()
    try:
        resp = use_client.get(SEC_TICKER_MAP_URL, headers=_ua_headers(edgar_ua), timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        mapping: Dict[str, int] = {}
        # Accept either dict-of-dicts (indexed) or list
        if isinstance(data, dict):
            it = data.values()
        elif isinstance(data, list):
            it = data
        else:
            it = []
        for row in it:
            try:
                t = str(row.get("ticker", "")).upper().strip()
                cik = int(row.get("cik_str"))
            except Exception:
                continue
            if t:
                mapping[t] = cik
        return mapping
    finally:
        if client is None:
            use_client.close()


def _resolve_cik10(cik_or_ticker: str, edgar_ua: Optional[str] = None, client: Optional[httpx.Client] = None) -> str:
    """Resolve input (CIK digits or TICKER) to zero-padded CIK########## string with CIK prefix."""
    s = str(cik_or_ticker).strip()
    if s.isdigit():
        return _ensure_cik10(s)
    # Treat as ticker; load mapping
    mapping = _load_ticker_map(edgar_ua=edgar_ua, client=client)
    cik = mapping.get(s.upper())
    if not cik:
        raise ValueError(f"Unknown ticker for SEC mapping: {cik_or_ticker}")
    return _ensure_cik10(cik)


def fetch_companyfacts(cik_or_ticker: str, edgar_ua: Optional[str] = None, client: Optional[httpx.Client] = None) -> Tuple[dict, dict]:
    """
    Fetch SEC companyfacts JSON for a CIK or a ticker. Returns (json, meta) where meta includes
    {source_url, retrieved_at, content_sha256}.
    Note: Requires network and a valid SEC User-Agent string.
    """
    use_client = client or httpx.Client()
    try:
        cik10 = _resolve_cik10(cik_or_ticker, edgar_ua=edgar_ua, client=use_client)
        url = f"{SEC_BASE}/api/xbrl/companyfacts/{cik10}.json"
        headers = _ua_headers(edgar_ua)
        resp = use_client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        b = resp.content
        meta = {
            "source_url": url,
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
            "content_sha256": _hash_bytes(b),
            "license": "SEC public data",
            "size": len(b),
            "content_type": resp.headers.get("Content-Type", "application/json"),
        }
        return resp.json(), meta
    finally:
        if client is None:
            use_client.close()


def _pick_fact_unit(fact: dict, unit_priority: Iterable[str]) -> Optional[dict]:
    units: dict = fact.get("units", {})
    for u in unit_priority:
        if u in units and units[u]:
            return {"unit": u, "series": units[u]}
    return None

def _scale_for_unit(unit: str) -> float:
    unit = (unit or "").lower().strip()
    if unit == "usd":
        return 1.0
    if unit == "usdm":
        return 1_000_000.0
    if unit in ("usdth", "usd000"):  # thousands
        return 1_000.0
    # Default: no scale
    return 1.0


def _to_annual(series: Iterable[dict], scale: float = 1.0) -> Dict[int, float]:
    """Return a map of {year: value} using full-year filings only.

    We accept only items with fp in {FY, FYR} to avoid mixing quarter or YTD values
    that can understate or overstate annual metrics (e.g., revenue). If no FY is
    present for a tag, callers should consider alternate tags.
    """
    ann: Dict[int, float] = {}
    for item in series:
        try:
            fy = item.get("fy")
            fp = str(item.get("fp") or "").upper().strip()
            if fp not in {"FY", "FYR"}:
                continue
            val = float(item.get("val")) * float(scale)
        except Exception:
            continue
        end = item.get("end")
        year = None
        if fy is not None:
            try:
                year = int(fy)
            except Exception:
                year = None
        if year is None and end:
            try:
                year = datetime.fromisoformat(end).year
            except Exception:
                continue
        if year is None:
            continue
        ann[year] = val
    return ann


def _quarter_of_fp(fp: Optional[str]) -> Optional[int]:
    if not fp:
        return None
    fp = str(fp).upper().strip()
    if fp.startswith("Q1"):
        return 1
    if fp.startswith("Q2"):
        return 2
    if fp.startswith("Q3"):
        return 3
    if fp.startswith("Q4"):
        return 4
    return None


def _collect_quarters(series: Iterable[dict], scale: float = 1.0) -> List[tuple]:
    qrows: List[tuple] = []
    for item in series:
        try:
            fy = int(item.get("fy")) if item.get("fy") is not None else None
            fp = item.get("fp")
            q = _quarter_of_fp(fp)
            end = item.get("end")
            val = float(item.get("val")) * float(scale)
        except Exception:
            continue
        if q is None:
            continue
        try:
            end_dt = datetime.fromisoformat(end).date() if end else None
        except Exception:
            end_dt = None
        if end_dt is None:
            # fallback: synthesize by year/quarter order
            end_dt = datetime(int(fy) if fy else 1900, max(1, q * 3), 1).date()
        qrows.append((end_dt, fy, q, val))
    qrows.sort(key=lambda x: x[0])
    return qrows


def _ttm_from_quarters(series: Iterable[dict], scale: float = 1.0) -> Optional[float]:
    qs = _collect_quarters(series, scale=scale)
    if len(qs) < 4:
        return None
    # Sum last 4 quarters
    last_four = [v for (_, _, _, v) in qs[-4:]]
    return float(sum(last_four))


REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
]
EBIT_TAGS = [
    "OperatingIncomeLoss",
]
DEPR_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
]
CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "CapitalExpenditures",
]
LEASE_ASSET_TAGS = [
    "OperatingLeaseRightOfUseAsset",
]
LEASE_LIAB_TAGS = [
    "OperatingLeaseLiability",
    "OperatingLeaseLiabilityNoncurrent",
    "OperatingLeaseLiabilityCurrent",
]
SHARES_TAGS = [
    # Prefer point-in-time outstanding, then fall back to weighted-average shares
    "CommonStockSharesOutstanding",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
]
TAX_RATE_TAGS = [
    "EffectiveIncomeTaxRateContinuingOperations",
    "EffectiveIncomeTaxRate",
]

# IFRS tags (companyfacts often under key 'ifrs-full')
IFRS_REVENUE_TAGS = ["Revenue"]
IFRS_EBIT_TAGS = ["OperatingProfitLoss", "ProfitLossFromOperatingActivities"]
IFRS_SHARES_TAGS = [
    "NumberOfSharesOutstanding",
    "WeightedAverageNumberOfOrdinarySharesOutstandingBasic",
]
IFRS_TAX_RATE_TAGS = ["EffectiveTaxRate"]

# Working capital (US-GAAP and IFRS) — annual snapshots
CURR_ASSETS_TAGS = ["AssetsCurrent"]
IFRS_CURR_ASSETS_TAGS = ["CurrentAssets"]
CURR_LIABS_TAGS = ["LiabilitiesCurrent"]
IFRS_CURR_LIABS_TAGS = ["CurrentLiabilities"]


def parse_companyfacts_to_fundamentals(cf: dict, ticker: str, company: Optional[str] = None) -> Fundamentals:
    facts_root = cf.get("facts", {})
    facts = facts_root.get("us-gaap", {})
    facts_ifrs = facts_root.get("ifrs-full", {})
    # Revenue
    revenue = {}
    revenue_ttm: Optional[float] = None
    for tag in REVENUE_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                series = pick["series"]
                revenue = _to_annual(series, scale=scale)
                # Try TTM from quarters
                ttm = _ttm_from_quarters(series, scale=scale)
                if ttm and ttm > 0:
                    revenue_ttm = ttm
                if revenue:
                    break
    if not revenue and facts_ifrs:
        for tag in IFRS_REVENUE_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    series = pick["series"]
                    revenue = _to_annual(series, scale=scale)
                    ttm = _ttm_from_quarters(series, scale=scale)
                    if ttm and ttm > 0:
                        revenue_ttm = ttm
                    if revenue:
                        break

    # If TTM not found yet, try other tags for quarterly series without overriding annual dict
    if revenue_ttm is None:
        for tag in REVENUE_TAGS:
            if tag in facts:
                pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
                if not pick:
                    continue
                scale = _scale_for_unit(pick["unit"])
                ttm = _ttm_from_quarters(pick["series"], scale=scale)
                if ttm and ttm > 0:
                    revenue_ttm = ttm
                    break
        if revenue_ttm is None and facts_ifrs:
            for tag in IFRS_REVENUE_TAGS:
                if tag in facts_ifrs:
                    pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                    if not pick:
                        continue
                    scale = _scale_for_unit(pick["unit"])
                    ttm = _ttm_from_quarters(pick["series"], scale=scale)
                    if ttm and ttm > 0:
                        revenue_ttm = ttm
                        break

    # EBIT
    ebit = {}
    ebit_ttm: Optional[float] = None
    for tag in EBIT_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                series = pick["series"]
                ebit = _to_annual(series, scale=scale)
                # Try TTM
                ttm = _ttm_from_quarters(series, scale=scale)
                if ttm and ttm > 0:
                    ebit_ttm = ttm
                if ebit:
                    break
    if not ebit and facts_ifrs:
        for tag in IFRS_EBIT_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    series = pick["series"]
                    ebit = _to_annual(series, scale=scale)
                    ttm = _ttm_from_quarters(series, scale=scale)
                    if ttm and ttm > 0:
                        ebit_ttm = ttm
                    if ebit:
                        break

    # Shares
    shares_out = None
    for tag in SHARES_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["shares"])
            if pick and pick["series"]:
                ann = _to_annual(pick["series"], scale=1.0)
                if ann:
                    # Use the latest year
                    y = max(ann.keys())
                    shares_out = float(ann[y])
                    break
    if shares_out is None and facts_ifrs:
        for tag in IFRS_SHARES_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["shares", "sharesPure", "pure"])
                if pick and pick["series"]:
                    ann = _to_annual(pick["series"], scale=1.0)
                    if ann:
                        y = max(ann.keys())
                        shares_out = float(ann[y])
                        break

    # Tax rate (approximate)
    tax_rate = None
    for tag in TAX_RATE_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["pure"])
            if pick and pick["series"]:
                ann = _to_annual(pick["series"], scale=1.0)
                if ann:
                    y = max(ann.keys())
                    tr = float(ann[y])
                    if tr > 1:
                        tr = tr / 100.0
                    tax_rate = max(0.0, min(0.6, tr))
                    break
    if tax_rate is None and facts_ifrs:
        for tag in IFRS_TAX_RATE_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["pure"])
                if pick and pick["series"]:
                    ann = _to_annual(pick["series"], scale=1.0)
                    if ann:
                        y = max(ann.keys())
                        tr = float(ann[y])
                        if tr > 1:
                            tr = tr / 100.0
                        tax_rate = max(0.0, min(0.6, tr))
                        break

    # Depreciation & amortization (annual)
    dep_amort = {}
    for tag in DEPR_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                dep_amort = _to_annual(pick["series"], scale=scale)
                if dep_amort:
                    break
    if not dep_amort and facts_ifrs:
        for tag in ["DepreciationAndAmortisationExpense", "DepreciationAndAmortizationExpense"]:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    dep_amort = _to_annual(pick["series"], scale=scale)
                    if dep_amort:
                        break

    # Capex (annual, sign may be negative; we keep sign from filings)
    capex = {}
    for tag in CAPEX_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                capex = _to_annual(pick["series"], scale=scale)
                if capex:
                    break
    if not capex and facts_ifrs:
        for tag in [
            "PurchaseOfPropertyPlantAndEquipment",
            "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        ]:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    capex = _to_annual(pick["series"], scale=scale)
                    if capex:
                        break

    # Lease assets/liabilities (annual)
    lease_assets = {}
    for tag in LEASE_ASSET_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                lease_assets = _to_annual(pick["series"], scale=scale)
                if lease_assets:
                    break
    if not lease_assets and facts_ifrs:
        for tag in ["Right-of-useAssets", "Right-of-useAsset"]:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    lease_assets = _to_annual(pick["series"], scale=scale)
                    if lease_assets:
                        break
    lease_liabilities = {}
    for tag in LEASE_LIAB_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                ll = _to_annual(pick["series"], scale=scale)
                # Merge Current/Noncurrent if both present; prefer sum by year
                for y, v in ll.items():
                    lease_liabilities[y] = float(lease_liabilities.get(y, 0.0)) + float(v)
    if facts_ifrs:
        for tag in ["LeaseLiabilities", "CurrentLeaseLiabilities", "NoncurrentLeaseLiabilities"]:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    scale = _scale_for_unit(pick["unit"])
                    ll = _to_annual(pick["series"], scale=scale)
                    for y, v in ll.items():
                        lease_liabilities[y] = float(lease_liabilities.get(y, 0.0)) + float(v)

    # Current assets/liabilities
    current_assets = {}
    for tag in CURR_ASSETS_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                current_assets = _to_annual(pick["series"], scale=_scale_for_unit(pick["unit"]))
                if current_assets:
                    break
    if not current_assets and facts_ifrs:
        for tag in IFRS_CURR_ASSETS_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    current_assets = _to_annual(pick["series"], scale=_scale_for_unit(pick["unit"]))
                    if current_assets:
                        break

    current_liabilities = {}
    for tag in CURR_LIABS_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                current_liabilities = _to_annual(pick["series"], scale=_scale_for_unit(pick["unit"]))
                if current_liabilities:
                    break
    if not current_liabilities and facts_ifrs:
        for tag in IFRS_CURR_LIABS_TAGS:
            if tag in facts_ifrs:
                pick = _pick_fact_unit(facts_ifrs[tag], ["USD", "USDm", "USDth"])
                if pick:
                    current_liabilities = _to_annual(pick["series"], scale=_scale_for_unit(pick["unit"]))
                    if current_liabilities:
                        break

    return Fundamentals(
        company=company or cf.get("entityName", ticker),
        ticker=ticker,
        currency="USD",
        revenue=revenue,
        ebit=ebit,
        revenue_ttm=revenue_ttm,
        ebit_ttm=ebit_ttm,
        shares_out=shares_out,
        tax_rate=tax_rate,
        dep_amort=dep_amort,
        capex=capex,
        lease_assets=lease_assets,
        lease_liabilities=lease_liabilities,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
    )
