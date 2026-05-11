"""Example utility module for ${name}."""

import pandas as pd


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Example preprocessing function."""
    return df.dropna()


def validate_features(features: list, expected_count: int) -> bool:
    """Example validation function."""
    return len(features) == expected_count
