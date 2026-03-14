import os
import numpy as np
import pandas as pd

try:
    import joblib
    _USE_JOBLIB = True
except ImportError:
    _USE_JOBLIB = False

DEFAULT_FEATURE_ORDER = [
    "recency", "frequency", "monetary", "avg_basket",
    "avg_items", "total_items", "num_products", "days_active",
    "purchase_rate", "pct_web", "pct_mobile", "pct_instore"
]


# ── Loaders ──────────────────────────────────────────────────────────────────

def _pkl_load(path):
    if _USE_JOBLIB:
        import joblib
        return joblib.load(path)
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)


def load_model(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Model file '{path}' not found. Place best_model.pkl in the project root."
        )
    return _pkl_load(path)


def load_feature_cols(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Feature cols file '{path}' not found. Place feature_cols.pkl in the project root."
        )
    return list(_pkl_load(path))


def load_data(path: str):
    """Load training snapshot CSV. Returns None if file not found."""
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path, encoding="latin1")
    except Exception as e:
        print(f"[ERROR] Could not load {path}: {e}")
        return None


# ── Inference ─────────────────────────────────────────────────────────────────

def predict_from_features(model, features: list) -> dict:
    X   = np.array(features, dtype=float).reshape(1, -1)
    raw = model.predict(X)[0]
    if hasattr(raw, "item"):
        raw = raw.item()
    return {"predicted_spend": round(float(raw), 2)}


# ── Feature engineering from uploaded CSV ─────────────────────────────────────

def _infer_channel(hour: int) -> str:
    """
    Infer channel from transaction hour (same heuristic used in training):
      06-12  → Web
      12-18  → In-store
      18-24  → Mobile
      00-06  → Mobile
    """
    if 6 <= hour < 12:
        return "Web"
    elif 12 <= hour < 18:
        return "In-store"
    else:
        return "Mobile"


def build_features_from_csv(df: pd.DataFrame, cutoff_date, feature_order=None) -> tuple:
    """
    Build the 12-feature vector from a raw transaction DataFrame.

    Required columns : InvoiceDate, Quantity, UnitPrice
    Optional columns : TotalAmount, Channel

    Returns (features_list, constructed_dict)
    """
    REQUIRED = {"InvoiceDate", "Quantity", "UnitPrice"}
    missing_cols = REQUIRED - set(df.columns)
    if missing_cols:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing_cols))}")

    df = df.copy()

    # Parse dates
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format="mixed", errors="coerce")
    df = df.dropna(subset=["InvoiceDate"])

    # Filter to on or before cutoff
    df = df[df["InvoiceDate"] <= pd.Timestamp(cutoff_date)]
    if df.empty:
        raise ValueError(f"No transactions found on or before {cutoff_date}.")

    # Ensure numeric
    df["Quantity"]  = pd.to_numeric(df["Quantity"],  errors="coerce").fillna(0)
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce").fillna(0)
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    if df.empty:
        raise ValueError("No valid transactions (Quantity > 0, UnitPrice > 0) found.")

    # TotalAmount
    if "TotalAmount" not in df.columns:
        df["TotalAmount"] = df["Quantity"] * df["UnitPrice"]
    else:
        df["TotalAmount"] = pd.to_numeric(df["TotalAmount"], errors="coerce").fillna(
            df["Quantity"] * df["UnitPrice"]
        )

    # Channel
    if "Channel" not in df.columns:
        df["Channel"] = df["InvoiceDate"].dt.hour.apply(_infer_channel)

    # ── Compute features ──
    cutoff_ts = pd.Timestamp(cutoff_date)

    # Use InvoiceNo if present (for grouping orders), else treat each row as an order
    if "InvoiceNo" in df.columns:
        invoice_groups = df.groupby("InvoiceNo")
        frequency    = invoice_groups.ngroups
        first_date   = df["InvoiceDate"].min()
        last_date    = df["InvoiceDate"].max()
        monetary     = df["TotalAmount"].sum()
        total_items  = df["Quantity"].sum()
        avg_items    = total_items / frequency
        avg_basket   = monetary / frequency
    else:
        frequency    = len(df)
        first_date   = df["InvoiceDate"].min()
        last_date    = df["InvoiceDate"].max()
        monetary     = df["TotalAmount"].sum()
        total_items  = df["Quantity"].sum()
        avg_items    = total_items / frequency
        avg_basket   = monetary / frequency

    recency      = (cutoff_ts - last_date).days
    days_active  = max((last_date - first_date).days, 1)
    purchase_rate = frequency / days_active

    # Unique products
    if "StockCode" in df.columns:
        num_products = df["StockCode"].nunique()
    elif "Description" in df.columns:
        num_products = df["Description"].nunique()
    else:
        num_products = min(frequency, int(total_items))

    # Channel fractions
    ch_counts   = df["Channel"].str.lower().value_counts(normalize=True)
    pct_web     = float(ch_counts.get("web",      0))
    pct_mobile  = float(ch_counts.get("mobile",   0))
    pct_instore = float(ch_counts.get("in-store", 0) +
                        ch_counts.get("instore",  0) +
                        ch_counts.get("in store", 0))

    constructed = {
        "recency":       int(recency),
        "frequency":     int(frequency),
        "monetary":      round(float(monetary), 2),
        "avg_basket":    round(float(avg_basket), 4),
        "avg_items":     round(float(avg_items), 4),
        "total_items":   int(total_items),
        "num_products":  int(num_products),
        "days_active":   int(days_active),
        "purchase_rate": round(float(purchase_rate), 6),
        "pct_web":       round(pct_web, 4),
        "pct_mobile":    round(pct_mobile, 4),
        "pct_instore":   round(pct_instore, 4),
    }

    order = feature_order if feature_order else DEFAULT_FEATURE_ORDER
    features = [constructed[f] for f in order]
    return features, constructed
