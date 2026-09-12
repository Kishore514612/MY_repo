import os
import pandas as pd
from typing import Dict

class DataLoader:
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir

    def load_all(self) -> Dict[str, pd.DataFrame]:
        data = {}
        files = [
            "requests.csv",
            "sample_requests.csv",
            "financial_profiles.csv",
            "financial_events.csv",
            "exchange_rates.csv",
            "request_payment_options.csv",
            "messages.csv",
            "images.csv"
        ]
        for f in files:
            path = os.path.join(self.dataset_dir, f)
            if os.path.exists(path):
                data[f.replace(".csv", "")] = pd.read_csv(path)
            else:
                data[f.replace(".csv", "")] = pd.DataFrame()
        return data
