from datetime import date, timedelta
from typing import Optional, List, Dict, Tuple
from utils.dates import add_days, date_range
from financial_state import FinancialState
from plan_generator import CandidatePlan

class Forecaster:
    def __init__(self, forecast_days: int = 90):
        self.forecast_days = forecast_days

    def is_plan_safe(
        self,
        plan: CandidatePlan,
        state: FinancialState,
        request_date: date
    ) -> bool:
        start_d = request_date
        end_d = add_days(request_date, self.forecast_days)
        
        # Parse spending changes
        stopped_events = set()
        reduced_amounts: Dict[str, float] = {}
        for sc in plan.spending_changes:
            parts = sc.split(':')
            if parts[0] == 'stop':
                stopped_events.add(parts[1])
            elif parts[0] == 'reduce_to':
                reduced_amounts[parts[1]] = float(parts[2])

        # Build day-by-day cash flows map
        daily_cash_flow: Dict[date, float] = {d: 0.0 for d in date_range(start_d, end_d)}
        
        # 1. Pending debits
        for pe in state.pending_events:
            p_date = pe.settlement_date or pe.event_date or request_date
            if start_d <= p_date <= end_d:
                daily_cash_flow[p_date] -= pe.amount

        # 2. Confirmed and Future recurring/scheduled items
        all_events = state.confirmed_events + state.future_events
        for evt in all_events:
            e_date = evt.settlement_date or evt.event_date
            if not e_date or e_date < start_d or e_date > end_d:
                continue
                
            if evt.event_id in stopped_events:
                continue
                
            amt = evt.amount
            if evt.event_id in reduced_amounts:
                amt = reduced_amounts[evt.event_id]
                
            if evt.direction == 'credit':
                # Count confirmed salary/income only on settlement date
                if evt.event_type in ('salary', 'income') and evt.status in ('settled', 'scheduled'):
                    daily_cash_flow[e_date] += amt
            elif evt.direction == 'debit':
                daily_cash_flow[e_date] -= amt

        # 3. Apply Plan Payments
        for p_date, p_amt in plan.payment_schedule:
            if start_d <= p_date <= end_d:
                daily_cash_flow[p_date] -= p_amt

        # 4. Simulate Daily Balance
        curr_bal = state.balance
        for d in date_range(start_d, end_d):
            curr_bal += daily_cash_flow[d]
            if curr_bal < state.minimum_balance - 1e-4:
                return False
                
        return True

    def calculate_amount_safe_to_pay_today(
        self,
        state: FinancialState,
        request_date: date,
        requested_amount: float
    ) -> float:
        # Binary search for max safe amount today without spending changes
        low = 0.0
        high = requested_amount
        best_safe = 0.0
        
        # Quick test high
        dummy_plan = CandidatePlan(
            request_id="", payment_method="full_payment", payment_option_id=None,
            payment_schedule=[(request_date, high)], spending_changes=[],
            total_amount_payable=high, start_date=request_date, number_of_payments=1
        )
        if self.is_plan_safe(dummy_plan, state, request_date):
            return requested_amount

        for _ in range(15):
            mid = (low + high) / 2.0
            p = CandidatePlan(
                request_id="", payment_method="full_payment", payment_option_id=None,
                payment_schedule=[(request_date, mid)], spending_changes=[],
                total_amount_payable=mid, start_date=request_date, number_of_payments=1
            )
            if self.is_plan_safe(p, state, request_date):
                best_safe = mid
                low = mid
            else:
                high = mid
                
        return round(best_safe, 2)

    def calculate_earliest_full_date(
        self,
        state: FinancialState,
        request_date: date,
        requested_amount: float
    ) -> Optional[date]:
        end_d = add_days(request_date, self.forecast_days)
        curr_d = request_date
        
        while curr_d <= end_d:
            p = CandidatePlan(
                request_id="", payment_method="full_payment", payment_option_id=None,
                payment_schedule=[(curr_d, requested_amount)], spending_changes=[],
                total_amount_payable=requested_amount, start_date=curr_d, number_of_payments=1
            )
            if self.is_plan_safe(p, state, request_date):
                return curr_d
            curr_d = add_days(curr_d, 1)
            
        return None
