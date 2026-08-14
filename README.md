# Fantasy Esports + FinTech Wallet Analytics Pipeline

An end-to-end data science & engineering portfolio project simulating a subscription-based fantasy esports platform with an embedded digital wallet — combining gaming engagement data with FinTech transaction data under one product.

## Business Context

The product: a fantasy esports platform (think DraftKings-for-esports) with three subscription tiers (Basic/Pro/Elite) and a built-in wallet for tournament entry fees, deposits, and prize payouts. This creates two data domains under one roof:

- **Gaming engagement** — logins, tournament entries, league activity (drives churn risk)
- **FinTech transactions** — deposits, withdrawals, entry fees, payouts (drives fraud/risk-scoring)

Every phase of this project is built to answer a real business question a founder or hiring manager would actually ask — not just to demonstrate a tool.

## Tech Stack

| Layer | Tools |
|---|---|
| Ingestion | Python, Stripe API (test mode) |
| Data simulation | Faker, NumPy |
| Transformation | dbt, Databricks (Lakehouse) |
| Analysis | SQL |
| Dashboarding | Power BI |
| Modeling | scikit-learn, MLflow (Databricks) |
| Orchestration | Airflow |
| Deployment | Docker, FastAPI |
| Experimentation | GrowthBook, scipy |
| Version control | Git / GitHub |

## Project Phases

This repo is built incrementally — each tagged release (`v1`-`v7`) adds one new capability on top of the last, so the commit history itself shows the build process:

- **v1** — Python + Git scaffolding, Stripe API ingestion (customers, subscriptions, invoices)
- **v2** — dbt models on Databricks (staging -> marts: MRR, cohort retention, feature usage)
- **v3** — SQL optimization + Power BI churn/retention dashboard
- **v4** — scikit-learn churn prediction model (tracked via MLflow on Databricks), with dollar-impact estimate on retained revenue
- **v5** — Airflow DAG orchestrating the full pipeline on a schedule
- **v6** — Dockerized model serving via a FastAPI endpoint
- **v7** — A/B testing: simulated pricing/onboarding experiments with proper power analysis and sample-size calculations

## Data Note

All customer, subscription, and transaction data in this project is synthetically generated (via Stripe's test mode plus Faker/NumPy simulation) for portfolio purposes. No real user data is used anywhere in this repository.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file (excluded from version control via `.gitignore`) with:

```
STRIPE_API_KEY=sk_test_...
```

Then run the pipeline in order:

```bash
python stripe_ingest.py
python generate_usage_events.py
```

## Author

Summer — [GitHub](https://github.com/summer725)
