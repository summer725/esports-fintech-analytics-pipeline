"""
Layers simulated behavioral usage events (logins, gaming-platform activity,
wallet transactions, support tickets) on top of the Stripe customer/
subscription data pulled by stripe_ingest.py.

Product: a subscription-based fantasy esports platform with an embedded
wallet. Two revenue streams: monthly subscription (Basic/Pro/Elite) and
transaction-based (entry fees, deposits, withdrawals, payouts) — this is
where the FinTech texture (fraud/risk signals) comes from, layered on a
gaming product.

Row count comes from EVENT granularity, not customer count — a few
thousand customers (dimension table) generate millions of individual
events (fact table). With the defaults below (5,000 customers x 90 days),
combining usage_events and wallet_transactions comfortably crosses 1M+ rows.

Setup:
  pip install faker pandas numpy
"""

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
rng = np.random.default_rng(seed=42)

TIER_LOGIN_LAMBDA = {"basic": 0.5, "pro": 1.5, "elite": 3.0}
TIER_GAMING_LAMBDA = {"basic": 2, "pro": 8, "elite": 20}
GAMING_EVENT_TYPES = ["tournament_entry", "league_created", "prediction_submitted",
                       "leaderboard_view", "roster_update"]

# Wallet: tier affects both deposit size and how often someone plays for money.
TIER_DEPOSIT_LAMBDA = {"basic": 0.2, "pro": 0.6, "elite": 1.2}
TIER_DEPOSIT_MEAN = {"basic": 15, "pro": 40, "elite": 100}

SUPPORT_TICKET_TEMPLATES = {
    "positive": ["Just upgraded, loving the new leaderboard!", "Quick question about billing."],
    "negative": ["This is too confusing, can't find my withdrawal.",
                 "Been waiting 3 days for a reply. Considering canceling."],
}


def simulate_usage_events(customers_df: pd.DataFrame, subs_df: pd.DataFrame,
                           days: int = 90) -> pd.DataFrame:
    """One row PER EVENT (not per customer-day) — this is what gets you to 1M+ rows."""
    merged = subs_df.merge(customers_df, on="customer_id")
    rows = []

    for _, row in merged.iterrows():
        tier = row.get("plan_id", "basic") or "basic"
        tier = "basic" if tier not in TIER_LOGIN_LAMBDA else tier
        will_churn = row["status"] == "canceled"

        for day in range(days):
            # Churning customers show declining engagement — the actual
            # signal your Phase 4 model should learn to detect.
            decay = max(0.1, 1 - day / days) if will_churn else 1.0

            n_logins = rng.poisson(TIER_LOGIN_LAMBDA[tier] * decay)
            for _ in range(n_logins):
                rows.append({
                    "customer_id": row["customer_id"],
                    "day": day,
                    "event_type": "login",
                    "detail": None,
                })

            n_gaming = rng.poisson(TIER_GAMING_LAMBDA[tier] * decay)
            for _ in range(n_gaming):
                rows.append({
                    "customer_id": row["customer_id"],
                    "day": day,
                    "event_type": rng.choice(GAMING_EVENT_TYPES),
                    "detail": None,
                })

    return pd.DataFrame(rows)


def simulate_wallet_transactions(customers_df: pd.DataFrame, subs_df: pd.DataFrame,
                                  days: int = 90) -> pd.DataFrame:
    """
    Deposits, entry fees, and withdrawals — the FinTech layer. A small
    fraction of accounts get flagged with a 'risk_flag' to give your later
    fraud/risk-scoring work something real to detect (e.g. rapid deposit
    -> withdrawal cycling, a classic laundering/fraud pattern).
    """
    merged = subs_df.merge(customers_df, on="customer_id")
    rows = []

    for _, row in merged.iterrows():
        tier = row.get("plan_id", "basic") or "basic"
        tier = "basic" if tier not in TIER_DEPOSIT_LAMBDA else tier
        is_flagged_risk = rng.random() < 0.02  # ~2% of accounts, realistic fraud base rate

        for day in range(days):
            n_deposits = rng.poisson(TIER_DEPOSIT_LAMBDA[tier])
            for _ in range(n_deposits):
                amount = round(float(rng.exponential(TIER_DEPOSIT_MEAN[tier])), 2)
                rows.append({
                    "customer_id": row["customer_id"],
                    "day": day,
                    "txn_type": "deposit",
                    "amount": amount,
                    "risk_flag": is_flagged_risk,
                })
                # Entry fee shortly after a deposit — normal platform behavior
                if rng.random() < 0.7:
                    rows.append({
                        "customer_id": row["customer_id"],
                        "day": day,
                        "txn_type": "entry_fee",
                        "amount": round(amount * rng.uniform(0.3, 0.9), 2),
                        "risk_flag": is_flagged_risk,
                    })
                # Flagged accounts get a rapid withdrawal right after depositing —
                # a classic fraud/laundering signal for your risk model to learn.
                if is_flagged_risk and rng.random() < 0.5:
                    rows.append({
                        "customer_id": row["customer_id"],
                        "day": day,
                        "txn_type": "withdrawal",
                        "amount": round(amount * rng.uniform(0.8, 1.0), 2),
                        "risk_flag": True,
                    })

            # Normal (non-fraud) withdrawals happen too, just less frequently/tightly coupled
            if not is_flagged_risk and rng.random() < 0.05:
                rows.append({
                    "customer_id": row["customer_id"],
                    "day": day,
                    "txn_type": "withdrawal",
                    "amount": round(float(rng.exponential(TIER_DEPOSIT_MEAN[tier])), 2),
                    "risk_flag": False,
                })

    return pd.DataFrame(rows)


def simulate_support_tickets(customers_df: pd.DataFrame, subs_df: pd.DataFrame) -> pd.DataFrame:
    """A handful of support tickets per customer, sentiment-weighted toward churners."""
    merged = subs_df.merge(customers_df, on="customer_id")
    rows = []

    for _, row in merged.iterrows():
        will_churn = row["status"] == "canceled"
        n_tickets = rng.integers(0, 4)

        for _ in range(n_tickets):
            sentiment = "negative" if (will_churn and rng.random() < 0.7) else "positive"
            rows.append({
                "customer_id": row["customer_id"],
                "created": fake.date_time_this_year(),
                "sentiment": sentiment,
                "ticket_text": rng.choice(SUPPORT_TICKET_TEMPLATES[sentiment]),
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    customers = pd.read_csv("data/raw/customers.csv")
    subs = pd.read_csv("data/raw/subscriptions.csv")

    # With ~5,000 customers x 90 days, combining usage + wallet events
    # comfortably exceeds 1M rows. Bump `days` if you have fewer Stripe
    # customers and still want to cross the 1M-row mark.
    usage = simulate_usage_events(customers, subs, days=90)
    wallet = simulate_wallet_transactions(customers, subs, days=90)
    tickets = simulate_support_tickets(customers, subs)

    print(f"Generated {len(usage):,} usage event rows")
    print(f"Generated {len(wallet):,} wallet transaction rows")
    print(f"Combined event rows: {len(usage) + len(wallet):,}")

    usage.to_csv("data/raw/usage_events.csv", index=False)
    wallet.to_csv("data/raw/wallet_transactions.csv", index=False)
    tickets.to_csv("data/raw/support_tickets.csv", index=False)
