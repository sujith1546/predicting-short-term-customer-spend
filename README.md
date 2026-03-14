# Online Retail Customer Spend Prediction

This project implements a machine learning pipeline to predict future customer spending using the **Online Retail** dataset. The goal is to forecast a customer's total spend over the next 30 days based on their historical transaction data, enriched with synthetic channel information (Web, Mobile, In‑store). The system supports predictions for both existing customers (using stored snapshots) and new customers (by uploading raw transaction files).

## 📌 Overview

The notebook covers the complete workflow:
- Data loading, cleaning, and exploratory data analysis (EDA)
- Synthetic `Channel` column generation based on transaction hour
- Feature engineering (RFM‑like metrics and channel proportions)
- Multi‑cutoff training data creation – for each day, we compute features from all past transactions and the target is the total spend in the following 30 days
- Training and evaluation of multiple regression models
- Prediction functions for existing customers (using historical snapshots) and new customers (from uploaded CSV)

The best performing model is a **Random Forest Regressor** with an R² of **0.883** on the test set.

## 📊 Dataset

The dataset used is the **Online Retail** dataset (UCI Machine Learning Repository). It contains transaction records from a UK‑based online retailer between 01/12/2010 and 09/12/2011.  
After cleaning, the data consists of **397,884** transactions from **4,338** unique customers.

### Original Columns
- `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`

## 🛠️ Steps Performed

1. **Environment Setup** – Install required libraries (`xgboost`, `lightgbm`, `scikit‑learn`).
2. **Data Loading** – Upload a CSV file and load it with `latin1` encoding.
3. **Data Cleaning**  
   - Remove rows without `CustomerID`  
   - Exclude cancelled invoices (those starting with `C`)  
   - Keep only positive `Quantity` and `UnitPrice`  
   - Create `TotalAmount = Quantity * UnitPrice`
4. **Exploratory Data Analysis (EDA)** – Extensive visual analysis of sales, products, customers, and time patterns.
5. **Synthetic Channel Column** – Based on transaction hour, randomly assign a channel (`Web`, `Mobile`, `In‑store`) with different probabilities for business hours (9‑17) vs. off‑hours.
6. **Feature Engineering Functions**  
   - Compute **recency**, **frequency**, **monetary**, **avg_basket**, **avg_items**, **total_items**, **num_products**, **days_active**, **purchase_rate**.  
   - Calculate **channel proportions** (`pct_web`, `pct_mobile`, `pct_instore`).
7. **Multi‑Cutoff Training Data**  
   - For every day in the dataset (ensuring a 30‑day future window exists), we take all transactions **up to that day** as the “past” and compute features for each customer.  
   - The target is the total spend in the **next 30 days**.  
   - This yields **839,792** training rows (each customer appears many times).
8. **Model Training & Evaluation**  
   - Split into train/test (80/20).  
   - Train six regression models: Linear Regression, Ridge, Random Forest, Gradient Boosting, XGBoost, LightGBM.  
   - Compare using **MAE**, **RMSE**, **R²**.  
   - **Random Forest** achieves the best performance (R² = 0.883).
9. **Prediction Functions**  
   - `predict_existing(customer_id, cutoff_date)` – retrieves the most recent snapshot for that customer before or on the given cutoff and predicts future spend.  
   - `predict_new_from_transactions(transactions_df, cutoff_date)` – builds features from raw transactions (with automatic channel assignment if missing) and predicts.
10. **Demo Cells** – Interactive examples for both existing and new customers.
11. **Model Export** – Save the trained model and feature list using `joblib` and download them.

## 📈 Model Performance

| Model               | MAE     | RMSE    | R²     |
|---------------------|---------|---------|--------|
| Linear Regression   | 228.52  | 857.50  | 0.4506 |
| Ridge               | 228.52  | 857.50  | 0.4506 |
| Random Forest       | **181.83** | **395.98** | **0.8828** |
| Gradient Boosting   | 192.75  | 447.72  | 0.8502 |
| XGBoost             | 186.16  | 428.75  | 0.8626 |
| LightGBM            | 185.72  | 430.97  | 0.8612 |

## 🧠 How to Use

### 1. Run the notebook in Google Colab
- Open the notebook in Colab.
- Execute cells sequentially.
- When prompted, upload your CSV file (the notebook expects the standard Online Retail format).

### 2. Predict for an existing customer
- After training, a cell will ask for a customer ID and a cutoff date.
- The model will return the predicted spend and the actual spend (if available in the training data).

### 3. Predict for a new customer
- Upload a CSV file containing at least `InvoiceDate`, `Quantity`, and `UnitPrice`.
- The system will automatically compute `TotalAmount` and assign a channel based on the transaction hour.
- Enter a cutoff date to get a prediction.

### 4. Save and download the model
- The final cell exports the best model as `best_model.pkl` and the feature list as `feature_cols.pkl` for later use.

## 📦 Requirements

- Python 3.7+
- Libraries: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scikit‑learn`, `xgboost`, `lightgbm`, `joblib`

All dependencies are installed in the first cell of the notebook.

## 📁 Files in the Repository

- `Untitled17.ipynb` – The complete Jupyter notebook.
- `best_model.pkl` – Trained Random Forest model (generated after execution).
- `feature_cols.pkl` – List of feature column names.
- `README.md` – This file.

## 📝 License

This project is for educational purposes. The dataset is from the UCI Machine Learning Repository and is publicly available.
