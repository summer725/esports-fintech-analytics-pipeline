"""
Phase 1 ingestion script: pulls customer, subscription, and invoice data
from Stripe's test-mode API and saves it locally as CSV.

Product theme: a gamified investing/savings app (Basic / Plus / Premium
tiers). Alongside raw entity data, this script also rolls up Monthly
Recurring Revenue (MRR) by tier — the core metric a founder or investor
would actually track for a subscription business, and the natural
business-framing anchor for your dbt marts and Power BI dashboard later.

Setup:
  pip install stripe pandas
  export STRIPE_API_KEY="sk_test_..."   # your test secret key
"""

import os
import stripe
import pandas as pd

stripe.api_key = os.environ["STRIPE_API_KEY"]

# Map each tier's Stripe Price ID to its monthly amount, so MRR can be
# computed straight from active subscription counts without re-querying
# Stripe for every price lookup. Fill in your real price_... IDs from the
# Dashboard after creating your three Prices.
TIER_PRICES = {
    "price_basic_id_here": {"tier": "basic", "monthly_amount": 9},
    "price_plus_id_here": {"tier": "plus", "monthly_amount": 19},
    "price_premium_id_here": {"tier": "premium", "monthly_amount": 39},
}


def fetch_customers() -> pd.DataFrame:
    customers = stripe.Customer.list(limit=100).auto_paging_iter()
    rows = [
        {
            "customer_id": c.id,
            "created": c.created,
            "email": c.email,
        }
        for c in customers
    ]
    return pd.DataFrame(rows)


def fetch_subscriptions() -> pd.DataFrame:
    subs = stripe.Subscription.list(status="all", limit=100).auto_paging_iter()
    rows = [
        {
            "subscription_id": s.id,
            "customer_id": s.customer,
            "status": s.status,
            "plan_id": s["items"]["data"][0]["price"]["id"] if s["items"]["data"] else None,
            "current_period_start": s.current_period_start,
            "current_period_end": s.current_period_end,
            "canceled_at": s.canceled_at,
        }
        for s in subs
    ]
    return pd.DataFrame(rows)


def fetch_invoices() -> pd.DataFrame:
    invoices = stripe.Invoice.list(limit=100).auto_paging_iter()
    rows = [
        {
            "invoice_id": i.id,
            "customer_id": i.customer,
            "subscription_id": i.subscription,
            "amount_paid": i.amount_paid / 100,  # cents -> dollars
            "status": i.status,
            "created": i.created,
        }
        for i in invoices
    ]
    return pd.DataFrame(rows)


def compute_mrr_summary(subs_df: pd.DataFrame) -> pd.DataFrame:
    """Rolls up Monthly Recurring Revenue by tier, using only active subscriptions.
    This is the metric your Power BI dashboard and dbt marts should be built around —
    it's what a founder actually checks, not raw row counts."""
    active = subs_df[subs_df["status"] == "active"].copy()
    active["tier"] = active["plan_id"].map(lambda p: TIER_PRICES.get(p, {}).get("tier", "unknown"))
    active["monthly_amount"] = active["plan_id"].map(
        lambda p: TIER_PRICES.get(p, {}).get("monthly_amount", 0)
    )

    summary = (
        active.groupby("tier")
        .agg(active_subscribers=("customer_id", "count"), mrr=("monthly_amount", "sum"))
        .reset_index()
    )
    summary.loc["total"] = ["total", summary["active_subscribers"].sum(), summary["mrr"].sum()]
    return summary


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    customers = fetch_customers()
    subscriptions = fetch_subscriptions()
    invoices = fetch_invoices()
    mrr_summary = compute_mrr_summary(subscriptions)

    customers.to_csv("data/raw/customers.csv", index=False)
    subscriptions.to_csv("data/raw/subscriptions.csv", index=False)
    invoices.to_csv("data/raw/invoices.csv", index=False)
    mrr_summary.to_csv("data/raw/mrr_summary.csv", index=False)

    print("Pulled Stripe test-mode data into data/raw/")
    print(mrr_summary)
