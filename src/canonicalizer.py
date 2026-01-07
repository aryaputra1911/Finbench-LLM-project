import pandas as pd
import numpy as np
import re
import io
import json
import os
from pathlib import Path

class FinancialCanonicalizer:
    def __init__(self):
        # celaning strange symbol and char
        self.clean_regex = re.compile(r'[^\d\.\(\)\-]')
        # emergency keywords for financial tabels detection
        self.emergency_keywords = ['revenue', 'income', 'asset', 'profit', 'loss', 'cash', 'tax', 'sales', 'operating', 'net', 'ebitda']

    def clean_cell(self, val):
        # handling nan values
        if val is None: 
            return 0.0
        
        # eror protection : 'The truth value of a Series is ambiguous'
        # if val series or list ,take first element
        if isinstance(val, (pd.Series, np.ndarray, list)):
            val = val[0] if len(val) > 0 else 0.0

        try:
            if pd.isna(val): return 0.0
        except:
            pass

        # Teks Normalization
        s = str(val).strip().lower()
        if s in ['-', '', '_', 'none', 'þ', '¨', 'n/a', 'nil', '.']: 
            return 0.0
        
        # percentage detection
        is_percent = '%' in s
        
        # char cleaning
        clean = self.clean_regex.sub('', s)
        
        # accountancy logic
        if clean.startswith('(') and clean.endswith(')'):
            clean = '-' + clean[1:-1]
        elif clean.endswith('-'):
            clean = '-' + clean[:-1]
            
        # convertion to float
        try:
            num = float(clean)
            return num / 100 if is_percent else num
        except:
            return str(val).strip()

    def is_high_quality(self, df):
        # filtering tabels
        if df.empty or df.shape[1] < 2: 
            return False
        
        # take a context form tabel and top 3 rows
        header_context = " ".join(df.columns.astype(str)).lower()
        top_rows_context = " ".join(df.head(3).astype(str).values.flatten()).lower()
        full_context = header_context + " " + top_rows_context

        # years detection
        has_time = bool(re.search(r'(201\d|202\d|q[1-4]|fiscal|year|ended)', full_context))

        # count number density
        def check_num(x):
            return isinstance(x, (int, float)) and x != 0.0
        
        num_count = df.map(check_num).sum().sum()
        density = num_count / df.size if df.size > 0 else 0

        # search financial keywords
        has_fin = any(kw in full_context for kw in self.emergency_keywords)

        # decision
        if has_time and density > 0.02: return True 
        if has_fin and density > 0.05: return True
        if density > 0.2: return True
        
        return False

    def parse_markdown_table(self, md_content):
        lines = md_content.strip().split('\n')
        rows = []
        for line in lines:
            if '|' in line:
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                # ignor separator row
                if all(set(c) <= {'-', ':', ' '} for c in cells):
                    continue
                rows.append(cells)
        
        if len(rows) < 2: return None
        
        df = pd.DataFrame(rows)

        df.columns = [str(c).strip() if c else f"Col_{i}" for i, c in enumerate(df.iloc[0])]
        return df.iloc[1:].reset_index(drop=True)

    def process_file(self, json_path, output_dir):
        # processing json files
        if not os.path.exists(json_path): return 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON {json_path}: {e}")
            return 0
        
        count = 0
        for item in data:
            if item.get('type') == 'table':
                df = self.parse_markdown_table(item['content'])
                if df is not None:
                    df = df.map(self.clean_cell)
                    
                    if self.is_high_quality(df):
                        file_id = item['id']
                        output_file = Path(output_dir) / f"{file_id}.csv"
                        df.to_csv(output_file, index=False)
                        count += 1
        return count
