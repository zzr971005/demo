"""
语义约束引擎测试

覆盖:
- C001: ts_mean 参数类型检查
- C101: close/volume 除法禁止
- C102: log(负数) 警告
- C201: 树深度限制
- C202: 同族嵌套限制
- C301: night_gap 必须配 vol_regime
- C302: basis 必须配 trend_strength
- C303: IF 品种 CLOSE_TODAY 禁止
- FamilyChecker: 至少 2 个不同族
"""

from __future__ import annotations

import pytest

from backend.quant_engine.factors.formula_dsl import parse_expr
from backend.quant_engine.factors.semantic_validator import (
    SemanticValidator,
    ValidationResult,
    Violation,
    quick_check,
    validate_expression,
)


class TestC001:
    """C001: ts_mean 只能接收价格/成交量/持仓量变量"""

    def test_ts_mean_with_price_ok(self) -> None:
        # 使用包含2个不同族的表达式，避免 FAMILY 检查失败
        result = validate_expression("ts_mean(close, 20) + ts_return(close, 10)")
        assert result.is_valid
        assert not any(v.code == "C001" for v in result.violations)

    def test_ts_mean_with_nested_expr_fatal(self) -> None:
        result = validate_expression("ts_mean(close + 1, 20)")
        c001 = [v for v in result.violations if v.code == "C001"]
        assert len(c001) == 1
        assert c001[0].severity == "fatal"
        assert not result.is_valid

    def test_ts_mean_with_function_fatal(self) -> None:
        result = validate_expression("ts_mean(ts_std(close, 10), 20)")
        c001 = [v for v in result.violations if v.code == "C001"]
        assert len(c001) == 1
        assert c001[0].severity == "fatal"


class TestC101:
    """C101: 禁止 close/volume 除法"""

    def test_close_div_volume_fatal(self) -> None:
        result = validate_expression("close / volume")
        c101 = [v for v in result.violations if v.code == "C101"]
        assert len(c101) == 1
        assert c101[0].severity == "fatal"
        assert not result.is_valid

    def test_volume_div_close_fatal(self) -> None:
        result = validate_expression("volume / close")
        c101 = [v for v in result.violations if v.code == "C101"]
        assert len(c101) == 1
        assert not result.is_valid

    def test_close_div_open_ok(self) -> None:
        result = validate_expression("close / open")
        c101 = [v for v in result.violations if v.code == "C101"]
        assert len(c101) == 0


class TestC102:
    """C102: log(负数) 警告"""

    def test_log_of_variable_warning(self) -> None:
        result = validate_expression("log(close)")
        c102 = [v for v in result.violations if v.code == "C102"]
        assert len(c102) == 1
        assert c102[0].severity == "warning"
        assert c102[0].penalty == pytest.approx(0.95)

    def test_log_of_abs_ok(self) -> None:
        result = validate_expression("log(abs(close))")
        c102 = [v for v in result.violations if v.code == "C102"]
        assert len(c102) == 0

    def test_log_of_positive_const_ok(self) -> None:
        result = validate_expression("log(5)")
        c102 = [v for v in result.violations if v.code == "C102"]
        assert len(c102) == 0


class TestC201:
    """C201: 树深度限制"""

    def test_shallow_tree_ok(self) -> None:
        result = validate_expression("close + open")
        c201 = [v for v in result.violations if v.code == "C201"]
        assert len(c201) == 0

    def test_deep_tree_warning(self) -> None:
        expr = "ts_mean(ts_mean(ts_mean(ts_mean(ts_mean(ts_mean(ts_mean(ts_mean(close, 2), 2), 2), 2), 2), 2), 2), 2)"
        result = validate_expression(expr)
        c201 = [v for v in result.violations if v.code == "C201"]
        assert len(c201) == 1
        assert c201[0].severity == "warning"
        assert c201[0].penalty == pytest.approx(0.8)

    def test_custom_max_depth(self) -> None:
        validator = SemanticValidator(max_tree_depth=2)
        node = parse_expr("close + open * volume")
        result = validator.validate(node)
        c201 = [v for v in result.violations if v.code == "C201"]
        assert len(c201) == 1


class TestC202:
    """C202: 同族嵌套限制"""

    def test_single_family_ok(self) -> None:
        result = validate_expression("ts_return(close, 10)")
        c202 = [v for v in result.violations if v.code == "C202"]
        # 需要至少2个不同族，这里只有1个族，会被 FAMILY 拦截
        # C202 本身不触发因为嵌套深度<=2
        assert len(c202) == 0

    def test_different_family_nesting_ok(self) -> None:
        # momentum + mean_reversion
        result = validate_expression("ts_return(close, 10) + zscore(volume, 20)")
        c202 = [v for v in result.violations if v.code == "C202"]
        assert len(c202) == 0


