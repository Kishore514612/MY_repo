# Buy or Wait? Financial Decision Agent Codebase

This directory contains the Python implementation of the **Buy or Wait?** AI-powered financial agent for the HackerRank Orchestrate challenge (September 2026).

---

## 🏗️ Architecture Overview

The system processes financial requests by converting raw transaction events, user preferences, exchange rates, and multimodal evidence into a normalized financial state, then evaluating payment feasibility over a 90-day forecast.

```text
code/
├── main.py                     # Entry point & full dataset execution pipeline
├── data_loader.py              # Ingests CSV datasets from dataset/
├── vision_extractor.py         # Image amount resolution module
├── financial_state.py          # Builds normalized FinancialState object
├── forecaster.py               # 90-day cash flow simulation engine ("Is this plan safe?")
├── plan_generator.py          # Candidate payment plan generator ("What plans can we try?")
├── plan_validator.py          # Constraint & preference validator ("Does plan obey rules?")
├── plan_ranker.py             # Evaluates & ranks safe candidate plans ("Which plan is best?")
├── decision_maker.py          # Formats final output fields & grounded explanations
│
├── utils/
│   ├── currency.py             # Foreign currency conversion using exchange_rates.csv
│   ├── dates.py                # Date parsing, formatting, and arithmetic
│   └── formatting.py           # Output string formatters for payment plans & spending changes
│
└── tests/
    └── test_financial_pipeline.py  # Unit test suite
```

---

## 🛠️ Module Responsibilities

1. **`financial_state.py`**:
   - Parses user profiles and historical transactions into a normalized `FinancialState` object containing `balance`, `minimum_balance`, `currency`, `recurring_income`, `recurring_expenses`, `confirmed_events`, `pending_events`, `cancelled_events`, `flexible_expenses`, and `future_events`.
   - Resolves transaction conflicts (settled > forecast, newer records, explicit cancellations).

2. **`forecaster.py`**:
   - Performs a daily balance cash flow simulation from `request_date` to `request_date + 90 days`.
   - Computes `amount_safe_to_pay` on request date before optional spending changes.
   - Computes `earliest_date_for_full_payment` (first date a single full payment passes safety check).

3. **`plan_generator.py`**:
   - Generates candidate payment options (`full_payment`, `partial_payment`, `installments`, `wait`).
   - Generates permitted flexible spending changes (`stop:<event_id>`, `reduce_to:<event_id>:<new_amount>`).

4. **`plan_validator.py`**:
   - Enforces user payment preferences (`payment_methods_user_will_consider`, `max_installment_months`).
   - Validates partial payment rules (`0 < amount_safe_to_pay < requested_amount`).
   - Ensures spending changes target flexible, non-protected categories only.

5. **`plan_ranker.py`**:
   - Orders safe candidate plans using the 6 challenge criteria:
     1. Completion by `desired_completion_date`
     2. 0 spending changes required
     3. Minimum total amount paid
     4. Earlier start date
     5. Fewer payments
     6. Lowest `payment_option_id` tie-breaker

6. **`decision_maker.py`**:
   - Formats final prediction dictionary matching the required `output.csv` schema.

---

## 🚀 Quick Start & Execution

### Prerequisites
- Python 3.8+
- `pandas` library (`pip install pandas`)

### Run the Evaluation Pipeline
From the repository root directory, execute:

```bash
python code/main.py
```

This will process all 250 requests in `dataset/requests.csv` and generate:
- `output.csv` (Root-level predictions file)
- `evaluation/usage_report.md` (Token usage & cost report)

### Run Unit Tests
To run the automated test suite:

```bash
python -m unittest discover -s code/tests
```
