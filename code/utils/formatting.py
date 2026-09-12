from datetime import date
from typing import List, Tuple, Union
from .dates import format_date

def format_payment_plan(payments: List[Tuple[Union[date, str], float]]) -> str:
    if not payments:
        return "none"
    formatted_parts = []
    for d, amt in payments:
        d_str = format_date(d) if isinstance(d, date) else str(d)
        # Round or format amount neatly (remove trailing zeros if integer, or format to 2 decimals)
        if amt == int(amt):
            amt_str = str(int(amt))
        else:
            amt_str = f"{amt:.2f}".rstrip('0').rstrip('.')
        formatted_parts.append(f"{d_str}:{amt_str}")
    return "|".join(formatted_parts)

def format_spending_changes(changes: List[str]) -> str:
    if not changes:
        return "none"
    return "|".join(changes[:3])
