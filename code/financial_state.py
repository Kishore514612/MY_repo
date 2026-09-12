from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any, Optional
import pandas as pd

from utils.dates import parse_date
from utils.currency import CurrencyConverter
from vision_extractor import VisionExtractor

@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str  # 'credit' or 'debit'
    amount: float   # converted to user home_currency
    currency: str   # home_currency
    event_date: Optional[date]
    settlement_date: Optional[date]
    status: str     # 'settled', 'pending', 'scheduled', 'cancelled', 'unrealized'
    linked_event_id: Optional[str]
    flexibility: str # 'fixed', 'stoppable', 'reducible', 'reducible_or_stoppable'
    minimum_allowed_amount: Optional[float]
    is_recurring: bool = False
    frequency_days: Optional[int] = None

@dataclass
class FinancialState:
    user_id: str
    home_currency: str
    balance: float
    minimum_balance: float
    financial_priorities: List[str] = field(default_factory=list)
    protected_categories: List[str] = field(default_factory=list)
    reduce_categories: List[str] = field(default_factory=list)
    stop_categories: List[str] = field(default_factory=list)
    payment_methods_user_will_consider: List[str] = field(default_factory=list)
    max_installment_months: Optional[float] = None
    
    recurring_income: List[FinancialEvent] = field(default_factory=list)
    recurring_expenses: List[FinancialEvent] = field(default_factory=list)
    confirmed_events: List[FinancialEvent] = field(default_factory=list)
    pending_events: List[FinancialEvent] = field(default_factory=list)
    cancelled_events: List[FinancialEvent] = field(default_factory=list)
    flexible_expenses: List[FinancialEvent] = field(default_factory=list)
    future_events: List[FinancialEvent] = field(default_factory=list)


def build_financial_state(
    user_id: str,
    profiles_df: pd.DataFrame,
    events_df: pd.DataFrame,
    messages_df: pd.DataFrame,
    converter: CurrencyConverter,
    vision_extractor: VisionExtractor,
    eval_date: Optional[date] = None
) -> FinancialState:
    # 1. User Profile
    user_profile = profiles_df[profiles_df['user_id'] == user_id]
    if user_profile.empty:
        raise ValueError(f"User {user_id} not found in financial_profiles.csv")
    
    row = user_profile.iloc[0]
    home_curr = str(row['home_currency']).strip()
    avail_balance = float(row['current_available_balance'])
    min_balance = float(row['minimum_balance_to_keep'])
    
    priorities = [p.strip() for p in str(row.get('financial_priorities', '')).split('|') if p and p != 'nan']
    protected = [p.strip() for p in str(row.get('expense_categories_to_protect', '')).split('|') if p and p != 'nan']
    reduce_cats = [p.strip() for p in str(row.get('expense_categories_user_is_willing_to_reduce', '')).split('|') if p and p != 'nan']
    stop_cats = [p.strip() for p in str(row.get('expense_categories_user_is_willing_to_stop', '')).split('|') if p and p != 'nan']
    pay_methods = [p.strip() for p in str(row.get('payment_methods_user_will_consider', '')).split('|') if p and p != 'nan']
    
    max_inst = row.get('max_installment_months')
    max_inst_months = float(max_inst) if pd.notna(max_inst) and str(max_inst).strip() != '' else None
    
    state = FinancialState(
        user_id=user_id,
        home_currency=home_curr,
        balance=avail_balance,
        minimum_balance=min_balance,
        financial_priorities=priorities,
        protected_categories=protected,
        reduce_categories=reduce_cats,
        stop_categories=stop_cats,
        payment_methods_user_will_consider=pay_methods,
        max_installment_months=max_inst_months
    )
    
    # 2. Financial Events processing for user
    user_events = events_df[events_df['user_id'] == user_id].copy()
    
    parsed_events: List[FinancialEvent] = []
    
    # Track cancellations/overrides
    cancelled_ids = set()
    for _, e_row in user_events.iterrows():
        status = str(e_row.get('status', '')).strip().lower()
        if status == 'cancelled':
            cancelled_ids.add(str(e_row['event_id']).strip())
            if pd.notna(e_row.get('linked_event_id')):
                cancelled_ids.add(str(e_row['linked_event_id']).strip())

    for _, e_row in user_events.iterrows():
        e_id = str(e_row['event_id']).strip()
        e_type = str(e_row.get('event_type', '')).strip().lower()
        desc = str(e_row.get('description', '')).strip()
        cat = str(e_row.get('category', '')).strip().lower()
        direction = str(e_row.get('direction', '')).strip().lower()
        orig_curr = str(e_row.get('currency', home_curr)).strip()
        status = str(e_row.get('status', '')).strip().lower()
        linked_id = str(e_row.get('linked_event_id', '')).strip() if pd.notna(e_row.get('linked_event_id')) else None
        flexibility = str(e_row.get('flexibility', 'fixed')).strip().lower()
        
        evt_date = parse_date(e_row.get('event_date'))
        settle_date = parse_date(e_row.get('settlement_date')) or evt_date
        
        # Determine Amount
        raw_amt = e_row.get('amount')
        if pd.isna(raw_amt) or str(raw_amt).strip() == '':
            # Extract from vision extractor
            extracted = vision_extractor.get_event_amount(e_id)
            amt = extracted if extracted is not None else 0.0
        else:
            amt = float(raw_amt)
            
        # Convert to home currency using event/settlement date
        converted_amt = converter.convert(amt, orig_curr, home_curr, settle_date or evt_date or date.today())
        
        min_allowed = e_row.get('minimum_allowed_amount')
        if pd.notna(min_allowed) and str(min_allowed).strip() != '':
            min_allowed_converted = converter.convert(float(min_allowed), orig_curr, home_curr, settle_date or evt_date or date.today())
        else:
            min_allowed_converted = None
            
        event_obj = FinancialEvent(
            event_id=e_id,
            user_id=user_id,
            event_type=e_type,
            description=desc,
            category=cat,
            direction=direction,
            amount=converted_amt,
            currency=home_curr,
            event_date=evt_date,
            settlement_date=settle_date,
            status=status,
            linked_event_id=linked_id,
            flexibility=flexibility,
            minimum_allowed_amount=min_allowed_converted
        )
        
        if e_id in cancelled_ids or status == 'cancelled':
            state.cancelled_events.append(event_obj)
            continue
            
        if status == 'pending':
            # Reserve pending debits only; ignore pending credits
            if direction == 'debit':
                state.pending_events.append(event_obj)
        elif status == 'settled':
            state.confirmed_events.append(event_obj)
        elif status in ('scheduled', 'unrealized'):
            if direction == 'debit' or e_type in ('salary', 'income'):
                state.future_events.append(event_obj)

        # Classify flexible expenses
        if direction == 'debit' and flexibility in ('stoppable', 'reducible', 'reducible_or_stoppable'):
            state.flexible_expenses.append(event_obj)
            
    # Detect recurring events (monthly/weekly)
    for evt in state.confirmed_events + state.future_events:
        if evt.direction == 'debit' and evt.category in ('rent', 'housing', 'utilities', 'education', 'debt_repayment', 'insurance') or evt.flexibility != 'fixed':
            evt.is_recurring = True
            evt.frequency_days = 30
        elif evt.direction == 'credit' and evt.event_type in ('salary', 'income'):
            evt.is_recurring = True
            evt.frequency_days = 30
            state.recurring_income.append(evt)

    for evt in state.confirmed_events + state.future_events:
        if evt.direction == 'debit' and evt.is_recurring:
            state.recurring_expenses.append(evt)

    return state
