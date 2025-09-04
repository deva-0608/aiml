import pandas as pd
import csv
import json
from scipy.stats import chi2_contingency


def dataset_feature_analysis(df, num_corr_threshold=0.7, chi2_p_threshold=0.05):
    """
    Performs feature analysis on a DataFrame, calculating correlation scores
    for numerical, categorical, and datetime columns.
    Returns a dictionary of feature scores and column types.
    """
    numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns.tolist()

    categorical_cols = [c for c in categorical_cols if df[c].nunique() < 50]

    feature_scores = {}
    
    if len(numerical_cols) > 1:
        pearson_corr = df[numerical_cols].corr(method="pearson").abs()
        num_scores = pearson_corr.max().to_dict()

        min_s, max_s = min(num_scores.values()), max(num_scores.values()) if num_scores else (0, 0)
        for col, score in num_scores.items():
            feature_scores[col] = (score - min_s) / (max_s - min_s) if max_s > min_s else 0.0

    if len(categorical_cols) > 1:
        cat_strength = {col: 0 for col in categorical_cols}
        for i, col1 in enumerate(categorical_cols):
            for col2 in categorical_cols[i + 1:]:
                table = pd.crosstab(df[col1], df[col2])
                if not table.empty and table.shape[0] > 1 and table.shape[1] > 1:
                    try:
                        _, p, _, _ = chi2_contingency(table)
                        score = 1 - p
                        cat_strength[col1] = max(cat_strength[col1], score)
                        cat_strength[col2] = max(cat_strength[col2], score)
                    except ValueError:
                        pass
        min_s, max_s = min(cat_strength.values()), max(cat_strength.values()) if cat_strength else (0, 0)
        for col, score in cat_strength.items():
            feature_scores[col] = (score - min_s) / (max_s - min_s) if max_s > min_s else 0.0

    if len(datetime_cols) > 0:
        dt_scores = {}
        for col in datetime_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            year_var = df[col].dt.year.var() if hasattr(df[col].dt, "year") else 0
            month_var = df[col].dt.month.var() if hasattr(df[col].dt, "month") else 0
            day_var = df[col].dt.day.var() if hasattr(df[col].dt, "day") else 0
            dt_scores[col] = year_var + month_var + day_var

        min_s, max_s = min(dt_scores.values()), max(dt_scores.values())
        for col, score in dt_scores.items():
            feature_scores[col] = (score - min_s) / (max_s - min_s) if max_s > min_s else 0.0

    col_types = {col: "numerical" for col in numerical_cols}
    col_types.update({col: "categorical" for col in categorical_cols})
    col_types.update({col: "datetime" for col in datetime_cols})

    return {
        "feature_scores": feature_scores,
        "col_types": col_types,
    }


def get_top_features(df, top_num=2, top_cat=2, top_dt=1):
    """
    Calls dataset_feature_analysis and extracts the top features, returning them as a dictionary.
    """
    report = dataset_feature_analysis(df)
    feature_scores = report["feature_scores"]
    col_types = report["col_types"]

    overall_ranked = sorted(
        feature_scores.items(), key=lambda item: item[1], reverse=True
    )
    overall_rank_dicts = [
        {"feature": col, "score": score, "type": col_types.get(col)}
        for col, score in overall_ranked
    ]

    top_numerical = sorted(
        [(col, score) for col, score in feature_scores.items() if col_types.get(col) == "numerical"],
        key=lambda item: item[1], reverse=True
    )[:top_num]
    top_numerical_dicts = [
        {"feature": col, "score": score} for col, score in top_numerical
    ]

    top_categorical = sorted(
        [(col, score) for col, score in feature_scores.items() if col_types.get(col) == "categorical"],
        key=lambda item: item[1], reverse=True
    )[:top_cat]
    top_categorical_dicts = [
        {"feature": col, "score": score} for col, score in top_categorical
    ]

    top_datetime = sorted(
        [(col, score) for col, score in feature_scores.items() if col_types.get(col) == "datetime"],
        key=lambda item: item[1], reverse=True
    )[:top_dt]
    top_datetime_dicts = [
        {"feature": col, "score": score} for col, score in top_datetime
    ]

    return {
        "overall_rank": overall_rank_dicts,
        "top_numerical_features": top_numerical_dicts,
        "top_categorical_features": top_categorical_dicts,
        "top_datetime_features": top_datetime_dicts,
    }


