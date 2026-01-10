import json
import yfinance as yf
from datetime import datetime, timedelta
from tavily import TavilyClient
from evaluator import FinancialEvaluator
from analytics import StockAnalyst 

class FinbenchSystem:
    def __init__(self, canonical_path, tavily_api_key):
        self.lstm_engine = StockAnalyst() 
        self.evaluator = FinancialEvaluator(canonical_path)
        self.tavily_api_key = tavily_api_key
        self.researcher = TavilyClient(api_key=tavily_api_key) if tavily_api_key else None             
        self.evidence_weights = {
            "FUNDAMENTAL_DATA": 1.0,
            "PEER_CONTEXT": 0.5,
            "MARKET_NOISE": 0.0
        }

    # input classifier
    def _epistemic_noise_filter(self, query):
        speculative_noise = ['buy', 'sell', 'long', 'short', 'reco', 'advice', 'target']
        sentiment_noise = ['bullish', 'bearish', 'hype', 'undervalued', 'overvalued', 'moon']
        temporal_noise = ['surge', 'plunge', 'daily', 'news', 'rally', 'correction']
        
        all_noise = speculative_noise + sentiment_noise + temporal_noise
        detected = [word for word in all_noise if word in query.lower()]
        
        return {
            "is_noisy": len(detected) > 0,
            "noise_elements": detected,
            "action": "BLOCK_RECO" if any(w in speculative_noise for w in detected) else "IGNORE"
        }

    def _get_deep_fundamentals(self, ticker):
        try:
            t = yf.Ticker(ticker)
            bs = t.balance_sheet
            is_stmt = t.income_stmt
            
            def extract(df, keys):
                if df is not None and not df.empty:
                    for k in keys:
                        if k in df.index: 
                            val = df.loc[k].iloc[0]
                            # CEK: Jika val adalah None atau NaN, kembalikan 0.0
                            if val is None or str(val) == 'nan':
                                return 0.0
                            return float(val)
                return 0.0 # Selalu kembalikan float 0.0 jika tidak ditemukan

            return {
                "revenue": extract(is_stmt, ['Total Revenue', 'TotalRevenue']),
                "net_income": extract(is_stmt, ['Net Income', 'NetIncome']),
                "total_assets": extract(bs, ['Total Assets', 'TotalAssets']),
                "ppe_net": extract(bs, ['Net PPE', 'Property Plant Equipment Net']),
                "inventory": extract(bs, ['Inventory']),
                "total_liabilities": extract(bs, ['Total Liabilities Net Minority Interest', 'TotalLiabilities'])
            }
        except Exception as e:
            print(f"[!] Acquisition Error: {e}")
            return {}

    def _identify_business_archetype(self, ticker, fundamentals):
        rev = fundamentals.get("revenue")
        ni = fundamentals.get("net_income")
        margin = (ni / rev) if rev and ni else 0
        
        if margin > 0.15:
            return "IP_DRIVEN_PREMIUM_INDUSTRIAL"
        elif margin < 0.05:
            return "COMMODITY_VOLUME_PLAYER"
        return "STANDARD_MANUFACTURING"

    def _calculate_sovereign_metrics(self, fundamentals, archetype):
        rev = fundamentals.get("revenue", 0)
        assets = fundamentals.get("assets", 0)
        ni = fundamentals.get("net_income", 0)
        
        metrics = {}
        if rev > 0 and assets > 0:
            metrics["asset_turnover"] = round(rev / assets, 2)
            metrics["capital_intensity_ratio"] = round(assets / rev, 2)
            metrics["net_profit_margin"] = round((ni / rev) * 100, 2)
            
            # DuPont Identity Check
            metrics["return_on_assets"] = round((ni / assets) * 100, 2)
            # Menghitung kontribusi margin vs turnover terhadap ROA
            metrics["margin_contribution_to_roa"] = round(metrics["net_profit_margin"] * metrics["asset_turnover"], 2)
        
        return metrics

    def _audit_denominator_integrity(self, fundamentals):
        rev = fundamentals.get("revenue", 0)
        ppe = fundamentals.get("ppe", 0)
        assets = fundamentals.get("assets", 0)
        rnd = fundamentals.get("rnd", 0)
        
        # R&D to Revenue
        rnd_intensity = rnd / rev if rev > 0 else 0
        
        return {
            "ppe_to_revenue": round(ppe / rev if rev > 0 else 0, 3),
            "rnd_to_revenue": round(rnd_intensity, 3),
            "asset_structure": "EXTERNALIZED" if (ppe / rev if rev > 0 else 0) < 0.15 else "INTEGRATED",
            "intangible_suppression_risk": rnd_intensity > 0.15 and (ppe / assets if assets > 0 else 0) < 0.2
        }

    def _get_sector_benchmarks(self, ticker):
        sector_data = {"median_roa": 10.0, "median_turnover": 0.7, "status": "FALLBACK"}
        
        if self.researcher:
            try:
                # search ROA avg
                t = yf.Ticker(ticker)
                sector = t.info.get('sector', 'Technology')
                query = f"average ROA and asset turnover for {sector} sector 2025"
                search = self.researcher.search(query=query, max_results=1)
                sector_data["search_context"] = search['results'][0]['content'] if search['results'] else ""
                sector_data["sector_name"] = sector
                sector_data["status"] = "LIVE_SEARCH_DATA"
            except: pass
            
        return sector_data
    
    def _calculate_normalization_stress_test(self, mechanical_audit, benchmarks):
        reported_roa = mechanical_audit.get("roa", 0)
        current_intensity = mechanical_audit.get("capital_intensity", 0)
        median_ci = benchmarks.get("median_capital_intensity", 1.5) 
        
        if current_intensity >= median_ci:
            return {"status": "ALREADY_CAPITAL_INTENSE", "normalized_roa": reported_roa}

        normalized_roa = round(reported_roa * (current_intensity / median_ci), 2)        
        collapse_magnitude = round(((reported_roa - normalized_roa) / reported_roa) * 100, 2) if reported_roa > 0 else 0

        return {
            "normalized_roa": normalized_roa,
            "industry_target_ci": median_ci,
            "potential_roa_collapse_pct": collapse_magnitude,
            "integrity_risk": "HIGH" if collapse_magnitude > 40 else "STABLE"
        }

    def run(self, ticker, query=""):
        # running noise filter
        noise_audit = self._epistemic_noise_filter(query)
        
        # Data Acquisition
        raw_fund = self._get_deep_fundamentals(ticker)
        if not raw_fund or None in raw_fund.values():
            return {"error": f"Data Insufficient for {ticker}. Epistemic Block active."}

        # Analyze structure
        archetype = self._identify_business_archetype(ticker, raw_fund)
        metrics = self._calculate_sovereign_metrics(raw_fund, archetype)
        benchmarks = self._get_sector_benchmarks(ticker)
        denom_audit = self._audit_denominator_integrity(raw_fund)

        # Governance & Decision Perimeter
        governance = {
            "epistemic_grade": "EVIDENCE_STRONG" if not noise_audit["is_noisy"] else "EVIDENCE_CONTAMINATED_BY_NOISE",
            "noise_filter_report": noise_audit,
            "business_archetype": archetype,
            "decision_perimeter": {
                "allowed": ["ANALYZE_STRUCTURE", "AUDIT_INTEGRITY"],
                "forbidden": ["BUY", "SELL", "RECO_DIRECTIONAL"],
                "instruction_contract": "STRICT_NEUTRALITY_MANDATED"
            },
            "evidence_hierarchy_applied": self.evidence_weights
        }

        # Search Context only if funadmental is clean
        narratives = []
        if self.researcher:
            try:
                search = self.researcher.search(query=f"{ticker} structural moat audit", max_results=2)
                narratives = [{"content": r['content'], "url": r.get('url'), "reliability": self.evidence_weights["PEER_CONTEXT"]} for r in search['results']]
            except: pass

        return {
            "temporal": {"analysis_date": datetime.now().strftime("%Y-%m-%d")},
            "evidence_integrity": {
                "ticker": ticker, 
                "source_reliability": self.evidence_weights["FUNDAMENTAL_DATA"],
                "noise_contamination": noise_audit["is_noisy"]
            },
            "archetype_context": archetype,
            "sovereign_metrics": metrics,
            "denominator_audit": denom_audit,
            "benchmarks": benchmarks,
            "governance": governance,
            "context_noise": narratives
        }
