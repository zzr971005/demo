"""
公式化因子定义语言 (Formula DSL)

使用递归下降解析器实现表达式解析，性能满足实时要求（<10ms per expression）。
支持：
- 字符串表达式 → AST → 可执行函数
- AST 序列化/反序列化（JSON）
- 变量：open, high, low, close, volume, open_interest
- 函数调用：ts_mean(close, 20), zscore(volume, 10) 等
- 二元运算：+, -, *, /, **
- 一元运算：-, abs, log, sign, sqrt
"""

from __future__ import annotations

import json
import operator
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .registry import FACTOR_REGISTRY

# ---------------------------------------------------------------------------
# AST 节点定义
# ---------------------------------------------------------------------------

@dataclass
class ExprNode:
    """表达式树节点基类"""
    pass


@dataclass
class VarNode(ExprNode):
    name: str

    def __repr__(self) -> str:
        return f"Var({self.name})"


@dataclass
class ConstNode(ExprNode):
    value: Union[int, float]

    def __repr__(self) -> str:
        return f"Const({self.value})"


@dataclass
class BinOpNode(ExprNode):
    op: str  # +, -, *, /, **
    left: ExprNode
    right: ExprNode

    def __repr__(self) -> str:
        return f"BinOp({self.op}, {self.left}, {self.right})"


@dataclass
class UnaryOpNode(ExprNode):
    op: str  # neg, abs, log, sign, sqrt
    operand: ExprNode

    def __repr__(self) -> str:
        return f"UnaryOp({self.op}, {self.operand})"


@dataclass
class FuncNode(ExprNode):
    name: str
    args: List[ExprNode]

    def __repr__(self) -> str:
        return f"Func({self.name}, {self.args})"


# ---------------------------------------------------------------------------
# 词法分析 (Tokenizer)
# ---------------------------------------------------------------------------

TOKEN_SPEC = [
    ("NUMBER", r"\d+\.?\d*"),
    ("NAME", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP2", r"\*\*|==|!=|<=|>="),
    ("OP1", r"[+\-*/(),]"),
    ("SKIP", r"[ \t]+"),
    ("MISMATCH", r"."),
]

import re

_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
)


def tokenize(expr: str) -> List[Tuple[str, str]]:
    if not expr or not expr.strip():
        raise SyntaxError("空表达式")
    tokens = []
    for mo in _TOKEN_RE.finditer(expr):
        kind = mo.lastgroup
        value = mo.group()
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            raise SyntaxError(f"非法字符: {value!r} at position {mo.start()}")
        tokens.append((kind, value))
    return tokens


# ---------------------------------------------------------------------------
# 语法分析 (Recursive Descent Parser)
# ---------------------------------------------------------------------------

