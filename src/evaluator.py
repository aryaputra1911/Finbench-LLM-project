import pandas as pd
import os
import glob
import re

class FinancialEvaluator:
    def __init__(self, canonical_dir):
        self.canonical_dir = canonical_dir
        self.schema = {
            'revenue': ['revenue', 'sales', 'operating income'],
            'net_income': ['net income', 'net earnings', 'net profit', 'income (loss)'],
            'assets': ['total assets', 'current assets', 'assets'],
            'liabilities': ['total liabilities', 'current liabilities', 'liabilities', 'debt']
        }

    def _clean_text(self, text):
        # clean html and strange char
        if pd.isna(text): return ""
        text = str(text).lower().replace('<br>', ' ').replace('&nbsp;', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_number(self, val):
        # number cleaning
        if pd.isna(val): return None
        s = str(val).lower().replace('\\', '').replace('$', '').replace(',', '').replace(' ', '')
        if s == '' or s == '-': return None
        if s.startswith('(') and s.endswith(')'): s = '-' + s[1:-1]
        try:
            return float(s)
        except:
            return None

    def analyze_company(self, company_id):
        # year form ID
        year_match = re.search(r'20\d{2}', company_id)
        target_year = year_match.group(0) if year_match else ""
        
        files = glob.glob(os.path.join(self.canonical_dir, f"*{company_id}*.csv"))
        data = {key: None for key in self.schema.keys()}
        
        for file in files:
            try:
                df = pd.read_csv(file)
                # column identification
                year_col_idx = -1
                for i, col in enumerate(df.columns):
                    if target_year in str(col):
                        year_col_idx = i
                        break
                
                # row itteration
                for idx, row in df.iterrows():
                    # Gabungkan header + isi baris agar pencarian keyword akurat
                    combined_text = self._clean_text(" ".join(df.columns.astype(str))) + " " + \
                                    self._clean_text(" ".join(row.astype(str)))
                    
                    for metric, keywords in self.schema.items():
                        if data[metric] is None:
                            if any(kw in combined_text for kw in keywords):
                                if year_col_idx != -1:
                                    val = self._get_number(row.iloc[year_col_idx])
                                    if val is not None: data[metric] = val
                                
                                if data[metric] is None:
                                    for cell in row:
                                        num = self._get_number(cell)
                                        if num is not None:
                                            data[metric] = num
                                            break
            except: continue
            
        return self._generate_report(company_id, data)

    def _generate_report(self, name, data):
        score = 0
        ratios = {}
        # score counting
        if data.get('revenue'): score += 25
        if data.get('net_income'): score += 25
        if data.get('assets'): score += 25
        if data.get('liabilities'): score += 25
        
        verdict = "Strong Data Found" if score >= 75 else "Partial Data" if score >= 25 else "No Data"
        return {"company_id": name, "score": score, "verdict": verdict, "raw_metrics": data}
    
