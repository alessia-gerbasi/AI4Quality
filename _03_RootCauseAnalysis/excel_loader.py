import pandas as pd
from typing import Dict, List, Any

class ExcelLoader:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.df = None
    
    def load(self) -> pd.DataFrame:
        """Load and cache Excel data"""
        self.df = pd.read_excel(self.excel_path)
        return self.df
    
    def get_case(self, patient_id: str) -> Dict[str, Any]:
        """Get single patient record as dict for rule evaluation"""
        if self.df is None:
            self.load()
        
        # Try common ID column names
        id_col = None
        for col in ['patient_id', 'Patient ID', 'ID', 'id']:
            if col in self.df.columns:
                id_col = col
                break
        
        if id_col is None:
            id_col = self.df.columns[0]  # Use first column as fallback
        
        row = self.df[self.df[id_col].astype(str) == str(patient_id)].iloc[0]
        return row.to_dict()
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all records"""
        if self.df is None:
            self.load()
        return self.df.to_dict('records')
    
    def get_available_ids(self) -> List[str]:
        """Get list of available patient/case IDs"""
        if self.df is None:
            self.load()
        
        id_col = None
        for col in ['patient_id', 'Patient ID', 'ID', 'id']:
            if col in self.df.columns:
                id_col = col
                break
        
        if id_col is None:
            id_col = self.df.columns[0]
        
        return self.df[id_col].astype(str).tolist()
