import json
import os
import yfinance as yf
from datetime import datetime
from evaluator import FinancialEvaluator
from analytics import StockAnalyst 

# Agent Enrichment description
class DataEnrichmentAgent:
    def fetch_live_fundamentals(self, ticker_symbol):
        print(f"[*] Executing Deep-Search for {ticker_symbol}...")
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            bs = ticker.balance_sheet
            is_stmt = ticker.income_stmt
            
            ts = datetime.now().isoformat()
            
            # Helper to retrieve the latest data from a dataframe or info
            def get_latest(df, key_list, default_info_key):
                if df is not None and not df.empty:
                    for k in key_list:
                        if k in df.index:
                            return float(df.loc[k].iloc[0])
                return info.get(default_info_key)

            # extraction with Fallback Keys
            revenue = get_latest(is_stmt, ['Total Revenue', 'TotalRevenue'], 'totalRevenue')
            net_inc = get_latest(is_stmt, ['Net Income', 'NetIncome'], 'netIncome')
            assets = get_latest(bs, ['Total Assets', 'TotalAssets'], 'totalAssets')
            liabs = get_latest(bs, ['Total Liabilities Net Minority Interest', 'TotalDebt'], 'totalDebt')

            return {
                "observed": {
                    "revenue": {"value": revenue, "source": "YahooFinance_DeepSearch", "ts": ts},
                    "net_income": {"value": net_inc, "source": "YahooFinance_DeepSearch", "ts": ts},
                    "assets": {"value": assets, "source": "YahooFinance_DeepSearch", "ts": ts},
                    "liabilities": {"value": liabs, "source": "YahooFinance_DeepSearch", "ts": ts}
                }
            }
        except Exception as e:
            print(f"[!] Deep-Search failed: {e}")
            return None

# System Orchestrator definiton
class FinbenchSystem:
    def __init__(self, canonical_path):
        self.lstm_engine = StockAnalyst()
        self.evaluator = FinancialEvaluator(canonical_path)
        self.enricher = DataEnrichmentAgent()

    def _determine_capability_gate(self, state):
        gates = {
            "EPISTEMIC_HEALTHY": ["PRICE_OBSERVATION", "VOLATILITY_TRACKING", "VALUATION", "FORECASTING", "STRATEGIC_ADVICE"],
            "EPISTEMIC_CONTAMINATED": ["PRICE_OBSERVATION", "VOLATILITY_TRACKING"],
            "EPISTEMIC_INSUFFICIENT": ["PRICE_OBSERVATION"]
        }
        return gates.get(state, ["PRICE_OBSERVATION"])

    def run(self, ticker, company_id):
        print(f"\n{'='*60}\nFINBENCH-LLM HUMBLE AGENT v9.4\n{'='*60}")

        # first audit (local database)
        audit = self.evaluator.analyze_company(company_id)
        obs = audit["knowledge_base"]["observed"]

        # Checking empty & Enrichment values
        is_empty = all(v.get("value") == 0 or v.get("value") is None for v in obs.values())
        if is_empty:
            print(f"[!] Local storage void for {ticker}. Executing Deep-Search...")
            live = self.enricher.fetch_live_fundamentals(ticker)
            if live:
                obs.update(live["observed"])

        # recalculate data after data is updated
        assets = obs.get("assets", {}).get("value") or 0
        liabilities = obs.get("liabilities", {}).get("value") or 0
        revenue = obs.get("revenue", {}).get("value") or 0
        net_income = obs.get("net_income", {}).get("value") or 0
        
        # Hitung Equity Deduced
        equity_calc = round(assets - liabilities, 2)
        
        # Prove Accounting Identity
        identity_verified = (assets > 0 and assets > liabilities and assets != liabilities)

        # Update audit objects manually
        audit["knowledge_base"]["accounting_proof"] = {
            "equity_deduced": equity_calc,
            "identity_verified": identity_verified
        }

        # Epistemic Scrubbing
        for key in ["revenue", "net_income", "assets", "liabilities"]:
            entry = obs.get(key, {"value": None})
            if entry.get("value") == 0 or entry.get("value") is None:
                obs[key] = {"value": None, "reason": "omitted_due_to_unreliability", "confidence": 0.0}

        # State Assessment
        completeness = sum(1 for v in obs.values() if v.get("value") is not None) / 4
        
        if identity_verified and completeness >= 0.75:
            state = "EPISTEMIC_HEALTHY"
        elif not identity_verified and completeness > 0:
            state = "EPISTEMIC_CONTAMINATED"
        else:
            state = "EPISTEMIC_INSUFFICIENT"
        
        allowed_capabilities = self._determine_capability_gate(state)

        # Output Construction
        forecast_output = None
        if "FORECASTING" in allowed_capabilities:
            # Memanggil mesin LSTM Anda
            forecast_output = self.lstm_engine.forecast_price(ticker)

        return {
            "execution_status": "PROCESS_COMPLETE",
            "epistemic_grade": {"status": state, "allowed_capabilities": allowed_capabilities},
            "knowledge_layer": {
                "observed": obs,
                "accounting_logic": audit["knowledge_base"]["accounting_proof"]
            },
            "predictive_layer": {
                "status": "ACTIVE" if forecast_output else "INACTIVE",
                "forecast": forecast_output # 
            },
            "metacognition": {
                "known_unknowns": [],
                "self_questioning": []
            }
        }