class Parser:
    """
    Grammar:
        expr     -> term (( '+' | '-' ) term)*
        term     -> power (( '*' | '/' ) power)*
        power    -> unary ( '**' unary )*
        unary    -> ( '-' | 'abs' | 'log' | 'sign' | 'sqrt' ) unary | primary
        primary  -> NUMBER | NAME | NAME '(' args ')' | '(' expr ')'
        args     -> expr (',' expr)* | empty
    """

    def __init__(self, tokens: List[Tuple[str, str]]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.n = len(tokens)

    def peek(self) -> Optional[Tuple[str, str]]:
        if self.pos < self.n:
            return self.tokens[self.pos]
        return None

    def consume(self, expected_kind: Optional[str] = None, expected_value: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("表达式意外结束")
        kind, value = tok
        if expected_kind and kind != expected_kind:
            raise SyntaxError(f"期望 {expected_kind}，得到 {kind}({value})")
        if expected_value and value != expected_value:
            raise SyntaxError(f"期望 {expected_value!r}，得到 {value!r}")
        self.pos += 1
        return tok

    def parse(self) -> ExprNode:
        node = self.expr()
        if self.peek() is not None:
            raise SyntaxError(f"解析结束后仍有未处理 token: {self.peek()}")
        return node

    def expr(self) -> ExprNode:
        node = self.term()
        while True:
            tok = self.peek()
            if tok and tok[1] in ("+", "-"):
                self.consume()
                right = self.term()
                node = BinOpNode(op=tok[1], left=node, right=right)
            else:
                break
        return node

    def term(self) -> ExprNode:
        node = self.power()
        while True:
            tok = self.peek()
            if tok and tok[1] in ("*", "/"):
                self.consume()
                right = self.power()
                node = BinOpNode(op=tok[1], left=node, right=right)
            else:
                break
        return node

    def power(self) -> ExprNode:
        node = self.unary()
        while True:
            tok = self.peek()
            if tok and tok[1] == "**":
                self.consume()
                right = self.unary()
                node = BinOpNode(op="**", left=node, right=right)
            else:
                break
        return node

    def unary(self) -> ExprNode:
        tok = self.peek()
        if tok and tok[1] == "-":
            self.consume()
            operand = self.unary()
            return UnaryOpNode(op="neg", operand=operand)
        if tok and tok[0] == "NAME" and tok[1] in ("abs", "log", "sign", "sqrt"):
            self.consume()
            operand = self.unary()
            return UnaryOpNode(op=tok[1], operand=operand)
        return self.primary()

    def primary(self) -> ExprNode:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("表达式意外结束")

        kind, value = tok

        if kind == "NUMBER":
            self.consume()
            if "." in value:
                return ConstNode(float(value))
            return ConstNode(int(value))

        if kind == "NAME":
            self.consume()
            next_tok = self.peek()
            if next_tok and next_tok[1] == "(":
                self.consume(expected_value="(")
                args = self.args()
                self.consume(expected_value=")")
                return FuncNode(name=value, args=args)
            return VarNode(name=value)

        if kind == "OP1" and value == "(":
            self.consume()
            node = self.expr()
            self.consume(expected_value=")")
            return node

        raise SyntaxError(f"意外的 token: {kind}({value})")

    def args(self) -> List[ExprNode]:
        if self.peek() is None or (self.peek()[1] == ")"):
            return []
        args = [self.expr()]
        while True:
            tok = self.peek()
            if tok and tok[1] == ",":
                self.consume()
                args.append(self.expr())
            else:
                break
        return args


# ---------------------------------------------------------------------------
# 表达式解析入口
# ---------------------------------------------------------------------------

def parse_expr(expr: str) -> ExprNode:
    tokens = tokenize(expr)
    if not tokens:
        raise SyntaxError("空表达式")
    parser = Parser(tokens)
    return parser.parse()


# ---------------------------------------------------------------------------
# AST 序列化 / 反序列化
# ---------------------------------------------------------------------------

def node_to_dict(node: ExprNode) -> Dict[str, Any]:
    if isinstance(node, VarNode):
        return {"type": "var", "name": node.name}
    if isinstance(node, ConstNode):
        return {"type": "const", "value": node.value}
    if isinstance(node, BinOpNode):
        return {
            "type": "binop",
            "op": node.op,
            "left": node_to_dict(node.left),
            "right": node_to_dict(node.right),
        }
    if isinstance(node, UnaryOpNode):
        return {
            "type": "unary",
            "op": node.op,
            "operand": node_to_dict(node.operand),
        }
    if isinstance(node, FuncNode):
        return {
            "type": "func",
            "name": node.name,
            "args": [node_to_dict(a) for a in node.args],
        }
    raise TypeError(f"未知节点类型: {type(node)}")


def dict_to_node(d: Dict[str, Any]) -> ExprNode:
    t = d["type"]
    if t == "var":
        return VarNode(name=d["name"])
    if t == "const":
        return ConstNode(value=d["value"])
    if t == "binop":
        return BinOpNode(
            op=d["op"],
            left=dict_to_node(d["left"]),
            right=dict_to_node(d["right"]),
        )
    if t == "unary":
        return UnaryOpNode(op=d["op"], operand=dict_to_node(d["operand"]))
    if t == "func":
        return FuncNode(name=d["name"], args=[dict_to_node(a) for a in d["args"]])
    raise ValueError(f"未知节点类型: {t}")


def serialize(node: ExprNode) -> str:
    return json.dumps(node_to_dict(node), ensure_ascii=False, separators=(",", ":"))


def deserialize(s: str) -> ExprNode:
    return dict_to_node(json.loads(s))


# ---------------------------------------------------------------------------
# AST → 可执行函数
# ---------------------------------------------------------------------------

# 合法变量名（OHLCV + 持仓量）
VALID_VARIABLES = {"open", "high", "low", "close", "volume", "open_interest"}

# 一元运算实现
_UNARY_OPS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "neg": lambda x: -x,
    "abs": np.abs,
    "log": lambda x: np.log(np.clip(x, 1e-12, None)),
    "sign": np.sign,
    "sqrt": lambda x: np.sqrt(np.clip(x, 0.0, None)),
}

# 二元运算实现
_BIN_OPS: Dict[str, Callable[[np.ndarray, np.ndarray], np.ndarray]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": lambda a, b: np.divide(a, b, out=np.zeros_like(a, dtype=np.float64), where=np.abs(b) > 1e-12),
    "**": np.power,
}


def compile_expr(node: ExprNode) -> Callable[..., np.ndarray]:
    """
    将 AST 编译为可执行函数。
    返回的函数签名: fn(open, high, low, close, volume, open_interest) -> np.ndarray
    """
    code = _compile_node(node)

    def _exec(open: np.ndarray, high: np.ndarray, low: np.ndarray,
              close: np.ndarray, volume: np.ndarray, open_interest: np.ndarray) -> np.ndarray:
        env = {
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "open_interest": open_interest,
        }
        return code(env)

    return _exec


def _compile_node(node: ExprNode) -> Callable[[Dict[str, np.ndarray]], np.ndarray]:
    if isinstance(node, VarNode):
        if node.name not in VALID_VARIABLES:
            raise NameError(f"未知变量: {node.name}，合法变量: {VALID_VARIABLES}")
        return lambda env: env[node.name]

    if isinstance(node, ConstNode):
        val = float(node.value)
        return lambda env: np.array(val)

    if isinstance(node, BinOpNode):
        left_fn = _compile_node(node.left)
        right_fn = _compile_node(node.right)
        op_fn = _BIN_OPS[node.op]
        return lambda env: op_fn(left_fn(env), right_fn(env))

    if isinstance(node, UnaryOpNode):
        operand_fn = _compile_node(node.operand)
        op_fn = _UNARY_OPS[node.op]
        return lambda env: op_fn(operand_fn(env))

    if isinstance(node, FuncNode):
        if node.name not in FACTOR_REGISTRY:
            raise NameError(f"未知函数: {node.name}，已注册函数: {list(FACTOR_REGISTRY.keys())}")
        meta = FACTOR_REGISTRY[node.name]
        arg_fns = [_compile_node(a) for a in node.args]
        func = meta.func
        if func is None:
            raise RuntimeError(f"函数 {node.name} 未绑定实现")

        def _call(env: Dict[str, np.ndarray], func=func, arg_fns=arg_fns, params=meta.params) -> np.ndarray:
            args = [fn(env) for fn in arg_fns]
            # 将 numpy scalar / 0-d array 参数转为 Python 原生类型，避免 numba 类型推断问题
            def _to_py(v):
                if isinstance(v, np.ndarray) and v.ndim == 0:
                    return v.item()
                if isinstance(v, (np.integer, np.floating)):
                    return v.item()
                return v
            args = [_to_py(a) for a in args]
            # 按注册签名将标量参数强制为登记类型（如 int 窗口）。
            # DSL 常量恒被编译为 float，若不按签名强转，window=15.0 会让
            # numba 整型索引报错、因子静默崩溃（属"看似在跑其实挂掉"一类）。
            coerced = []
            for i, a in enumerate(args):
                if i < len(params) and not isinstance(a, np.ndarray):
                    ptype = params[i][1]
                    if ptype in (int, float):
                        try:
                            a = ptype(a)
                        except (TypeError, ValueError):
                            pass
                coerced.append(a)
            return func(*coerced)

        return _call

    raise TypeError(f"未知节点类型: {type(node)}")


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def expr_to_func(expr: str) -> Tuple[Callable[..., np.ndarray], ExprNode]:
    """字符串表达式 → (可执行函数, AST)"""
    t0 = time.perf_counter()
    ast = parse_expr(expr)
    t1 = time.perf_counter()
    fn = compile_expr(ast)
    t2 = time.perf_counter()
    # 性能日志（调试用）
    # print(f"[DSL] parse={t1-t0:.4f}s compile={t2-t1:.4f}s total={t2-t0:.4f}s")
    return fn, ast


def evaluate_expr(expr: str, open: np.ndarray, high: np.ndarray, low: np.ndarray,
                  close: np.ndarray, volume: np.ndarray, open_interest: np.ndarray) -> np.ndarray:
    """一键求值：表达式字符串 + 数据 → 结果数组"""
    fn, _ = expr_to_func(expr)
    return fn(open, high, low, close, volume, open_interest)


# ---------------------------------------------------------------------------
# AST 遍历工具
# ---------------------------------------------------------------------------

def walk_dfs(node: ExprNode, callback: Callable[[ExprNode], None]) -> None:
    """深度优先遍历 AST"""
    callback(node)
    if isinstance(node, BinOpNode):
        walk_dfs(node.left, callback)
        walk_dfs(node.right, callback)
    elif isinstance(node, UnaryOpNode):
        walk_dfs(node.operand, callback)
    elif isinstance(node, FuncNode):
        for arg in node.args:
            walk_dfs(arg, callback)


def tree_depth(node: ExprNode) -> int:
    """计算表达式树深度"""
    if isinstance(node, (VarNode, ConstNode)):
        return 1
    if isinstance(node, UnaryOpNode):
        return 1 + tree_depth(node.operand)
    if isinstance(node, BinOpNode):
        return 1 + max(tree_depth(node.left), tree_depth(node.right))
    if isinstance(node, FuncNode):
        if not node.args:
            return 1
        return 1 + max(tree_depth(a) for a in node.args)
    return 1


def collect_nodes(node: ExprNode, predicate: Optional[Callable[[ExprNode], bool]] = None) -> List[ExprNode]:
    """收集满足条件的节点"""
    result: List[ExprNode] = []

    def _cb(n: ExprNode) -> None:
        if predicate is None or predicate(n):
            result.append(n)

    walk_dfs(node, _cb)
    return result


def collect_functions(node: ExprNode) -> List[str]:
    """收集表达式中所有函数名"""
    return [n.name for n in collect_nodes(node, lambda n: isinstance(n, FuncNode))]


def collect_variables(node: ExprNode) -> List[str]:
    """收集表达式中所有变量名"""
    return [n.name for n in collect_nodes(node, lambda n: isinstance(n, VarNode))]


def expr_to_string(node: ExprNode) -> str:
    """AST 还原为字符串表达式"""
    if isinstance(node, VarNode):
        return node.name
    if isinstance(node, ConstNode):
        return str(node.value)
    if isinstance(node, BinOpNode):
        left = expr_to_string(node.left)
        right = expr_to_string(node.right)
        return f"({left} {node.op} {right})"
    if isinstance(node, UnaryOpNode):
        operand = expr_to_string(node.operand)
        if node.op == "neg":
            return f"(-{operand})"
        return f"{node.op}({operand})"
    if isinstance(node, FuncNode):
        args = ", ".join(expr_to_string(a) for a in node.args)
        return f"{node.name}({args})"
    return ""
