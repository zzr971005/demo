"""
DSL 解析测试

覆盖:
- 词法分析 (tokenize)
- 语法分析 (parse_expr)
- AST 序列化/反序列化
- 表达式编译与执行
- 错误处理
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.quant_engine.factors.formula_dsl import (
    BinOpNode,
    ConstNode,
    ExprNode,
    FuncNode,
    UnaryOpNode,
    VarNode,
    collect_functions,
    collect_variables,
    compile_expr,
    deserialize,
    evaluate_expr,
    expr_to_func,
    expr_to_string,
    node_to_dict,
    parse_expr,
    serialize,
    tokenize,
    tree_depth,
)


class TestTokenizer:
    """词法分析测试"""

    def test_tokenize_simple(self) -> None:
        tokens = tokenize("close + 1")
        assert len(tokens) == 3
        assert tokens[0] == ("NAME", "close")
        assert tokens[1] == ("OP1", "+")
        assert tokens[2] == ("NUMBER", "1")

    def test_tokenize_function(self) -> None:
        tokens = tokenize("ts_mean(close, 20)")
        assert len(tokens) == 6
        assert tokens[0] == ("NAME", "ts_mean")
        assert tokens[1] == ("OP1", "(")
        assert tokens[2] == ("NAME", "close")
        assert tokens[3] == ("OP1", ",")
        assert tokens[4] == ("NUMBER", "20")
        assert tokens[5] == ("OP1", ")")

    def test_tokenize_float(self) -> None:
        tokens = tokenize("3.14")
        assert tokens[0] == ("NUMBER", "3.14")

    def test_tokenize_power(self) -> None:
        tokens = tokenize("2 ** 3")
        assert tokens[1] == ("OP2", "**")

    def test_tokenize_empty_raises(self) -> None:
        with pytest.raises(SyntaxError, match="空表达式"):
            tokenize("")

    def test_tokenize_invalid_char_raises(self) -> None:
        with pytest.raises(SyntaxError, match="非法字符"):
            tokenize("close @ 1")


class TestParser:
    """语法分析测试"""

    def test_parse_variable(self) -> None:
        node = parse_expr("close")
        assert isinstance(node, VarNode)
        assert node.name == "close"

    def test_parse_constant(self) -> None:
        node = parse_expr("42")
        assert isinstance(node, ConstNode)
        assert node.value == 42

    def test_parse_float(self) -> None:
        node = parse_expr("3.14")
        assert isinstance(node, ConstNode)
        assert node.value == 3.14

    def test_parse_binop(self) -> None:
        node = parse_expr("close + open")
        assert isinstance(node, BinOpNode)
        assert node.op == "+"
        assert isinstance(node.left, VarNode)
        assert isinstance(node.right, VarNode)

    def test_parse_precedence(self) -> None:
        node = parse_expr("close + open * 2")
        assert isinstance(node, BinOpNode)
        assert node.op == "+"
        assert isinstance(node.left, VarNode)
        assert isinstance(node.right, BinOpNode)

    def test_parse_power(self) -> None:
        node = parse_expr("2 ** 3")
        assert isinstance(node, BinOpNode)
        assert node.op == "**"

    def test_parse_unary_neg(self) -> None:
        node = parse_expr("-close")
        assert isinstance(node, UnaryOpNode)
        assert node.op == "neg"

    def test_parse_unary_abs(self) -> None:
        node = parse_expr("abs(close)")
        assert isinstance(node, UnaryOpNode)
        assert node.op == "abs"

    def test_parse_function(self) -> None:
        node = parse_expr("ts_mean(close, 20)")
        assert isinstance(node, FuncNode)
        assert node.name == "ts_mean"
        assert len(node.args) == 2

    def test_parse_nested(self) -> None:
        node = parse_expr("ts_mean(close + open, 10)")
        assert isinstance(node, FuncNode)
        assert isinstance(node.args[0], BinOpNode)

    def test_parse_parens(self) -> None:
        node = parse_expr("(close + open) * 2")
        assert isinstance(node, BinOpNode)
        assert node.op == "*"
        assert isinstance(node.left, BinOpNode)

    def test_parse_invalid_raises(self) -> None:
        with pytest.raises(SyntaxError):
            parse_expr("close +")

    def test_parse_unexpected_token_raises(self) -> None:
        with pytest.raises(SyntaxError, match="意外的 token"):
            parse_expr("* close")


class TestSerialization:
    """AST 序列化测试"""

    def test_serialize_roundtrip(self) -> None:
        original = parse_expr("ts_mean(close + 1, 20)")
        s = serialize(original)
        restored = deserialize(s)
        assert expr_to_string(restored) == expr_to_string(original)

    def test_node_to_dict_structure(self) -> None:
        node = parse_expr("close + 1")
        d = node_to_dict(node)
        assert d["type"] == "binop"
        assert d["op"] == "+"
        assert d["left"]["type"] == "var"
        assert d["right"]["type"] == "const"


class TestCompilation:
    """表达式编译测试"""

    @pytest.fixture
    def sample_data(self) -> dict[str, np.ndarray]:
        n = 100
        return {
            "open": np.random.randn(n),
            "high": np.random.randn(n),
            "low": np.random.randn(n),
            "close": np.random.randn(n),
            "volume": np.random.randint(1, 1000, n).astype(float),
            "open_interest": np.random.randint(1, 500, n).astype(float),
        }

    def test_compile_simple(self, sample_data: dict) -> None:
        fn, ast = expr_to_func("close + 1")
        result = fn(**sample_data)
        expected = sample_data["close"] + 1
        np.testing.assert_array_almost_equal(result, expected)

    def test_compile_binops(self, sample_data: dict) -> None:
        fn, _ = expr_to_func("(close - open) / open")
        result = fn(**sample_data)
        expected = (sample_data["close"] - sample_data["open"]) / sample_data["open"]
        np.testing.assert_array_almost_equal(result, expected)

    def test_compile_unary(self, sample_data: dict) -> None:
        fn, _ = expr_to_func("-close")
        result = fn(**sample_data)
        np.testing.assert_array_almost_equal(result, -sample_data["close"])

    def test_compile_abs(self, sample_data: dict) -> None:
        fn, _ = expr_to_func("abs(close)")
        result = fn(**sample_data)
        np.testing.assert_array_almost_equal(result, np.abs(sample_data["close"]))

    def test_compile_sqrt(self, sample_data: dict) -> None:
        fn, _ = expr_to_func("sqrt(volume)")
        result = fn(**sample_data)
        np.testing.assert_array_almost_equal(result, np.sqrt(sample_data["volume"]))

    def test_compile_unknown_var_raises(self) -> None:
        with pytest.raises(NameError, match="未知变量"):
            expr_to_func("unknown_var + 1")

    def test_compile_unknown_func_raises(self) -> None:
        with pytest.raises(NameError, match="未知函数"):
            expr_to_func("unknown_func(close)")

    def test_evaluate_expr(self, sample_data: dict) -> None:
        result = evaluate_expr("close * 2", **sample_data)
        expected = sample_data["close"] * 2
        np.testing.assert_array_almost_equal(result, expected)


class TestASTUtils:
    """AST 工具函数测试"""

    def test_tree_depth_simple(self) -> None:
        node = parse_expr("close")
        assert tree_depth(node) == 1

    def test_tree_depth_nested(self) -> None:
        node = parse_expr("ts_mean(close + open, 20)")
        assert tree_depth(node) == 3

    def test_collect_functions(self) -> None:
        node = parse_expr("ts_mean(close, 20) + ts_std(volume, 10)")
        funcs = collect_functions(node)
        assert set(funcs) == {"ts_mean", "ts_std"}

    def test_collect_variables(self) -> None:
        node = parse_expr("close + volume - open_interest")
        vars_list = collect_variables(node)
        assert set(vars_list) == {"close", "volume", "open_interest"}

    def test_expr_to_string(self) -> None:
        node = parse_expr("close + 1")
        s = expr_to_string(node)
        assert s == "(close + 1)"
