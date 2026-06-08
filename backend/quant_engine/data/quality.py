"""
Data quality check module
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DataQualityReport:
    """Data quality report"""
    completeness: float  # Percentage of non-missing values
    consistency: float  # Consistency score
    anomaly_count: int  # Number of anomalies detected
    anomaly_ratio: float  # Ratio of anomalies
    time_alignment_score: float  # Time alignment score
    overall_score: float  # Overall quality score
    issues: List[str]  # List of detected issues


@dataclass
class TimeAlignmentReport:
    """Time alignment report"""
    aligned_symbols: List[str]
    misaligned_symbols: List[str]
    common_time_range: Tuple[pd.Timestamp, pd.Timestamp]
    coverage_ratio: float  # Ratio of time coverage


def check_data_quality(dfs: Dict[str, pd.DataFrame]) -> DataQualityReport:
    """
    Check data quality for multiple symbols
    
    Args:
        dfs: Dictionary of {symbol: DataFrame}
        
    Returns:
        DataQualityReport with quality metrics
    """
    issues = []
    
    # Check completeness
    total_cells = 0
    missing_cells = 0
    for df in dfs.values():
        total_cells += len(df) * len(df.columns)
        missing_cells += df.isnull().sum().sum()
    
    completeness = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 0.0
    
    if completeness < 0.95:
        issues.append(f"Low completeness: {completeness:.2%}")
    
    # Check consistency (standard deviation of returns)
    consistency_scores = []
    for symbol, df in dfs.items():
        if 'log_return' in df.columns:
            std = df['log_return'].std()
            if std > 0:
                consistency_scores.append(std)
    
    consistency = np.mean(consistency_scores) if consistency_scores else 0.0
    
    # Check for anomalies (extreme values)
    anomaly_count = 0
    total_values = 0
    for df in dfs.values():
        for col in df.select_dtypes(include=[np.number]).columns:
            values = df[col].dropna()
            if len(values) > 0:
                q1 = values.quantile(0.25)
                q3 = values.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 3 * iqr
                upper_bound = q3 + 3 * iqr
                anomalies = ((values < lower_bound) | (values > upper_bound)).sum()
                anomaly_count += anomalies
                total_values += len(values)
    
    anomaly_ratio = anomaly_count / total_values if total_values > 0 else 0.0
    
    if anomaly_ratio > 0.05:
        issues.append(f"High anomaly ratio: {anomaly_ratio:.2%}")
    
    # Check time alignment
    time_report = check_time_alignment(dfs)
    time_alignment_score = time_report.coverage_ratio
    
    if time_alignment_score < 0.8:
        issues.append(f"Poor time alignment: {time_alignment_score:.2%}")
    
    # Calculate overall score
    overall_score = (completeness * 0.4 + 
                    (1.0 - anomaly_ratio) * 0.3 + 
                    time_alignment_score * 0.3)
    
    return DataQualityReport(
        completeness=completeness,
        consistency=consistency,
        anomaly_count=anomaly_count,
        anomaly_ratio=anomaly_ratio,
        time_alignment_score=time_alignment_score,
        overall_score=overall_score,
        issues=issues
    )


def check_time_alignment(dfs: Dict[str, pd.DataFrame]) -> TimeAlignmentReport:
    """
    Check time alignment across multiple symbols
    
    Args:
        dfs: Dictionary of {symbol: DataFrame}
        
    Returns:
        TimeAlignmentReport with alignment metrics
    """
    if not dfs:
        return TimeAlignmentReport([], [], (pd.Timestamp.now(), pd.Timestamp.now()), 0.0)
    
    # Get time ranges for each symbol
    time_ranges = {}
    for symbol, df in dfs.items():
        if hasattr(df.index, 'to_pydatetime'):
            times = df.index.to_pydatetime()
            if len(times) > 0:
                time_ranges[symbol] = (min(times), max(times))
    
    if not time_ranges:
        return TimeAlignmentReport([], [], (pd.Timestamp.now(), pd.Timestamp.now()), 0.0)
    
    # Find common time range
    all_starts = [r[0] for r in time_ranges.values()]
    all_ends = [r[1] for r in time_ranges.values()]
    
    common_start = max(all_starts)
    common_end = min(all_ends)
    
    # Check which symbols are aligned
    aligned_symbols = []
    misaligned_symbols = []
    
    for symbol, (start, end) in time_ranges.items():
        if start <= common_start and end >= common_end:
            aligned_symbols.append(symbol)
        else:
            misaligned_symbols.append(symbol)
    
    # Calculate coverage ratio
    if common_end > common_start:
        total_range = (max(all_ends) - min(all_starts)).total_seconds()
        common_range = (common_end - common_start).total_seconds()
        coverage_ratio = common_range / total_range if total_range > 0 else 0.0
    else:
        coverage_ratio = 0.0
    
    return TimeAlignmentReport(
        aligned_symbols=aligned_symbols,
        misaligned_symbols=misaligned_symbols,
        common_time_range=(common_start, common_end),
        coverage_ratio=coverage_ratio
    )


def generate_quality_report(dfs: Dict[str, pd.DataFrame]) -> str:
    """
    Generate human-readable data quality report
    
    Args:
        dfs: Dictionary of {symbol: DataFrame}
        
    Returns:
        Formatted report string
    """
    quality_report = check_data_quality(dfs)
    time_report = check_time_alignment(dfs)
    
    report = []
    report.append("=" * 60)
    report.append("Data Quality Report")
    report.append("=" * 60)
    report.append(f"Overall Quality Score: {quality_report.overall_score:.2%}")
    report.append(f"Completeness: {quality_report.completeness:.2%}")
    report.append(f"Consistency: {quality_report.consistency:.4f}")
    report.append(f"Anomaly Count: {quality_report.anomaly_count}")
    report.append(f"Anomaly Ratio: {quality_report.anomaly_ratio:.2%}")
    report.append(f"Time Alignment Score: {quality_report.time_alignment_score:.2%}")
    report.append("")
    report.append("Time Alignment:")
    report.append(f"  Aligned Symbols: {', '.join(time_report.aligned_symbols)}")
    report.append(f"  Misaligned Symbols: {', '.join(time_report.misaligned_symbols)}")
    report.append(f"  Common Time Range: {time_report.common_time_range[0]} to {time_report.common_time_range[1]}")
    report.append(f"  Coverage Ratio: {time_report.coverage_ratio:.2%}")
    report.append("")
    
    if quality_report.issues:
        report.append("Issues Detected:")
        for issue in quality_report.issues:
            report.append(f"  - {issue}")
    else:
        report.append("No issues detected.")
    
    report.append("=" * 60)
    
    return "\n".join(report)
