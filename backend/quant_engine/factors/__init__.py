"""
quant_engine.factors — 因子原语引擎

包含：
- registry: 8族因子原语注册表
- market_context: 品种特性与交易时间上下文
- formula_dsl: 公式化因子定义语言（字符串表达式 → AST → 可执行函数）
- semantic_validator: 语义约束引擎（C001~C303 + FamilyChecker）
- alpha_generator: Alpha信号批量生成器
- ic_analysis: 信息系数(IC)分析
- vector_index: 因子向量相似度去重
"""

from .registry import FACTOR_REGISTRY, PrimitiveFamily, register_primitive, list_primitives
from .market_context import MarketContext, SYMBOL_CONFIGS, SYMBOL_GROUPS
from .formula_dsl import (
    ExprNode,
    VarNode,
    ConstNode,
    BinOpNode,
    UnaryOpNode,
    FuncNode,
    parse_expr,
    serialize,
    deserialize,
    expr_to_func,
    evaluate_expr,
    compile_expr,
    tree_depth,
    walk_dfs,
    collect_nodes,
    collect_functions,
    collect_variables,
    expr_to_string,
    VALID_VARIABLES,
)
from .semantic_validator import (
    SemanticValidator,
    Violation,
    ValidationResult,
    validate_expression,
    quick_check,
)

__all__ = [
    # registry
    "FACTOR_REGISTRY",
    "PrimitiveFamily",
    "register_primitive",
    "list_primitives",
    # market_context
    "MarketContext",
    "SYMBOL_CONFIGS",
    "SYMBOL_GROUPS",
    # formula_dsl
    "ExprNode",
    "VarNode",
    "ConstNode",
    "BinOpNode",
    "UnaryOpNode",
    "FuncNode",
    "parse_expr",
    "serialize",
    "deserialize",
    "expr_to_func",
    "evaluate_expr",
    "compile_expr",
    "tree_depth",
    "walk_dfs",
    "collect_nodes",
    "collect_functions",
    "collect_variables",
    "expr_to_string",
    "VALID_VARIABLES",
    # semantic_validator
    "SemanticValidator",
    "Violation",
    "ValidationResult",
    "validate_expression",
    "quick_check",
]
