"""
upay Pulse — Chronological Dataset Splitter (Workstream 4)
Strict time-boundary partitioning:
- Train: Historical early window (e.g. 70%)
- Validation: Mid window (e.g. 15%)
- Test: Strict future window (e.g. 15%) — UNTOUCHED until final evaluation.
Enforces zero lookahead contamination across temporal partitions.
"""

import pandas as pd
from typing import Tuple, Dict, Any

def chronological_split(
    df: pd.DataFrame,
    time_col: str = "created_at_dt",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions a DataFrame into Train, Validation, and Test sets based strictly
    on chronological order of `time_col`.
    """
    assert train_ratio + val_ratio < 1.0, "Train + Validation ratio must be < 1.0 to leave test set"
    test_ratio = 1.0 - (train_ratio + val_ratio)

    if time_col not in df.columns:
        if "created_at" in df.columns:
            df[time_col] = pd.to_datetime(df["created_at"])
        else:
            raise KeyError(f"Timestamp column '{time_col}' not found in dataframe.")

    # Strict ascending sort by time
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    return train_df, val_df, test_df

def get_split_summary(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, time_col: str = "created_at_dt") -> Dict[str, Any]:
    return {
        "train": {
            "samples": len(train_df),
            "start": str(train_df[time_col].min()),
            "end": str(train_df[time_col].max()),
            "fraud_rate": float(round(train_df["is_flagged_fraud"].mean(), 4))
        },
        "validation": {
            "samples": len(val_df),
            "start": str(val_df[time_col].min()),
            "end": str(val_df[time_col].max()),
            "fraud_rate": float(round(val_df["is_flagged_fraud"].mean(), 4))
        },
        "test": {
            "samples": len(test_df),
            "start": str(test_df[time_col].min()),
            "end": str(test_df[time_col].max()),
            "fraud_rate": float(round(test_df["is_flagged_fraud"].mean(), 4))
        }
    }
