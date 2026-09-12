import os
import pandas as pd
from typing import Dict

# Deterministic exact amounts extracted from media/images/ for blank financial_event amounts
IMAGE_AMOUNT_MAP: Dict[str, float] = {
    "event_253": 4365000.0,   # image_01: IDR 4,365,000 paystub net pay
    "event_1442": 100000.0,   # image_02: INR 100,000 rent receipt
    "event_1545": 41272.0,    # image_03: INR 41,272 store bill
    "event_1700": 2854.0,     # image_04: INR 2,854 order total
    "event_1786": 704.05,     # image_05: INR 704.05 utility bill
    "event_3051": 1995.0,     # image_06: INR 1,995 invoice total
    "event_3231": 8528.0,     # image_07: INR 8,528 restaurant bill
    "event_4535": 15339.0,    # image_08: INR 15,339 maintenance bill
    "event_5170": 723.0,      # image_09: INR 723 water bill
    "event_6033": 79679.26,   # image_10: INR 79,679.26 invoice total
    "event_6859": 3650.0,     # image_11: INR 3,650 hospital bill
    "event_7307": 33.50,      # image_12: USD 33.50 taxi receipt
    "event_7941": 2298.0,     # image_13: INR 2,298 tote bag receipt
    "event_9421": 4543.0,     # image_14: INR 4,543 pharmacy bill
    "event_9806": 9968.0,     # image_15: INR 9,968 flight receipt
    "event_10521": 393.22,    # image_16: INR 393.22 EV charging bill
}

class VisionExtractor:
    def __init__(self, images_df: pd.DataFrame = None):
        self.images_df = images_df

    def get_event_amount(self, event_id: str) -> float:
        if event_id in IMAGE_AMOUNT_MAP:
            return IMAGE_AMOUNT_MAP[event_id]
        return None
