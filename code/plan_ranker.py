from datetime import date
from typing import List, Optional
from plan_generator import CandidatePlan

def rank_plans(
    safe_plans: List[CandidatePlan],
    desired_completion_date: date
) -> Optional[CandidatePlan]:
    if not safe_plans:
        return None

    def plan_sort_key(p: CandidatePlan):
        # 1. Completion date <= desired_completion_date (0 = yes, 1 = no)
        last_payment_date = p.payment_schedule[-1][0] if p.payment_schedule else p.start_date
        completes_on_time = 0 if last_payment_date <= desired_completion_date else 1

        # 2. Spending changes count (0 is best)
        num_changes = len(p.spending_changes)

        # 3. Total amount payable
        total_paid = p.total_amount_payable

        # 4. Start date (earlier is best)
        start_d = p.start_date

        # 5. Number of payments (fewer is best)
        num_payments = p.number_of_payments

        # 6. Option ID tie-breaker
        opt_id = p.payment_option_id if p.payment_option_id is not None else "zzzzzz"

        return (completes_on_time, num_changes, total_paid, start_d, num_payments, opt_id)

    sorted_plans = sorted(safe_plans, key=plan_sort_key)
    return sorted_plans[0]
