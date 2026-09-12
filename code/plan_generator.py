from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd

from utils.dates import parse_date, add_days
from financial_state import FinancialState, FinancialEvent

@dataclass
class CandidatePlan:
    request_id: str
    payment_method: str  # 'full_payment', 'partial_payment', 'installments', 'wait'
    payment_option_id: Optional[str]
    payment_schedule: List[Tuple[date, float]]  # List of (date, amount)
    spending_changes: List[str]  # e.g. ['stop:event_14', 'reduce_to:event_21:100']
    total_amount_payable: float
    start_date: date
    number_of_payments: int

def generate_candidate_plans(
    request_id: str,
    requested_amount: float,
    request_date: date,
    desired_completion_date: date,
    allows_partial_payment: bool,
    payment_options_df: pd.DataFrame,
    state: FinancialState,
    amount_safe_to_pay_today: float,
    earliest_full_date: Optional[date]
) -> List[CandidatePlan]:
    plans: List[CandidatePlan] = []
    
    # Filter options for this request
    req_options = payment_options_df[payment_options_df['request_id'] == request_id] if payment_options_df is not None and not payment_options_df.empty else pd.DataFrame()

    # 1. Immediate Full Payment
    full_opts = req_options[req_options['payment_method'] == 'full_payment']
    if not full_opts.empty:
        opt_row = full_opts.iloc[0]
        opt_id = str(opt_row['payment_option_id']).strip()
        p_date = parse_date(opt_row['first_payment_date']) or request_date
        amt = float(opt_row['payment_amount'])
    else:
        opt_id = None
        p_date = request_date
        amt = requested_amount
        
    plans.append(CandidatePlan(
        request_id=request_id,
        payment_method='full_payment',
        payment_option_id=opt_id,
        payment_schedule=[(p_date, amt)],
        spending_changes=[],
        total_amount_payable=amt,
        start_date=p_date,
        number_of_payments=1
    ))
    
    # 2. Installments options
    inst_opts = req_options[req_options['payment_method'] == 'installments']
    for _, opt_row in inst_opts.iterrows():
        opt_id = str(opt_row['payment_option_id']).strip()
        num_payments = int(opt_row['number_of_payments'])
        p_amount = float(opt_row['payment_amount'])
        first_date = parse_date(opt_row['first_payment_date']) or request_date
        freq_days = int(opt_row['payment_frequency_days']) if pd.notna(opt_row.get('payment_frequency_days')) else 30
        tot_payable = float(opt_row['total_payable_amount'])
        
        schedule = []
        curr_d = first_date
        for _ in range(num_payments):
            schedule.append((curr_d, p_amount))
            curr_d = add_days(curr_d, freq_days)
            
        plans.append(CandidatePlan(
            request_id=request_id,
            payment_method='installments',
            payment_option_id=opt_id,
            payment_schedule=schedule,
            spending_changes=[],
            total_amount_payable=tot_payable,
            start_date=first_date,
            number_of_payments=num_payments
        ))

    # 3. Partial Payment Plan
    if allows_partial_payment and amount_safe_to_pay_today > 0 and amount_safe_to_pay_today < requested_amount and earliest_full_date:
        rem_amount = requested_amount - amount_safe_to_pay_today
        schedule = [
            (request_date, amount_safe_to_pay_today),
            (earliest_full_date, rem_amount)
        ]
        plans.append(CandidatePlan(
            request_id=request_id,
            payment_method='partial_payment',
            payment_option_id=None,
            payment_schedule=schedule,
            spending_changes=[],
            total_amount_payable=requested_amount,
            start_date=request_date,
            number_of_payments=2
        ))

    # 4. Wait Plan
    if earliest_full_date and earliest_full_date > request_date:
        plans.append(CandidatePlan(
            request_id=request_id,
            payment_method='wait',
            payment_option_id=None,
            payment_schedule=[(earliest_full_date, requested_amount)],
            spending_changes=[],
            total_amount_payable=requested_amount,
            start_date=earliest_full_date,
            number_of_payments=1
        ))

    # Generate variants with permitted spending changes if needed
    spending_change_combos = generate_spending_change_combinations(state)
    
    base_plans = list(plans)
    for bp in base_plans:
        for sc in spending_change_combos:
            if not sc:
                continue
            cp = CandidatePlan(
                request_id=bp.request_id,
                payment_method=bp.payment_method,
                payment_option_id=bp.payment_option_id,
                payment_schedule=list(bp.payment_schedule),
                spending_changes=sc,
                total_amount_payable=bp.total_amount_payable,
                start_date=bp.start_date,
                number_of_payments=bp.number_of_payments
            )
            plans.append(cp)

    return plans

def generate_spending_change_combinations(state: FinancialState) -> List[List[str]]:
    combos: List[List[str]] = [[]]
    
    flexible_events = state.flexible_expenses
    
    stoppable_actions = []
    reducible_actions = []
    
    for evt in flexible_events:
        if evt.category in state.protected_categories:
            continue
            
        if evt.flexibility in ('stoppable', 'reducible_or_stoppable') and evt.category in state.stop_categories:
            stoppable_actions.append(f"stop:{evt.event_id}")
            
        if evt.flexibility in ('reducible', 'reducible_or_stoppable') and evt.category in state.reduce_categories:
            min_amt = evt.minimum_allowed_amount if evt.minimum_allowed_amount is not None else (evt.amount * 0.5)
            # format as integer or tidy string
            amt_str = str(int(min_amt)) if min_amt == int(min_amt) else f"{min_amt:.2f}".rstrip('0').rstrip('.')
            reducible_actions.append(f"reduce_to:{evt.event_id}:{amt_str}")

    # Single actions
    for act in stoppable_actions + reducible_actions:
        combos.append([act])
        
    # Dual actions (mutually exclusive per event)
    all_acts = stoppable_actions + reducible_actions
    for i in range(len(all_acts)):
        for j in range(i + 1, len(all_acts)):
            e1 = all_acts[i].split(':')[1]
            e2 = all_acts[j].split(':')[1]
            if e1 != e2:
                combos.append([all_acts[i], all_acts[j]])
                
    return combos
