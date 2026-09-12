from datetime import date
from typing import Dict, Any, Optional
from financial_state import FinancialState
from plan_generator import CandidatePlan
from utils.dates import format_date
from utils.formatting import format_payment_plan, format_spending_changes

def assemble_decision(
    request_id: str,
    requested_amount: float,
    request_date: date,
    desired_completion_date: date,
    state: FinancialState,
    amount_safe_to_pay_today: float,
    earliest_full_date: Optional[date],
    winning_plan: Optional[CandidatePlan]
) -> Dict[str, Any]:
    
    amount_safe = min(amount_safe_to_pay_today, requested_amount)
    amount_safe_str = str(int(amount_safe)) if amount_safe == int(amount_safe) else f"{amount_safe:.2f}".rstrip('0').rstrip('.')
    
    if winning_plan is None:
        if earliest_full_date and earliest_full_date > request_date:
            affordability_status = "affordable_later"
            recommended_pm = "wait"
            earliest_date_str = format_date(earliest_full_date)
            plan_str = "none"
            spending_str = "none"
            explanation = (
                f"The request of {requested_amount} {state.home_currency} is not safe to pay today with current available balance of "
                f"{state.balance} {state.home_currency} while maintaining minimum balance of {state.minimum_balance} {state.home_currency}. "
                f"However, full payment will become safe on {earliest_date_str}."
            )
        else:
            affordability_status = "not_affordable"
            recommended_pm = "not_recommended"
            earliest_date_str = ""
            plan_str = "none"
            spending_str = "none"
            explanation = (
                f"The request of {requested_amount} {state.home_currency} cannot be completed safely within the 90-day forecast period "
                f"while maintaining the user's required minimum balance of {state.minimum_balance} {state.home_currency}."
            )
    else:
        pm = winning_plan.payment_method
        has_spending_changes = len(winning_plan.spending_changes) > 0
        
        if pm == 'full_payment' and winning_plan.start_date == request_date and not has_spending_changes:
            affordability_status = "affordable_now"
            recommended_pm = "full_payment"
            earliest_date_str = format_date(request_date)
            plan_str = format_payment_plan(winning_plan.payment_schedule)
            spending_str = "none"
            explanation = (
                f"The request of {requested_amount} {state.home_currency} is affordable today. "
                f"Available balance ({state.balance} {state.home_currency}) remains above minimum balance "
                f"({state.minimum_balance} {state.home_currency}) throughout the 90-day forecast."
            )
        elif pm == 'wait':
            affordability_status = "affordable_later"
            recommended_pm = "wait"
            earliest_date_str = format_date(winning_plan.start_date)
            plan_str = format_payment_plan(winning_plan.payment_schedule)
            spending_str = format_spending_changes(winning_plan.spending_changes)
            explanation = (
                f"The request is affordable later starting on {earliest_date_str}. Waiting until this date ensures "
                f"the balance stays above the minimum threshold of {state.minimum_balance} {state.home_currency}."
            )
        else: # partial_payment, installments, or with spending changes
            affordability_status = "affordable_with_plan"
            recommended_pm = pm
            earliest_date_str = format_date(earliest_full_date) if earliest_full_date else ""
            plan_str = format_payment_plan(winning_plan.payment_schedule)
            spending_str = format_spending_changes(winning_plan.spending_changes)
            
            changes_desc = f" with spending adjustments ({spending_str})" if has_spending_changes else ""
            explanation = (
                f"The request is affordable with a plan using {recommended_pm}{changes_desc}. "
                f"This schedule satisfies essential expenses and maintains the user's minimum balance "
                f"of {state.minimum_balance} {state.home_currency}."
            )

    return {
        "request_id": request_id,
        "amount_safe_to_pay": amount_safe_str,
        "affordability_status": affordability_status,
        "recommended_payment_method": recommended_pm,
        "payment_plan": plan_str,
        "earliest_date_for_full_payment": earliest_date_str,
        "spending_changes_needed": spending_str,
        "decision_explanation": explanation
    }
