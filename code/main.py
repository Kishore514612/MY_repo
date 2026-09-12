import os
import sys
import pandas as pd
from datetime import datetime

# Adjust sys.path to ensure local package imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.dates import parse_date
from utils.currency import CurrencyConverter
from data_loader import DataLoader
from vision_extractor import VisionExtractor
from financial_state import build_financial_state
from forecaster import Forecaster
from plan_generator import generate_candidate_plans
from plan_validator import validate_plan
from plan_ranker import rank_plans
from decision_maker import assemble_decision

def run_pipeline(dataset_dir: str, output_csv_path: str, usage_report_path: str):
    loader = DataLoader(dataset_dir)
    data = loader.load_all()

    requests_df = data.get("requests", pd.DataFrame())
    profiles_df = data.get("financial_profiles", pd.DataFrame())
    events_df = data.get("financial_events", pd.DataFrame())
    exchange_rates_df = data.get("exchange_rates", pd.DataFrame())
    payment_options_df = data.get("request_payment_options", pd.DataFrame())
    messages_df = data.get("messages", pd.DataFrame())
    images_df = data.get("images", pd.DataFrame())

    converter = CurrencyConverter(exchange_rates_df)
    vision_extractor = VisionExtractor(images_df)
    forecaster = Forecaster(forecast_days=90)

    results = []
    
    total_requests = len(requests_df)
    print(f"Processing {total_requests} financial requests...")

    for idx, row in requests_df.iterrows():
        req_id = str(row['request_id']).strip()
        u_id = str(row['user_id']).strip()
        req_date = parse_date(row['request_date'])
        req_amount = float(row['requested_amount'])
        desired_comp_date = parse_date(row.get('desired_completion_date')) or req_date
        
        allows_partial_raw = str(row.get('allows_partial_payment', 'false')).strip().lower()
        allows_partial = allows_partial_raw in ('true', '1', 'yes')

        # 1. Build normalized FinancialState
        state = build_financial_state(
            user_id=u_id,
            profiles_df=profiles_df,
            events_df=events_df,
            messages_df=messages_df,
            converter=converter,
            vision_extractor=vision_extractor,
            eval_date=req_date
        )

        # 2. Forecaster baseline capacity metrics
        amt_safe_today = forecaster.calculate_amount_safe_to_pay_today(state, req_date, req_amount)
        earliest_full_d = forecaster.calculate_earliest_full_date(state, req_date, req_amount)

        # 3. Generate candidate plans
        candidates = generate_candidate_plans(
            request_id=req_id,
            requested_amount=req_amount,
            request_date=req_date,
            desired_completion_date=desired_comp_date,
            allows_partial_payment=allows_partial,
            payment_options_df=payment_options_df,
            state=state,
            amount_safe_to_pay_today=amt_safe_today,
            earliest_full_date=earliest_full_d
        )

        # 4. Validate & Filter safe candidate plans
        safe_valid_plans = []
        for plan in candidates:
            is_valid, msg = validate_plan(plan, state, allows_partial)
            if is_valid:
                if forecaster.is_plan_safe(plan, state, req_date):
                    safe_valid_plans.append(plan)

        # 5. Rank valid safe plans
        winning_plan = rank_plans(safe_valid_plans, desired_comp_date)

        # 6. Assemble final output record
        out_dict = assemble_decision(
            request_id=req_id,
            requested_amount=req_amount,
            request_date=req_date,
            desired_completion_date=desired_comp_date,
            state=state,
            amount_safe_to_pay_today=amt_safe_today,
            earliest_full_date=earliest_full_d,
            winning_plan=winning_plan
        )

        results.append(out_dict)

    # Required output columns in exact order
    output_cols = [
        "request_id",
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
        "decision_explanation"
    ]

    out_df = pd.DataFrame(results)[output_cols]
    out_df.to_csv(output_csv_path, index=False)
    print(f"Successfully generated {output_csv_path} with {len(out_df)} rows.")

    # Generate token usage report
    write_usage_report(usage_report_path, total_requests)

def write_usage_report(report_path: str, total_requests: int):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report_content = f"""# Token Usage and Cost Analysis

## Summary
- **Evaluation Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Total Requests Evaluated**: {total_requests}

## Model Usage Breakdown

| Provider | Model Name | Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|---|
| Rule-Engine / Hybrid Vision | Deterministic Vision + Rule Engine | {total_requests} | 0 | 0 | 0 | $0.0000 |

## Per-Request Metrics
- **Average Input Tokens per Request**: 0
- **Average Output Tokens per Request**: 0
- **Estimated Total Cost**: $0.0000
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Successfully generated token usage report at {report_path}.")

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dataset_dir = os.path.join(repo_root, "dataset")
    output_csv_path = os.path.join(repo_root, "output.csv")
    usage_report_path = os.path.join(repo_root, "evaluation", "usage_report.md")

    run_pipeline(dataset_dir, output_csv_path, usage_report_path)
