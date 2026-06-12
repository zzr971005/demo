"""
Generalization test engine for factor cross-symbol applicability
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GeneralizationTestResult:
    """Generalization test result"""
    factor_id: str
    test_symbols: List[str]
    original_symbol: str
    is_universal: bool
    generalization_score: float
    symbol_performance: Dict[str, Dict]
    performance_std: float
    performance_mean: float
    ic_correlation: float
    tested_at: datetime


class GeneralizationTestEngine:
    """Engine for testing factor generalization across symbols"""
    
    def __init__(self, data_hub):
        self.data_hub = data_hub
        self.test_results: Dict[str, GeneralizationTestResult] = {}
    
    def test_factor(
        self,
        factor_id: str,
        original_symbol: str,
        test_symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> GeneralizationTestResult:
        """
        Test factor generalization across multiple symbols
        
        Args:
            factor_id: ID of the factor to test
            original_symbol: Symbol where factor was discovered
            test_symbols: Symbols to test generalization on
            start_date: Test start date
            end_date: Test end date
            
        Returns:
            GeneralizationTestResult with test metrics
        """
        logger.info(f"Testing generalization of factor {factor_id} from {original_symbol}")
        
        # Get factor expression (TODO: implement factor retrieval)
        factor_expr = self._get_factor_expression(factor_id)
        
        # Evaluate on original symbol
        original_performance = self._evaluate_factor_on_symbol(
            factor_expr, original_symbol, start_date, end_date
        )
        
        # Evaluate on test symbols
        symbol_performance = {}
        for symbol in test_symbols:
            performance = self._evaluate_factor_on_symbol(
                factor_expr, symbol, start_date, end_date
            )
            symbol_performance[symbol] = performance
        
        # Calculate generalization metrics
        performance_values = [p.get('sharpe', 0.0) for p in symbol_performance.values()]
        performance_mean = np.mean(performance_values)
        performance_std = np.std(performance_values)
        
        # Calculate IC correlation across symbols
        ic_correlation = self._calculate_ic_correlation(symbol_performance)
        
        # Determine if factor is universal
        generalization_score = self._calculate_generalization_score(
            original_performance, symbol_performance
        )
        
        is_universal = generalization_score >= 0.7
        
        result = GeneralizationTestResult(
            factor_id=factor_id,
            test_symbols=test_symbols,
            original_symbol=original_symbol,
            is_universal=is_universal,
            generalization_score=generalization_score,
            symbol_performance=symbol_performance,
            performance_std=performance_std,
            performance_mean=performance_mean,
            ic_correlation=ic_correlation,
            tested_at=datetime.now()
        )
        
        self.test_results[factor_id] = result
        return result
    
    def _get_factor_expression(self, factor_id: str) -> str:
        """Get factor expression from database"""
        # TODO: Implement factor retrieval from database
        return "close - shift(close, 1)"
    
    def _evaluate_factor_on_symbol(
        self,
        factor_expr: str,
        symbol: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Dict:
        """
        Evaluate factor on a single symbol
        
        Args:
            factor_expr: Factor expression
            symbol: Symbol to evaluate on
            start_date: Start date
            end_date: End date
            
        Returns:
            Performance metrics dictionary
        """
        # TODO: Implement actual factor evaluation
        # This will involve:
        # 1. Loading data for the symbol
        # 2. Computing factor values
        # 3. Running backtest
        # 4. Calculating performance metrics
        
        return {
            "symbol": symbol,
            "sharpe": np.random.uniform(0.5, 2.0),
            "ic_mean": np.random.uniform(0.02, 0.1),
            "max_drawdown": np.random.uniform(0.1, 0.3),
            "calmar": np.random.uniform(0.5, 2.0)
        }
    
    def _calculate_generalization_score(
        self,
        original_performance: Dict,
        symbol_performance: Dict[str, Dict]
    ) -> float:
        """
        Calculate generalization score
        
        Args:
            original_performance: Performance on original symbol
            symbol_performance: Performance on test symbols
            
        Returns:
            Generalization score (0-1)
        """
        if not symbol_performance:
            return 0.0
        
        # Get Sharpe ratios
        original_sharpe = original_performance.get('sharpe', 0.0)
        test_sharpes = [p.get('sharpe', 0.0) for p in symbol_performance.values()]
        
        # Calculate performance retention
        performance_retention = np.mean([s / original_sharpe for s in test_shares if original_sharpe > 0])
        
        # Calculate stability (inverse of std)
        performance_std = np.std(test_shares)
        stability = 1.0 / (1.0 + performance_std)
        
        # Combine metrics
        generalization_score = (performance_retention * 0.6 + stability * 0.4)
        
        return min(max(generalization_score, 0.0), 1.0)
    
    def _calculate_ic_correlation(self, symbol_performance: Dict[str, Dict]) -> float:
        """
        Calculate IC correlation across symbols
        
        Args:
            symbol_performance: Performance data for each symbol
            
        Returns:
            IC correlation coefficient
        """
        # TODO: Implement IC correlation calculation
        # This requires IC time series data for each symbol
        return np.random.uniform(0.3, 0.8)
    
    def batch_test_factors(
        self,
        factor_ids: List[str],
        test_symbols: List[str]
    ) -> Dict[str, GeneralizationTestResult]:
        """
        Test multiple factors for generalization
        
        Args:
            factor_ids: List of factor IDs to test
            test_symbols: Symbols to test on
            
        Returns:
            Dictionary of {factor_id: GeneralizationTestResult}
        """
        results = {}
        for factor_id in factor_ids:
            # Get original symbol for this factor
            original_symbol = self._get_factor_original_symbol(factor_id)
            
            result = self.test_factor(
                factor_id, original_symbol, test_symbols
            )
            results[factor_id] = result
        
        return results
    
    def _get_factor_original_symbol(self, factor_id: str) -> str:
        """Get original symbol for factor"""
        # TODO: Implement symbol retrieval from database
        return "RB"
