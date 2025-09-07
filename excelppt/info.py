import pandas as pd
import os

def extract_columns(upload_dir):
    for fname in os.listdir(upload_dir):
        if fname.startswith("input") and fname.endswith(".csv"):
            df = pd.read_csv(os.path.join(upload_dir, fname))
            return df.columns.tolist()
    return []