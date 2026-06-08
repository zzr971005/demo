"""
遗传编程个体表示

实现GP树形结构个体的编码、解码和操作
"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from quant_engine.factors.formula_dsl import (
    BinOpNode,
    ConstNode,
    ExprNode,
    FuncNode,
    VarNode,
    parse_expr,
    serialize,
)
from quant_engine.factors.registry import FACTOR_REGISTRY, PrimitiveFamily


# ---------------------------------------------------------------------------
# GP个体表示
# ---------------------------------------------------------------------------

@dataclass
class GPNode:
    """GP树节点"""
    
    # 节点类型: 'func' | 'var' | 'const' | 'binop'
    node_type: str
    
    # 函数名/变量名/操作符
    name: str
    
    # 子节点（对于函数和二元操作）
    children: List[GPNode] = field(default_factory=list)
    
    # 常量值
    value: Optional[float] = None
    
    # 节点深度（运行时计算）
    depth: int = 0
    
    # 节点所属族（如果是函数节点）
    family: Optional[PrimitiveFamily] = None
    
    def to_expr_node(self) -> ExprNode:
        """转换为DSL表达式节点"""
        if self.node_type == 'var':
            return VarNode(name=self.name)
        elif self.node_type == 'const':
            return ConstNode(value=self.value if self.value is not None else 0.0)
        elif self.node_type == 'binop':
            if len(self.children) != 2:
                raise ValueError(f"Binary op {self.name} must have 2 children")
            return BinOpNode(
                op=self.name,
                left=self.children[0].to_expr_node(),
                right=self.children[1].to_expr_node(),
            )
        elif self.node_type == 'func':
            return FuncNode(
                name=self.name,
                args=[child.to_expr_node() for child in self.children],
            )
        else:
            raise ValueError(f"Unknown node type: {self.node_type}")
    
    def to_expression(self) -> str:
        """转换为表达式字符串"""
        node = self.to_expr_node()
        return self._node_to_string(node)
    
    def _node_to_string(self, node: ExprNode) -> str:
        """递归转换为字符串"""
        if isinstance(node, VarNode):
            return node.name
        elif isinstance(node, ConstNode):
            # 统一格式化：整数显示为整数，浮点数保留5位小数
            if node.value is None:
                return "0"
            if isinstance(node.value, int) or (isinstance(node.value, float) and node.value.is_integer()):
                return str(int(node.value))
            else:
                return f"{node.value:.5f}"
        elif isinstance(node, BinOpNode):
            left = self._node_to_string(node.left)
            right = self._node_to_string(node.right)
            return f"({left} {node.op} {right})"
        elif isinstance(node, FuncNode):
            args = ", ".join(self._node_to_string(arg) for arg in node.args)
            return f"{node.name}({args})"
        else:
            return ""
    
    def calculate_depth(self) -> int:
        """计算节点深度"""
        if not self.children:
            self.depth = 1
        else:
            self.depth = 1 + max(child.calculate_depth() for child in self.children)
        return self.depth
    
    def count_nodes(self) -> int:
        """计算子树节点数"""
        if not self.children:
            return 1
        return 1 + sum(child.count_nodes() for child in self.children)
    
    def collect_functions(self) -> Set[str]:
        """收集所有函数名"""
        funcs = set()
        if self.node_type == 'func':
            funcs.add(self.name)
        for child in self.children:
            funcs.update(child.collect_functions())
        return funcs
    
    def collect_families(self) -> Set[PrimitiveFamily]:
        """收集所有族"""
        families = set()
        if self.family:
            families.add(self.family)
        for child in self.children:
            families.update(child.collect_families())
        return families
    
    def clone(self) -> GPNode:
        """深拷贝节点"""
        return GPNode(
            node_type=self.node_type,
            name=self.name,
            children=[child.clone() for child in self.children],
            value=self.value,
            depth=self.depth,
            family=self.family,
        )


@dataclass
class GPIndividual:
    """GP个体"""
    
    # 根节点
    root: GPNode
    
    # 个体ID
    id: str = field(default_factory=lambda: f"ind_{random.randint(10000, 99999)}")
    
    # 适应度值
    fitness: Dict[str, float] = field(default_factory=dict)
    
    # 原始夏普比率（未惩罚）
    raw_sharpe: float = 0.0
    
    # 惩罚后夏普
    penalized_sharpe: float = 0.0
    
    # 其他指标
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # 创建代数
    generation: int = 0
    
    # 父代ID
    parent_ids: List[str] = field(default_factory=list)
    
    # 创建操作: 'random' | 'crossover' | 'mutation' | 'elitism'
    origin: str = 'random'
    
    def to_expression(self) -> str:
        """转换为表达式"""
        return self.root.to_expression()
    
    def get_depth(self) -> int:
        """获取树深度"""
        return self.root.calculate_depth()
    
    def get_node_count(self) -> int:
        """获取节点数"""
        return self.root.count_nodes()
    
    def get_functions(self) -> Set[str]:
        """获取使用的函数"""
        return self.root.collect_functions()
    
    def get_families(self) -> Set[PrimitiveFamily]:
        """获取使用的族"""
        return self.root.collect_families()
    
    def clone(self) -> GPIndividual:
        """深拷贝个体"""
        return GPIndividual(
            root=self.root.clone(),
            id=f"ind_{random.randint(10000, 99999)}",
            fitness=deepcopy(self.fitness),
            raw_sharpe=self.raw_sharpe,
            penalized_sharpe=self.penalized_sharpe,
            metrics=deepcopy(self.metrics),
            generation=self.generation,
            parent_ids=[self.id],
            origin='elitism',
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'id': self.id,
            'expression': self.to_expression(),
            'depth': self.get_depth(),
            'node_count': self.get_node_count(),
            'fitness': self.fitness,
            'raw_sharpe': self.raw_sharpe,
            'penalized_sharpe': self.penalized_sharpe,
            'metrics': self.metrics,
            'generation': self.generation,
            'parent_ids': self.parent_ids,
            'origin': self.origin,
            'functions': list(self.get_functions()),
            'families': [f.value for f in self.get_families()],
        }


# ---------------------------------------------------------------------------
# 从DSL表达式创建GP个体
# ---------------------------------------------------------------------------

def expr_node_to_gp(node: ExprNode) -> GPNode:
    """将DSL表达式节点转换为GP节点"""
    if isinstance(node, VarNode):
        return GPNode(node_type='var', name=node.name)
    elif isinstance(node, ConstNode):
        return GPNode(node_type='const', name='const', value=node.value)
    elif isinstance(node, BinOpNode):
        left = expr_node_to_gp(node.left)
        right = expr_node_to_gp(node.right)
        gp_node = GPNode(
            node_type='binop',
            name=node.op,
            children=[left, right],
        )
        gp_node.calculate_depth()
        return gp_node
    elif isinstance(node, FuncNode):
        children = [expr_node_to_gp(arg) for arg in node.args]
        
        # 查找函数所属族
        family = None
        if node.name in FACTOR_REGISTRY:
            family = FACTOR_REGISTRY[node.name].family
        
        gp_node = GPNode(
            node_type='func',
            name=node.name,
            children=children,
            family=family,
        )
        gp_node.calculate_depth()
        return gp_node
    else:
        raise ValueError(f"Unknown node type: {type(node)}")


def create_individual_from_expr(expression: str, generation: int = 0) -> GPIndividual:
    """从表达式创建GP个体"""
    ast = parse_expr(expression)
    root = expr_node_to_gp(ast)
    return GPIndividual(
        root=root,
        generation=generation,
        origin='random',
    )


# ---------------------------------------------------------------------------
# 随机个体生成
# ---------------------------------------------------------------------------

def random_terminal(
    var_names: List[str] = None,
    const_range: Tuple[float, float] = (-10, 10),
    force_type: Optional[str] = None,
) -> GPNode:
    """生成随机终端节点"""
    if var_names is None or not var_names:
        var_names = ['open', 'high', 'low', 'close', 'volume']
    
    if force_type == 'var':
        return GPNode(node_type='var', name=random.choice(var_names))
    if force_type == 'const':
        value = round(random.uniform(*const_range), 4)
        return GPNode(node_type='const', name='const', value=value)
    
    if random.random() < 0.95:  # 95%概率选择变量，避免纯常量表达式
        return GPNode(node_type='var', name=random.choice(var_names))
    else:  # 5%概率选择常量
        value = round(random.uniform(*const_range), 4)
        return GPNode(node_type='const', name='const', value=value)


def random_function_node(
    max_depth: int,
    current_depth: int = 0,
    var_names: List[str] = None,
    expected_type: Optional[str] = None,
) -> GPNode:
    """递归生成随机函数节点"""

    if expected_type in ('var', 'const'):
        return random_terminal(var_names=var_names, force_type=expected_type)

    # 达到最大深度，生成终端
    if current_depth >= max_depth - 1:
        return random_terminal(var_names)
    
    # 随机选择函数
    func_names = list(FACTOR_REGISTRY.keys())
    func_name = random.choice(func_names)
    func_meta = FACTOR_REGISTRY[func_name]
    
    # 生成参数
    children = []
    
    # 根据参数定义生成子节点
    # 参数格式: (param_name, param_type, param_default)
    # param_type 为 str 表示变量名，为 int/float 表示常量
    for param_name, param_type, param_default in func_meta.params:
        if param_type == str:
            # 字符串类型表示变量名（如 'close', 'high', 'low', 'volume'）
            allowed = [param_default] if isinstance(param_default, str) else None
            children.append(random_terminal(var_names=allowed or var_names, force_type='var'))
        elif param_type == int:
            # 整数参数（通常是窗口大小）- 扩大选择范围以增加多样性
            if 'window' in param_name:
                value = random.choice([3, 5, 7, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100])
            elif 'fast' in param_name:
                value = random.choice([3, 5, 7, 10, 12, 15, 20])
            elif 'slow' in param_name:
                value = random.choice([15, 20, 25, 30, 40, 50, 60, 80, 100])
            elif 'days_to_expiry' in param_name:
                value = random.choice([3, 5, 7, 14, 21, 30, 45, 60, 90, 120])
            else:
                # 其他整数参数，基于默认值生成随机变体
                if param_default is not None:
                    variation = random.randint(-5, 5)
                    value = max(1, param_default + variation)
                else:
                    value = random.randint(1, 100)
            children.append(GPNode(node_type='const', name='const', value=value))
        elif param_type == float:
            # 浮点数参数：增加随机性，使用更高精度
            if 'std' in param_name or 'threshold' in param_name:
                value = round(random.uniform(0.3, 5.0), 3)
            elif param_default is not None:
                # 基于默认值生成随机变体，确保为正数，使用更高精度
                if param_default != 0:
                    value = round(abs(param_default) * random.uniform(0.3, 2.0), 5)
                else:
                    value = round(random.uniform(0.05, 2.0), 5)
            else:
                value = round(random.uniform(0.05, 2.0), 5)
            children.append(GPNode(node_type='const', name='const', value=value))
        else:
            # 其他类型，使用随机终端
            children.append(random_terminal(var_names))
    
    node = GPNode(
        node_type='func',
        name=func_name,
        children=children,
        family=func_meta.family,
    )
    node.calculate_depth()
    return node


def random_individual(max_depth: int = 3, var_names: List[str] = None, 
                      generation: int = 0) -> GPIndividual:
    """生成随机GP个体"""
    
    # 50%概率生成简单个体（单个函数）
    if random.random() < 0.5:
        root = random_function_node(max_depth=2, var_names=var_names)
    else:
        # 生成二元操作表达式
        left = random_function_node(max_depth=max_depth-1, var_names=var_names)
        right = random_function_node(max_depth=max_depth-1, var_names=var_names)
        op = random.choice(['+', '-', '*', '/'])
        root = GPNode(
            node_type='binop',
            name=op,
            children=[left, right],
        )
        root.calculate_depth()
    
    return GPIndividual(
        root=root,
        generation=generation,
        origin='random',
    )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def get_all_nodes(root: GPNode) -> List[Tuple[GPNode, List[int]]]:
    """
    获取所有节点及其路径
    
    Returns
    -------
    List of (node, path) tuples where path is list of child indices
    """
    nodes = []
    
    def traverse(node: GPNode, path: List[int]):
        nodes.append((node, path))
        for i, child in enumerate(node.children):
            traverse(child, path + [i])
    
    traverse(root, [])
    return nodes


def get_node_at_path(root: GPNode, path: List[int]) -> GPNode:
    """通过路径获取节点"""
    node = root
    for idx in path:
        node = node.children[idx]
    return node


def replace_node_at_path(root: GPNode, path: List[int], new_node: GPNode) -> None:
    """替换指定路径的节点"""
    if not path:
        raise ValueError("Cannot replace root node")
    
    parent_path = path[:-1]
    child_idx = path[-1]
    
    if parent_path:
        parent = get_node_at_path(root, parent_path)
    else:
        # 直接子节点
        parent = root
    
    parent.children[child_idx] = new_node


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # 测试随机个体生成
    print("=== 测试随机个体生成 ===")
    for i in range(3):
        ind = random_individual(max_depth=3, generation=0)
        print(f"\n个体 {i+1}:")
        print(f"  表达式: {ind.to_expression()}")
        print(f"  深度: {ind.get_depth()}")
        print(f"  节点数: {ind.get_node_count()}")
        print(f"  函数: {ind.get_functions()}")
        print(f"  族: {[f.value for f in ind.get_families()]}")
    
    # 测试从表达式创建
    print("\n=== 测试从表达式创建 ===")
    expr = "ts_mean(close, 20) + ts_std(close, 20) * 0.5"
    ind = create_individual_from_expr(expr, generation=1)
    print(f"表达式: {expr}")
    print(f"解析后: {ind.to_expression()}")
    print(f"深度: {ind.get_depth()}")
    print(f"节点数: {ind.get_node_count()}")
