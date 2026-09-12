from typing import Tuple
from financial_state import FinancialState
from plan_generator import CandidatePlan

def validate_plan(
    plan: CandidatePlan,
    state: FinancialState,
    allows_partial_payment: bool
) -> Tuple[bool, str]:
    pm = plan.payment_method
    
    # 1. User Payment Method Preference Check
    user_pms = state.payment_methods_user_will_consider
    
    if pm == 'full_payment' and 'full_payment' not in user_pms:
        return False, "User will not consider full_payment"
        
    if pm == 'partial_payment':
        if 'partial_payment' not in user_pms:
            return False, "User will not consider partial_payment"
        if not allows_partial_payment:
            return False, "Request does not allow partial payment"
        if len(plan.payment_schedule) != 2:
            return False, "Partial payment must have exactly 2 payments"
        p1_amt = plan.payment_schedule[0][1]
        if p1_amt <= 0 or p1_amt >= plan.total_amount_payable:
            return False, "Partial payment first payment must be > 0 and < requested_amount"

    if pm == 'installments':
        if 'installments' not in user_pms:
            return False, "User will not consider installments"
        if state.max_installment_months is not None:
            # Estimate duration in months
            num_payments = plan.number_of_payments
            if num_payments > state.max_installment_months + 1:
                return False, f"Installment length {num_payments} exceeds max_installment_months {state.max_installment_months}"

    if pm == 'wait':
        if 'full_payment' not in user_pms:
            return False, "Wait requires user considering full_payment"

    # 2. Spending Changes Validation
    if len(plan.spending_changes) > 3:
        return False, "Max 3 spending changes allowed"
        
    target_events = set()
    for sc in plan.spending_changes:
        parts = sc.split(':')
        action_type = parts[0]
        event_id = parts[1]
        
        if event_id in target_events:
            return False, f"Multiple spending changes targeting same event {event_id}"
        target_events.add(event_id)
        
        # Check against protected categories
        matched_evt = next((e for e in state.flexible_expenses if e.event_id == event_id), None)
        if matched_evt:
            if matched_evt.category in state.protected_categories:
                return False, f"Event {event_id} is in protected category {matched_evt.category}"
            if action_type == 'stop' and matched_evt.category not in state.stop_categories:
                return False, f"Category {matched_evt.category} not in user stop_categories"
            if action_type == 'reduce_to' and matched_evt.category not in state.reduce_categories:
                return False, f"Category {matched_evt.category} not in user reduce_categories"

    return True, "Valid"
