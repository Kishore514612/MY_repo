from datetime import datetime, date, timedelta
from typing import Union, List

DATE_FORMAT = "%Y-%m-%d"

def parse_date(d_str: Union[str, date, datetime]) -> date:
    if isinstance(d_str, date) and not isinstance(d_str, datetime):
        return d_str
    if isinstance(d_str, datetime):
        return d_str.date()
    if not d_str or str(d_str).strip() == "" or str(d_str) == "nan":
        return None
    return datetime.strptime(str(d_str).strip(), DATE_FORMAT).date()

def format_date(d: date) -> str:
    if d is None:
        return ""
    return d.strftime(DATE_FORMAT)

def add_days(d: date, days: int) -> date:
    return d + timedelta(days=days)

def date_range(start_date: date, end_date: date) -> List[date]:
    curr = start_date
    res = []
    while curr <= end_date:
        res.append(curr)
        curr += timedelta(days=1)
    return res
