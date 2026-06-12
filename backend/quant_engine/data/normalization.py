"""
Data normalization module for multi-symbol data processing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def to_log_returns(df: pd.DataFrame, price_col: str = 'close') -> pd.DataFrame:
    """
    Convert price data to log returns
    
    Args:
        df: DataFrame with price data
        price_col: Column name for price data
        
    Returns:
        DataFrame with log returns
    """
    df = df.copy()
    df['log_return'] = np.log(df[price_col] / df[price_col].shift(1))
    return df


def normalize_intra_symbol(df: pd.DataFrame, method: str = 'zscore') -> pd.DataFrame:
    """
    Normalize data within a single symbol
    
    Args:
        df: DataFrame with data
        method: Normalization method ('zscore', 'minmax', 'robust')
        
    Returns:
        Normalized DataFrame
    """
    df = df.copy()
    
    if method == 'zscore':
        # Z-score normalization
        for col in df.select_dtypes(include=[np.number]).columns:
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                df[col] = (df[col] - mean) / std
    elif method == 'minmax':
        # Min-max normalization
        for col in df.select_dtypes(include=[np.number]).columns:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[col] = (df[col] - min_val) / (max_val - min_val)
    elif method == 'robust':
        # Robust normalization using median and IQR
        for col in df.select_dtypes(include=[np.number]).columns:
            median = df[col].median()
            q75 = df[col].quantile(0.75)
            q25 = df[col].quantile(0.25)
            iqr = q75 - q25
            if iqr > 0:
                df[col] = (df[col] - median) / iqr
    
    return df


def align_timeframes(dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Align timeframes across multiple symbols
    
    Args:
        dfs: Dictionary of {symbol: DataFrame}
        
    Returns:
        Dictionary with aligned timeframes
    """
    if not dfs:
        return {}
    
    # Find common time range
    all_timestamps = []
    for df in dfs.values():
        if hasattr(df.index, 'to_pydatetime'):
            all_timestamps.extend(df.index.to_pydatetime())
    
    if not all_timestamps:
        return dfs
    
    min_time = min(all_timestamps)
    max_time = max(all_timestamps)
    
    # Filter each DataFrame to common range
    aligned = {}
    for symbol, df in dfs.items():
        if hasattr(df.index, 'to_pydatetime'):
            mask = (df.index >= min_time) & (df.index <= max_time)
            aligned[symbol] = df[mask].copy()
        else:
            aligned[symbol] = df.copy()
    
    return aligned


def handle_missing_values(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
    """
    Handle missing values in data
    
    Args:
        df: DataFrame with potential missing values
        method: Method to handle missing values ('ffill', 'bfill', 'interpolate', 'drop')
        
    Returns:
        DataFrame with missing values handled
    """
    df = df.copy()
    
    if method == 'ffill':
        df = df.fillna(method='ffill')
    elif method == 'bfill':
        df = df.fillna(method='bfill')
    elif method == 'interpolate':
        df = df.interpolate()
    elif method == 'drop':
        df = df.dropna()
    
    return df


def normalize_multi_symbol_data(
    dfs: Dict[str, pd.DataFrame],
    method: str = 'zscore',
    align: bool = True,
    handle_missing: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Normalize multi-symbol data
    
    Args:
        dfs: Dictionary of {symbol: DataFrame}
        method: Normalization method
        align: Whether to align timeframes
        handle_missing: Whether to handle missing values
        
    Returns:
        Normalized data dictionary
    """
    result = {}
    
    if align:
        dfs = align_timeframes(dfs)
    
    for symbol, df in dfs.items():
        if handle_missing:
            df = handle_missing_values(df)
        df = normalize_intra_symbol(df, method)
        result[symbol] = df
    
    return result