def generate(df, print_stats=True, save_json=True):
    """
    Main function to orchestrate the feature analysis and reporting.
    It returns the generated insights and the segregated top column lists.
    """
    top_features_data = get_top_features(df, top_num=2, top_cat=2, top_dt=1)

    # Extracting the names of the top features
    top_numerical_cols = [item['feature'] for item in top_features_data['top_numerical_features']]
    top_categorical_cols = [item['feature'] for item in top_features_data['top_categorical_features']]
    top_datetime_cols = [item['feature'] for item in top_features_data['top_datetime_features']]

    if print_stats:
        def print_table(title, data, headers):
            print(f"\n{title}\n")
            widths = {header: len(header) for header in headers}
            for item in data:
                for header in headers:
                    widths[header] = max(widths[header], len(str(item.get(header))))
            
            header_str = " | ".join(f"{h:<{widths[h]}}" for h in headers)
            print(header_str)
            print("-" * len(header_str))

            for item in data:
                row_str = " | ".join(f"{str(item.get(h, '')):<{widths[h]}}" for h in headers)
                print(row_str)
        
                
        print_table("Overall Feature Rank (All Types):", top_features_data["overall_rank"], headers=["feature", "score", "type"])
        print_table("Top Numerical Features:", top_features_data["top_numerical_features"], headers=["feature", "score"])
        print_table("Top Categorical Features:", top_features_data["top_categorical_features"], headers=["feature", "score"])
        print_table("Top Datetime Feature:", top_features_data["top_datetime_features"], headers=["feature", "score"])

    if save_json:
        def default_serializer(obj):
            if isinstance(obj, (float, pd.Series, pd.DataFrame)):
                return str(obj)
            raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
        try:
            with open("feature_insights.json", "w") as f:
                json.dump(top_features_data, f, indent=4, default=default_serializer)
            print("\nInsights saved to feature_insights.json")
        except TypeError as e:
            print(f"Error saving JSON file: {e}")

    return top_features_data, top_numerical_cols, top_categorical_cols, top_datetime_cols


def load_dataset(path):
    with open(path, 'r') as f:
        first_line = f.readline()
        dialect = csv.Sniffer().sniff(first_line, delimiters=[",", ";", "\t", "|", "/"])
        sep = dialect.delimiter
    return pd.read_csv(path, sep=sep)


# Example usage
if __name__ == "__main__":
    data = {
        'tenure_months': [12, 5, 20, 3, 15],
        'monthly_usage_hours': [150, 60, 200, 30, 180],
        'has_multiple_devices': [1, 0, 1, 0, 1],
        'customer_support_calls': [2, 0, 3, 1, 2],
        'city': ['A', 'B', 'A', 'C', 'B'],
        'subscription_type': ['premium', 'basic', 'basic', 'premium', 'premium'],
        'join_date': pd.to_datetime(['2020-01-15', '2019-05-20', '2023-11-01', '2018-07-10', '2017-03-25']),
        'last_login_date': pd.to_datetime(['2025-08-01', '2025-08-05', '2025-08-02', '2025-08-03', '2025-08-04'])
    }
    df = pd.DataFrame(data)

    insights, numerical_columns, categorical_columns, datetime_columns = generate(df, print_stats=True, save_json=True)

    print("\n\nReady for the next function call:")
    print(f"Numerical columns: {numerical_columns}")
    print(f"Categorical columns: {categorical_columns}")
    print(f"Datetime columns: {datetime_columns}")

    def next_function(df, num_cols, cat_cols, dt_cols):
        print("\nInside the next function with limited features:")
        print(f"Processing numerical features: {num_cols}")
        print(f"Processing categorical features: {cat_cols}")
        print(f"Processing datetime features: {dt_cols}")

    next_function(df, numerical_columns, categorical_columns, datetime_columns)