class TestC301:
    """C301: night_gap 必须配 vol_regime"""

    def test_night_gap_without_vol_regime_warning(self) -> None:
        result = validate_expression("night_gap(close) + ts_return(close, 10)")
        c301 = [v for v in result.violations if v.code == "C301"]
        assert len(c301) == 1
        assert c301[0].severity == "warning"
        assert c301[0].penalty == pytest.approx(0.85)

    def test_night_gap_with_vol_regime_ok(self) -> None:
        result = validate_expression("night_gap(close) * vol_regime(close, 20)")
        c301 = [v for v in result.violations if v.code == "C301"]
        assert len(c301) == 0


class TestC302:
    """C302: basis 必须配 trend_strength"""

    def test_basis_without_trend_strength_warning(self) -> None:
        result = validate_expression("basis(close, open) + ts_return(close, 10)")
        c302 = [v for v in result.violations if v.code == "C302"]
        assert len(c302) == 1
        assert c302[0].severity == "warning"
        assert c302[0].penalty == pytest.approx(0.85)

    def test_basis_with_trend_strength_ok(self) -> None:
        result = validate_expression("basis(close, open) * trend_strength(close, 20)")
        c302 = [v for v in result.violations if v.code == "C302"]
        assert len(c302) == 0


class TestC303:
    """C303: IF 品种禁止 CLOSE_TODAY"""

    def test_if_symbol_fatal(self) -> None:
        result = validate_expression("close + 1", symbol="IF")
        c303 = [v for v in result.violations if v.code == "C303"]
        assert len(c303) == 1
        assert c303[0].severity == "fatal"
        assert not result.is_valid

    def test_non_if_symbol_ok(self) -> None:
        result = validate_expression("close + 1", symbol="RB")
        c303 = [v for v in result.violations if v.code == "C303"]
        assert len(c303) == 0


class TestFamilyChecker:
    """FamilyChecker: 至少包含 2 个不同族"""

    def test_single_family_fatal(self) -> None:
        result = validate_expression("ts_return(close, 10) + ts_slope(close, 20)")
        family = [v for v in result.violations if v.code == "FAMILY"]
        assert len(family) == 1
        assert family[0].severity == "fatal"
        assert not result.is_valid

    def test_two_families_ok(self) -> None:
        result = validate_expression("ts_return(close, 10) + zscore(volume, 20)")
        family = [v for v in result.violations if v.code == "FAMILY"]
        assert len(family) == 0
        assert result.is_valid

    def test_three_families_ok(self) -> None:
        result = validate_expression(
            "ts_return(close, 10) + zscore(volume, 20) + ts_std(close, 10)"
        )
        family = [v for v in result.violations if v.code == "FAMILY"]
        assert len(family) == 0


class TestPenaltyFactor:
    """惩罚系数计算测试"""

    def test_no_penalty(self) -> None:
        result = validate_expression("close + open")
        assert result.penalty_factor == pytest.approx(1.0)

    def test_multiple_penalties_multiplied(self) -> None:
        # C102 (0.95) + C301 (0.85) - 都应该是 warning
        result = validate_expression("log(close) + night_gap(open)")
        assert result.penalty_factor < 1.0
        assert result.penalty_factor >= 0.1

    def test_penalty_floor(self) -> None:
        # 大量 warning 不应使惩罚低于 0.1
        validator = SemanticValidator()
        # 构造一个有很多 violations 的表达式
        node = parse_expr("log(close) + log(volume) + log(open)")
        result = validator.validate(node)
        assert result.penalty_factor >= 0.1


class TestQuickCheck:
    """快速检查入口测试"""

    def test_quick_check_valid(self) -> None:
        # 使用包含2个不同族的表达式
        is_valid, penalty = quick_check("ts_return(close, 10) + zscore(volume, 20)")
        assert is_valid
        assert penalty == pytest.approx(1.0)

    def test_quick_check_invalid(self) -> None:
        is_valid, penalty = quick_check("close / volume")
        assert not is_valid


class TestValidationResult:
    """ValidationResult 数据结构测试"""

    def test_to_dict(self) -> None:
        result = validate_expression("close + 1")
        d = result.to_dict()
        assert "is_valid" in d
        assert "penalty_factor" in d
        assert "violations" in d
        assert isinstance(d["violations"], list)
