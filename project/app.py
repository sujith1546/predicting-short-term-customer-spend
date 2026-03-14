import os
import io
import pandas as pd
from flask import Flask, request, jsonify, render_template
from model_loader import (
    load_model, load_feature_cols,
    predict_from_features, build_features_from_csv,
    load_data
)

app = Flask(__name__)

# ── Load model at startup ──────────────────────────────────────────────────
MODEL_PATH        = "best_model.pkl"
FEATURE_COLS_PATH = "feature_cols.pkl"
DATA_PATH         = "data.csv"    # Training snapshot CSV (for existing customers)

try:
    model        = load_model(MODEL_PATH)
    feature_cols = load_feature_cols(FEATURE_COLS_PATH)
    print(f"[INFO] Model loaded. Feature order: {feature_cols}")
except FileNotFoundError as _e:
    print(f"[WARNING] {_e}")
    model        = None
    feature_cols = None

data = load_data(DATA_PATH)   # Returns None if file doesn't exist


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Existing Customer — CustomerID + Cutoff Date
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/predict/existing", methods=["POST"])
def predict_existing():
    if model is None:
        return jsonify({"error": "Model not loaded. Place best_model.pkl in the project folder and restart."}), 503

    body        = request.get_json(force=True) or {}
    customer_id = str(body.get("customer_id", "")).strip()
    cutoff_str  = str(body.get("cutoff_date", "")).strip()

    if not customer_id:
        return jsonify({"error": "customer_id is required."}), 400
    if not cutoff_str:
        return jsonify({"error": "cutoff_date is required (YYYY-MM-DD)."}), 400

    try:
        cutoff_date = pd.to_datetime(cutoff_str)
    except Exception:
        return jsonify({"error": f"Invalid cutoff_date '{cutoff_str}'. Use YYYY-MM-DD format."}), 400

    if data is None:
        return jsonify({"error": "Historical data file (data.csv) not found on the server."}), 500

    id_col = "CustomerID" if "CustomerID" in data.columns else data.columns[0]
    
    # In raw data, CustomerID is often parsed as a float like '17850.0'. 
    # Convert to string and strip '.0' for clean matching.
    clean_ids = data[id_col].astype(str).str.replace(r"\.0$", "", regex=True)
    subset = data[clean_ids == customer_id]
    
    if subset.empty:
        return jsonify({"error": f"No records found for CustomerID '{customer_id}'."}), 404

    # Build feature vector dynamically from the raw transactions
    try:
        f_order = feature_cols if feature_cols else None
        features, constructed = build_features_from_csv(subset, cutoff_date, f_order)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    prediction = predict_from_features(model, features)

    return jsonify({
        "mode":        "existing",
        "customer_id": customer_id,
        "cutoff_date": cutoff_str,
        "prediction":  prediction,
        "actual":      None,
        "snapshot":    constructed
    })


# ─────────────────────────────────────────────────────────────────────────────
# New Customer — CSV Upload + Cutoff Date
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/predict/new", methods=["POST"])
def predict_new():
    if model is None:
        return jsonify({"error": "Model not loaded. Place best_model.pkl in the project folder and restart."}), 503

    # Expect multipart/form-data
    if "csv_file" not in request.files:
        return jsonify({"error": "No CSV file uploaded. Please attach a file with key 'csv_file'."}), 400

    cutoff_str = request.form.get("cutoff_date", "").strip()
    if not cutoff_str:
        return jsonify({"error": "cutoff_date is required (YYYY-MM-DD)."}), 400

    try:
        cutoff_date = pd.to_datetime(cutoff_str)
    except Exception:
        return jsonify({"error": f"Invalid cutoff_date '{cutoff_str}'. Use YYYY-MM-DD format."}), 400

    csv_file = request.files["csv_file"]
    if csv_file.filename == "":
        return jsonify({"error": "Empty filename. Please upload a valid CSV file."}), 400

    try:
        content = csv_file.read().decode("utf-8", errors="replace")
        df      = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    # Build features from the uploaded transaction data
    try:
        f_order  = feature_cols if feature_cols else None
        features, constructed = build_features_from_csv(df, cutoff_date, f_order)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    prediction = predict_from_features(model, features)

    return jsonify({
        "mode":        "new",
        "cutoff_date": cutoff_str,
        "prediction":  prediction,
        "constructed": constructed
    })


if __name__ == "__main__":
    app.run(debug=True)
