import os
import json
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import entropy
from data import process_csv_file   # from your refactored data.py

from support import generate
# ==========================================================
#  Column Processors
# ==========================================================
def ensure_plots_dir(job_id: str):
    # Always build the full directory
    base_dir = f"/storage/outputs/{job_id}/plots"
    
    # Create the full directory tree if missing
    os.makedirs(base_dir, exist_ok=True)
    
    return base_dir


# --- use it like this ---

def process_numerical(df, col, job_id):
    s = df[col].dropna()

    stats = {
        "column_name": col,
        "mean": float(s.mean()),
        "median": float(s.median()),
        "mode": float(s.mode().iloc[0]) if not s.mode().empty else None,
        "std": float(s.std()),
        "min": float(s.min()),
        "max": float(s.max()),
        "skewness": float(s.skew()),
        "kurtosis": float(s.kurt()),
        "missing_values": int(df[col].isna().sum()),
        "unique_values": int(s.nunique()),
    }

    # Save plots into outputs/{job_id}/plots/
     # Create plots directory
    plots_dir = ensure_plots_dir(job_id)
    

    plot_path = os.path.join(plots_dir, f"{col}.png")
    plot_path = plot_path.replace("\\", "/")
    plt.figure(figsize=(6, 4))
    if stats["unique_values"] > 20 and abs(stats["skewness"]) < 2:
        sns.histplot(s, kde=True, bins=30)
        plt.title(f"Histogram of {col}")
    elif stats["unique_values"] > 20 and abs(stats["skewness"]) >= 2:
        sns.boxplot(x=s)
        plt.title(f"Boxplot of {col} (Skewed)")
    else:
        s.value_counts().plot(kind="bar")
        plt.title(f"Bar Chart of {col}")

    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    stats["plot_path"] = plot_path
    return stats


def process_categorical(df, col, job_id):
    s = df[col].dropna()
    value_counts = s.value_counts(dropna=False)
    percentages = value_counts / value_counts.sum() * 100

    stats = {
        "column_name": col,
        "unique_values": int(s.nunique(dropna=False)),
        "most_frequent": str(value_counts.idxmax()) if not value_counts.empty else None,
        "most_frequent_count": int(value_counts.max()) if not value_counts.empty else None,
        "least_frequent": str(value_counts.idxmin()) if not value_counts.empty else None,
        "least_frequent_count": int(value_counts.min()) if not value_counts.empty else None,
        "missing_values": int(df[col].isna().sum()),
        "entropy": float(entropy(value_counts)) if not value_counts.empty else None,
    }
    if stats["unique_values"] < 10:
        stats["value_distribution"] = value_counts.to_dict()

    plots_dir = ensure_plots_dir(job_id)
    

    plot_path = os.path.join(plots_dir, f"{col}.png")
    plot_path = plot_path.replace("\\", "/")

    plot_path = os.path.join(plots_dir, f"{col}.png")
    plot_path = plot_path.replace("\\", "/")

    plt.figure(figsize=(6, 4))
    if stats["unique_values"] <= 5 and percentages.max() < 80:
        value_counts.plot(kind="pie", autopct="%1.1f%%")
        plt.ylabel("")
        plt.title(f"Pie Chart of {col}")
    else:
        value_counts.head(10).plot(kind="bar")
        plt.title(f"Bar Chart of {col} (Top 10)")
        plt.ylabel("Count")

    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    stats["plot_path"] = plot_path
    return stats


def process_datetime(df, col, job_id):
    df[col] = pd.to_datetime(df[col], errors="coerce")
    series = df[col].dropna().sort_values()

    stats = {"column_name": col, "missing_values": int(df[col].isna().sum())}
    if series.empty:
        stats.update({"error": "No valid dates"})
        return stats

    gaps = series.diff().dropna().dt.days
    stats.update({
        "min_date": str(series.min().date()),
        "max_date": str(series.max().date()),
        "time_span_days": int((series.max() - series.min()).days),
        "most_frequent_date": str(series.value_counts().idxmax().date()),
        "repeated_dates": int((series.value_counts() > 1).sum()),
        "avg_gap_days": float(gaps.mean()) if not gaps.empty else None,
        "median_gap_days": float(gaps.median()) if not gaps.empty else None,
    })

    plots_dir = ensure_plots_dir(job_id)
    

    plot_path = os.path.join(plots_dir, f"{col}.png")
    plot_path = plot_path.replace("\\", "/")

    plot_path = os.path.join(plots_dir, f"{col}.png")
    plot_path = plot_path.replace("\\", "/")

    plt.figure(figsize=(8, 4))
    if stats["time_span_days"] > 365:
        series.groupby(series.dt.to_period("Y")).count().plot()
        plt.title(f"Yearly Trend of {col}")
    else:
        series.value_counts().sort_index().plot()
        plt.title(f"Daily Trend of {col}")

    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    stats["plot_path"] = plot_path
    return stats


# ==========================================================
#  Insights Generator
# ==========================================================
def generate_insights(df, num_cols, cat_cols, datetime_cols, job_id, save_json=True):
    insights = {"numerical": {}, "categorical": {}, "datetime": {}}

    for col in num_cols:
        insights["numerical"][col] = process_numerical(df, col, job_id)

    for col in cat_cols:
        insights["categorical"][col] = process_categorical(df, col, job_id)

    for col in datetime_cols:
        insights["datetime"][col] = process_datetime(df, col, job_id)

    if save_json:
        save_dir = os.path.join("storage/outputs", job_id)
        os.makedirs(save_dir, exist_ok=True)
        insights_path = os.path.join(save_dir, "insights.json")
        with open(insights_path, "w") as f:
            json.dump(insights, f, indent=2)

    return insights


# ==========================================================
#  UVI Runner
# ==========================================================
def run_uvi(file_path, job_id="uvi_job", output_dir="outputs"):
    """
    Runs data.py for description and generates insights with plots.
    Saves description.json + insights.json + plots/ under outputs/{job_id}/.
    """
    file_path = f'storage/uploads/{job_id}/input.csv'
    file_path=str(file_path)

    # 1. Description from data.py
    description_json, success = process_csv_file(job_id, file_path)
    if not success:
        return {"error": "processing failed", "details": description_json, "success": False}

    # 2. Extract column types
    col_types = description_json.get("data_type_tuples", {})
    num_cols = list(col_types.get("numerical", []))
    cat_cols = list(col_types.get("categorical", []))
    dt_cols = list(col_types.get("datetime", []))

    # 3. Load dataframe
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # 4. Generate insights (with plots)
    top_features_data, top_numerical_cols, top_categorical_cols, top_datetime_cols = generate(df)
    insights=generate_insights(df,top_numerical_cols, top_categorical_cols, top_datetime_cols,job_id)
    # 5. Save description.json
    save_dir = os.path.join(output_dir, job_id)
    os.makedirs(save_dir, exist_ok=True)
    desc_path = os.path.join(save_dir, "description.json")
    with open(desc_path, "w") as f:
        json.dump(description_json, f, indent=2)

    # 6. Return combined results
    return {
        "description": description_json,
        "feature_insights": insights,
        "numerical_columns": num_cols,
        "categorical_columns": cat_cols,
        "datetime_columns": dt_cols,
        "paths": {
            "description_json": desc_path,
            "insights_json": os.path.join(save_dir, "insights.json"),
            "plots_dir": os.path.join(save_dir, "plots")
        },
        "success": True
    }


# ==========================================================
#  CLI Test
# ==========================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python uvi.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    job_id = "manual_test"

    result = run_uvi(file_path, job_id=job_id)
    print("✅ UVI Result:")
    print(json.dumps(result, indent=2))