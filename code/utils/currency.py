import pandas as pd
from datetime import date
from typing import Dict, Tuple
from .dates import parse_date

class CurrencyConverter:
    def __init__(self, exchange_rates_df: pd.DataFrame):
        self.rates: Dict[Tuple[str, str, str], float] = {}
        for _, row in exchange_rates_df.iterrows():
            d_str = str(row['rate_date']).strip()
            from_curr = str(row['from_currency']).strip()
            to_curr = str(row['to_currency']).strip()
            rate = float(row['rate'])
            self.rates[(d_str, from_curr, to_curr)] = rate

    def convert(self, amount: float, from_curr: str, to_curr: str, event_date: date) -> float:
        if amount is None:
            return None
        if from_curr == to_curr:
            return float(amount)

        d_str = event_date.strftime("%Y-%m-%d") if isinstance(event_date, date) else str(event_date)
        
        # Direct lookup
        if (d_str, from_curr, to_curr) in self.rates:
            return amount * self.rates[(d_str, from_curr, to_curr)]

        # Inverse lookup
        if (d_str, to_curr, from_curr) in self.rates:
            return amount / self.rates[(d_str, to_curr, from_curr)]

        # Find closest date if exact date not present
        matching_keys = [k for k in self.rates if k[1] == from_curr and k[2] == to_curr]
        if matching_keys:
            # Pick closest date rate
            closest_key = min(matching_keys, key=lambda k: abs((parse_date(k[0]) - event_date).days))
            return amount * self.rates[closest_key]

        matching_inv_keys = [k for k in self.rates if k[1] == to_curr and k[2] == from_curr]
        if matching_inv_keys:
            closest_key = min(matching_inv_keys, key=lambda k: abs((parse_date(k[0]) - event_date).days))
            return amount / self.rates[closest_key]

        # Fallback 1.0 if not found
        return float(amount)
