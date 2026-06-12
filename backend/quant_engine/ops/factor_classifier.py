"""
Factor classifier for categorizing factors by type
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FactorCategory(str, Enum):
    """Factor category types"""
    UNIVERSAL = "universal"  # Works across multiple symbols
    SYMBOL_SPECIFIC = "symbol_specific"  # Works only on specific symbol
    SECTOR_SPECIFIC = "sector_specific"  # Works within a sector
    CONDITIONAL = "conditional"  # Works under specific conditions


@dataclass
class FactorClassification:
    """Factor classification result"""
    factor_id: str
    category: FactorCategory
    confidence: float
    applicable_symbols: List[str]
    excluded_symbols: List[str]
    classification_reason: str


class FactorClassifier:
    """Classifier for determining factor type"""
    
    def __init__(self, generalization_engine):
        self.generalization_engine = generalization_engine
        self.classifications: Dict[str, FactorClassification] = {}
    
    def classify_factor(
        self,
        factor_id: str,
        test_symbols: List[str],
        threshold: float = 0.7
    ) -> FactorClassification:
        """
        Classify a factor by type
        
        Args:
            factor_id: ID of the factor to classify
            test_symbols: Symbols to test on
            threshold: Generalization threshold for universal classification
            
        Returns:
            FactorClassification with category and confidence
        """
        logger.info(f"Classifying factor {factor_id}")
        
        # Run generalization test
        test_result = self.generalization_engine.test_factor(
            factor_id,
            test_symbols[0],  # Assume first is original
            test_symbols[1:]
        )
        
        # Determine category based on test results
        if test_result.is_universal and test_result.generalization_score >= threshold:
            category = FactorCategory.UNIVERSAL
            confidence = test_result.generalization_score
            applicable_symbols = test_result.test_symbols
            excluded_symbols = []
            reason = f"Generalization score {test_result.generalization_score:.2f} >= threshold {threshold}"
        elif test_result.generalization_score >= 0.5:
            category = FactorCategory.SECTOR_SPECIFIC
            confidence = test_result.generalization_score
            applicable_symbols = self._identify_sector(test_result.symbol_performance)
            excluded_symbols = [s for s in test_result.test_symbols if s not in applicable_symbols]
            reason = f"Partial generalization, works within sector"
        else:
            category = FactorCategory.SYMBOL_SPECIFIC
            confidence = 1.0 - test_result.generalization_score
            applicable_symbols = [test_result.original_symbol]
            excluded_symbols = [s for s in test_result.test_symbols if s != test_result.original_symbol]
            reason = f"Low generalization score {test_result.generalization_score:.2f}, symbol-specific"
        
        classification = FactorClassification(
            factor_id=factor_id,
            category=category,
            confidence=confidence,
            applicable_symbols=applicable_symbols,
            excluded_symbols=excluded_symbols,
            classification_reason=reason
        )
        
        self.classifications[factor_id] = classification
        return classification
    
    def _identify_sector(self, symbol_performance: Dict[str, Dict]) -> List[str]:
        """
        Identify sector based on performance patterns
        
        Args:
            symbol_performance: Performance data for each symbol
            
        Returns:
            List of symbols in the same sector
        """
        # TODO: Implement sector identification
        # This could use:
        # 1. Symbol metadata (exchange, contract type)
        # 2. Performance clustering
        # 3. Correlation analysis
        
        # For now, return all symbols with positive performance
        return [
            symbol for symbol, perf in symbol_performance.items()
            if perf.get('sharpe', 0) > 0
        ]
    
    def batch_classify(
        self,
        factor_ids: List[str],
        test_symbols: List[str]
    ) -> Dict[str, FactorClassification]:
        """
        Classify multiple factors
        
        Args:
            factor_ids: List of factor IDs to classify
            test_symbols: Symbols to test on
            
        Returns:
            Dictionary of {factor_id: FactorClassification}
        """
        results = {}
        for factor_id in factor_ids:
            classification = self.classify_factor(factor_id, test_symbols)
            results[factor_id] = classification
        
        return results
    
    def get_factors_by_category(
        self,
        category: FactorCategory
    ) -> List[str]:
        """
        Get all factors of a specific category
        
        Args:
            category: Factor category to filter by
            
        Returns:
            List of factor IDs
        """
        return [
            factor_id for factor_id, classification in self.classifications.items()
            if classification.category == category
        ]
    
    def get_classification_summary(self) -> Dict[str, int]:
        """
        Get summary of classifications
        
        Returns:
            Dictionary with counts by category
        """
        summary = {
            "universal": 0,
            "symbol_specific": 0,
            "sector_specific": 0,
            "conditional": 0,
            "total": len(self.classifications)
        }
        
        for classification in self.classifications.values():
            summary[classification.category.value] += 1
        
        return summary
