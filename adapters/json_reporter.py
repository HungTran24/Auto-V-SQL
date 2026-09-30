import json
import os
from dataclasses import asdict
from typing import List
from core.models import ExperimentRecord

class JsonReporterAdapter:
    """Adapter lưu trữ kết quả thực nghiệm ra file JSON"""
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_records(self, records: List[ExperimentRecord], filename: str = "experiment_results.json") -> str:
        filepath = os.path.join(self.output_dir, filename)
        serialized_data = [asdict(r) for r in records]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serialized_data, f, ensure_ascii=False, indent=2)
            
        return filepath
