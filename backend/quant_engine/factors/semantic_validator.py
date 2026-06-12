"""
语义约束引擎 (Semantic Validator)

对公式化因子表达式进行语义约束检查，返回 (is_valid, penalty_factor, violations_list)。
与 registry.py 中的原语族定义联动。

约束清单：
- C001: ts_mean 只能接收价格/成交量/持仓量变量
- C101: 禁止 close/volume（除法导致量纲错误）
- C102: 禁止 log(负数)
- C201: 树深度>8，适应度 x0.8
- C202: 同一族连续嵌套>2层，适应度 x0.9
- C301: night_gap 必须配 vol_regime
- C302: basis 必须配 trend_strength
- C303: IF 品种禁止 CLOSE_TODAY（品种级约束）
- FamilyChecker: 确保每个表达式至少包含 2 个不同族
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .formula_dsl import (
    BinOpNode,
    ExprNode,
    FuncNode,
    UnaryOpNode,
    VarNode,
    collect_functions,
    collect_nodes,
    collect_variables,
    tree_depth,
    walk_dfs,
)
from .registry import FACTOR_REGISTRY, PrimitiveFamily

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    code: str
    message: str
    severity: str  # "fatal" | "warning"
    penalty: float  # 适应度惩罚系数（1.0 表示无惩罚）


@dataclass
class ValidationResult:
    is_valid: bool
    penalty_factor: float
    violations: List[Violation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "penalty_factor": round(self.penalty_factor, 4),
            "violations": [
                {
                    "code": v.code,
                    "message": v.message,
                    "severity": v.severity,
                    "penalty": v.penalty,
                }
                for v in self.violations
            ],
        }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

# 价格/成交量/持仓量变量（C001 合法输入）
_PRICE_VOLUME_OI_VARS = {"open", "high", "low", "close", "volume", "open_interest"}

# 需要 trend_strength 配合的函数（C302）
_REQUIRES_TREND_STRENGTH = {"basis", "basis_annualized", "spread_near_far"}

# 需要 vol_regime 配合的函数（C301）
_REQUIRES_VOL_REGIME = {"night_gap", "am_pm_gap", "intraday_range"}


def _get_family(func_name: str) -> Optional[PrimitiveFamily]:
    meta = FACTOR_REGISTRY.get(func_name)
    return meta.family if meta else None


def _is_price_volume_oi_node(node: ExprNode) -> bool:
    """判断节点是否为纯价格/成交量/持仓量变量"""
    if isinstance(node, VarNode):
        return node.name in _PRICE_VOLUME_OI_VARS
    return False


def _has_negative_risk(node: ExprNode) -> bool:
    """粗略判断节点是否可能产生负值（用于 C102）"""
    if isinstance(node, VarNode):
        # close, volume, open_interest 均可能为任意正数；high/low/open 同理
        return True
    if isinstance(node, ConstNode):
        return float(node.value) < 0
    if isinstance(node, BinOpNode):
        if node.op == "-":
            return True
        if node.op == "*":
            return _has_negative_risk(node.left) or _has_negative_risk(node.right)
        if node.op == "/":
            return True  # 除法结果可正可负
        if node.op == "+":
            return _has_negative_risk(node.left) or _has_negative_risk(node.right)
        if node.op == "**":
            # 偶次幂可能为正，但奇次幂可能为负；保守返回 True
            return True
    if isinstance(node, UnaryOpNode):
        if node.op == "neg":
            return True
        if node.op in ("abs", "sqrt"):
            return False
        if node.op == "log":
            return True  # log 本身可能负，但这里关注输入是否可能负
        if node.op == "sign":
            return True
    if isinstance(node, FuncNode):
        # 保守：大部分因子函数输出可正可负
        if node.name in ("ts_std", "atr", "ts_range", "garman_klass_vol",
                         "volume_zscore", "intraday_range", "bb_position"):
            return False
        return True
    return True


# 需要导入 ConstNode
from .formula_dsl import ConstNode


# ---------------------------------------------------------------------------
# 约束检查器
# ---------------------------------------------------------------------------

class SemanticValidator:
    """
    语义约束引擎主类。
    调用 validate(node, symbol) 获取 ValidationResult。
    """

    def __init__(self, max_tree_depth: int = 8, max_family_nesting: int = 2) -> None:
        self.max_tree_depth = max_tree_depth
        self.max_family_nesting = max_family_nesting

    def validate(self, node: ExprNode, symbol: Optional[str] = None) -> ValidationResult:
        violations: List[Violation] = []

        # C001
        violations.extend(self._check_c001(node))

        # C101
        violations.extend(self._check_c101(node))

        # C102
        violations.extend(self._check_c102(node))

        # C201
        violations.extend(self._check_c201(node))

        # C202
        violations.extend(self._check_c202(node))

        # C301
        violations.extend(self._check_c301(node))

        # C302
        violations.extend(self._check_c302(node))

        # C303
        if symbol:
            violations.extend(self._check_c303(symbol))

        # FamilyChecker
        violations.extend(self._check_family_diversity(node))

        # 计算总惩罚
        penalty = 1.0
        fatal = False
        for v in violations:
            if v.severity == "fatal":
                fatal = True
            penalty *= v.penalty

        # 惩罚系数下限 0.1
        penalty = max(penalty, 0.1)

        return ValidationResult(
            is_valid=not fatal,
            penalty_factor=penalty,
            violations=violations,
        )

    # -----------------------------------------------------------------------
    # C001: ts_mean 只能接收价格/成交量/持仓量
    # -----------------------------------------------------------------------
    def _check_c001(self, node: ExprNode) -> List[Violation]:
        violations = []

        def _cb(n: ExprNode) -> None:
            if isinstance(n, FuncNode) and n.name == "ts_mean":
                for arg in n.args:
                    # 允许价格/成交量/持仓量变量，以及数值常量（如窗口大小）
                    if isinstance(arg, ConstNode):
                        continue
                    if not _is_price_volume_oi_node(arg):
                        violations.append(
                            Violation(
                                code="C001",
                                message=f"ts_mean 的参数必须是价格/成交量/持仓量变量，得到 {type(arg).__name__}",
                                severity="fatal",
                                penalty=1.0,
                            )
                        )

        walk_dfs(node, _cb)
        return violations

    # -----------------------------------------------------------------------
    # C101: 禁止 close/volume（除法导致量纲错误）
    # -----------------------------------------------------------------------
    def _check_c101(self, node: ExprNode) -> List[Violation]:
        violations = []

        def _cb(n: ExprNode) -> None:
            if isinstance(n, BinOpNode) and n.op == "/":
                left_vars = set()
                right_vars = set()
                walk_dfs(n.left, lambda x: left_vars.add(x.name) if isinstance(x, VarNode) else None)
                walk_dfs(n.right, lambda x: right_vars.add(x.name) if isinstance(x, VarNode) else None)
                if "close" in left_vars and "volume" in right_vars:
                    violations.append(
                        Violation(
                            code="C101",
                            message="禁止 close/volume 除法（量纲错误：价格/成交量）",
                            severity="fatal",
                            penalty=1.0,
                        )
                    )
                if "volume" in left_vars and "close" in right_vars:
                    violations.append(
                        Violation(
                            code="C101",
                            message="禁止 volume/close 除法（量纲错误：成交量/价格）",
                            severity="fatal",
                            penalty=1.0,
                        )
                    )

        walk_dfs(node, _cb)
        return violations

    # -----------------------------------------------------------------------
    # C102: 禁止 log(负数)
    # -----------------------------------------------------------------------
    def _check_c102(self, node: ExprNode) -> List[Violation]:
        violations = []

        def _cb(n: ExprNode) -> None:
            if isinstance(n, UnaryOpNode) and n.op == "log":
                if _has_negative_risk(n.operand):
                    violations.append(
                        Violation(
                            code="C102",
                            message="log 运算的输入可能为负数或零，导致 NaN/异常",
                            severity="warning",
                            penalty=0.95,
                        )
                    )

        walk_dfs(node, _cb)
        return violations

    # -----------------------------------------------------------------------
    # C201: 树深度>8，适应度 x0.8
    # -----------------------------------------------------------------------
    def _check_c201(self, node: ExprNode) -> List[Violation]:
        depth = tree_depth(node)
        if depth > self.max_tree_depth:
            return [
                Violation(
                    code="C201",
                    message=f"表达式树深度 {depth} 超过限制 {self.max_tree_depth}，适应度 x0.8",
                    severity="warning",
                    penalty=0.8,
                )
            ]
        return []

    # -----------------------------------------------------------------------
    # C202: 同一族连续嵌套>2层，适应度 x0.9
    # -----------------------------------------------------------------------
    def _check_c202(self, node: ExprNode) -> List[Violation]:
        violations = []
        max_nesting = self.max_family_nesting

        def _max_family_depth(n: ExprNode, current_family: Optional[PrimitiveFamily], depth: int) -> int:
            if isinstance(n, FuncNode):
                family = _get_family(n.name)
                if family and family == current_family:
                    new_depth = depth + 1
                else:
                    new_depth = 1 if family else 0
                max_d = new_depth
                for arg in n.args:
                    max_d = max(max_d, _max_family_depth(arg, family, new_depth))
                return max_d
            if isinstance(n, (BinOpNode, UnaryOpNode)):
                # 运算符不改变族，继续向下
                max_d = depth
                if isinstance(n, BinOpNode):
                    max_d = max(max_d, _max_family_depth(n.left, current_family, depth))
                    max_d = max(max_d, _max_family_depth(n.right, current_family, depth))
                else:
                    max_d = max(max_d, _max_family_depth(n.operand, current_family, depth))
                return max_d
            return depth

        max_found = 0

        def _scan(n: ExprNode) -> None:
            nonlocal max_found
            if isinstance(n, FuncNode):
                family = _get_family(n.name)
                d = _max_family_depth(n, family, 1)
                max_found = max(max_found, d)
                for arg in n.args:
                    _scan(arg)
            elif isinstance(n, BinOpNode):
                _scan(n.left)
                _scan(n.right)
            elif isinstance(n, UnaryOpNode):
                _scan(n.operand)

        _scan(node)

        if max_found > max_nesting:
            violations.append(
                Violation(
                    code="C202",
                    message=f"同一族连续嵌套深度 {max_found} 超过限制 {max_nesting}，适应度 x0.9",
                    severity="warning",
                    penalty=0.9,
                )
            )
        return violations

    # -----------------------------------------------------------------------
    # C301: night_gap 必须配 vol_regime
    # -----------------------------------------------------------------------
    def _check_c301(self, node: ExprNode) -> List[Violation]:
        funcs = set(collect_functions(node))
        has_night_gap = bool(_REQUIRES_VOL_REGIME & funcs)
        has_vol_regime = "vol_regime" in funcs
        if has_night_gap and not has_vol_regime:
            return [
                Violation(
                    code="C301",
                    message="使用 night_gap/am_pm_gap/intraday_range 时必须配合 vol_regime",
                    severity="warning",
                    penalty=0.85,
                )
            ]
        return []

    # -----------------------------------------------------------------------
    # C302: basis 必须配 trend_strength
    # -----------------------------------------------------------------------
    def _check_c302(self, node: ExprNode) -> List[Violation]:
        funcs = set(collect_functions(node))
        has_basis = bool(_REQUIRES_TREND_STRENGTH & funcs)
        has_trend_strength = "trend_strength" in funcs
        if has_basis and not has_trend_strength:
            return [
                Violation(
                    code="C302",
                    message="使用 basis/basis_annualized/spread_near_far 时必须配合 trend_strength",
                    severity="warning",
                    penalty=0.85,
                )
            ]
        return []

    # -----------------------------------------------------------------------
    # C303: IF 品种禁止 CLOSE_TODAY
    # -----------------------------------------------------------------------
    def _check_c303(self, symbol: str) -> List[Violation]:
        # 该约束在表达式层面不直接体现，但在策略/交易层面检查
        # 这里仅做品种级标记，实际执行在交易网关层拦截
        if symbol == "IF":
            return [
                Violation(
                    code="C303",
                    message="IF 品种禁止 CLOSE_TODAY（平今手续费为隔日10倍）",
                    severity="fatal",
                    penalty=1.0,
                )
            ]
        return []

    # -----------------------------------------------------------------------
    # FamilyChecker: 至少包含 2 个不同族
    # -----------------------------------------------------------------------
    def _check_family_diversity(self, node: ExprNode) -> List[Violation]:
        funcs = collect_functions(node)
        families: Set[PrimitiveFamily] = set()
        for fn in funcs:
            fam = _get_family(fn)
            if fam:
                families.add(fam)
        if len(families) < 2:
            return [
                Violation(
                    code="FAMILY",
                    message=f"表达式必须包含至少 2 个不同原语族，当前仅 {len(families)} 个: {[f.value for f in families]}",
                    severity="fatal",
                    penalty=1.0,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def validate_expression(expr_str: str, symbol: Optional[str] = None) -> ValidationResult:
    """
    对表达式字符串进行完整语义验证。
    先解析为 AST，再运行所有约束检查。
    """
    from .formula_dsl import parse_expr

    ast = parse_expr(expr_str)
    validator = SemanticValidator()
    return validator.validate(ast, symbol=symbol)


def quick_check(expr_str: str, symbol: Optional[str] = None) -> Tuple[bool, float]:
    """快速检查：返回 (是否合法, 惩罚系数)"""
    result = validate_expression(expr_str, symbol=symbol)
    return result.is_valid, result.penalty_factor
