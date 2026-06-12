"""
遗传编程交叉和变异算子

实现GP树的交叉、变异等遗传操作
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .gp_individual import (
    GPIndividual,
    GPNode,
    get_all_nodes,
    random_function_node,
    random_terminal,
)
from ..factors.registry import FACTOR_REGISTRY


# ---------------------------------------------------------------------------
# 参数类型检查辅助函数
# ---------------------------------------------------------------------------

def _get_expected_child_type(parent_node: GPNode, child_index: int) -> Optional[str]:
    """
    获取父节点对指定位置子节点的期望类型
    
    Returns
    -------
    'var' - 期望变量节点
    'const' - 期望常量节点
    None - 无特殊要求
    """
    if parent_node.node_type != 'func':
        return None
    
    func_meta = FACTOR_REGISTRY.get(parent_node.name)
    if func_meta is None or child_index >= len(func_meta.params):
        return None
    
    param_name, param_type, param_default = func_meta.params[child_index]
    if param_type == str:
        return 'var'  # 字符串类型参数需要变量节点
    elif param_type in (int, float):
        return 'const'  # 数值类型参数需要常量节点
    else:
        return None


def _get_expected_param_type(parent_node: GPNode, child_index: int) -> Optional[type]:
    """
    获取父节点对指定位置子节点的期望参数类型（int/float）
    
    Returns
    -------
    int - 期望整数参数
    float - 期望浮点参数
    None - 无特殊要求
    """
    if parent_node.node_type != 'func':
        return None
    
    func_meta = FACTOR_REGISTRY.get(parent_node.name)
    if func_meta is None or child_index >= len(func_meta.params):
        return None
    
    param_name, param_type, param_default = func_meta.params[child_index]
    if param_type in (int, float):
        return param_type
    else:
        return None

def _check_node_compatibility(
    source_node: GPNode,
    target_parent: GPNode,
    target_child_index: int
) -> bool:
    """
    检查源节点是否可以交换到目标位置
    
    主要检查参数类型兼容性，避免常量被交换到变量位置
    同时检查常量的值类型（int/float）是否匹配
    """
    expected_type = _get_expected_child_type(target_parent, target_child_index)
    
    if expected_type is None:
        return True  # 无特殊要求，允许交换
    
    if expected_type == 'var':
        # 期望变量节点，必须是var类型
        return source_node.node_type == 'var'
    elif expected_type == 'const':
        # 期望常量节点，必须是const类型
        if source_node.node_type != 'const':
            return False
        
        # 进一步检查常量的值类型是否匹配
        expected_param_type = _get_expected_param_type(target_parent, target_child_index)
        if expected_param_type == int:
            # 期望整数参数，源常量必须是整数
            return isinstance(source_node.value, int) or (isinstance(source_node.value, float) and source_node.value.is_integer())
        elif expected_param_type == float:
            # 期望浮点参数，源常量可以是任意数值
            return isinstance(source_node.value, (int, float))
    
    return True

# ---------------------------------------------------------------------------
# 交叉算子
# ---------------------------------------------------------------------------

def subtree_crossover(
    parent1: GPIndividual,
    parent2: GPIndividual,
    max_depth: int = 5,
) -> Tuple[GPIndividual, GPIndividual]:
    """
    子树交叉算子
    
    从两个父代中随机选择子树进行交换
    
    Returns
    -------
    (offspring1, offspring2) 两个子代个体
    """
    # 深拷贝父代
    offspring1 = parent1.clone()
    offspring2 = parent2.clone()
    
    # 获取所有可交换的节点（排除根节点）
    nodes1 = [(n, p) for n, p in get_all_nodes(offspring1.root) if len(p) > 0]
    nodes2 = [(n, p) for n, p in get_all_nodes(offspring2.root) if len(p) > 0]
    
    if not nodes1 or not nodes2:
        # 无法交叉，返回克隆
        return offspring1, offspring2
    
    # 随机选择交换点
    node1, path1 = random.choice(nodes1)
    node2, path2 = random.choice(nodes2)
    
    # 检查深度约束
    # 计算交换后的深度
    depth1 = len(path1) + node2.calculate_depth()
    depth2 = len(path2) + node1.calculate_depth()
    
    if depth1 > max_depth or depth2 > max_depth:
        # 超过最大深度，不进行交叉
        return offspring1, offspring2
    
    # 获取父节点
    parent_path1 = path1[:-1]
    child_idx1 = path1[-1]
    if parent_path1:
        parent_node1 = get_node_at_path(offspring1.root, parent_path1)
    else:
        parent_node1 = offspring1.root
    
    parent_path2 = path2[:-1]
    child_idx2 = path2[-1]
    if parent_path2:
        parent_node2 = get_node_at_path(offspring2.root, parent_path2)
    else:
        parent_node2 = offspring2.root
    
    # 检查参数类型兼容性
    # 避免常量被交换到变量位置（如 money_flow(high, 20, ...) 中的 20 被交换为变量 low）
    if not _check_node_compatibility(node2, parent_node1, child_idx1):
        # 类型不兼容，跳过交叉
        return offspring1, offspring2
    
    if not _check_node_compatibility(node1, parent_node2, child_idx2):
        # 类型不兼容，跳过交叉
        return offspring1, offspring2
    
    # 执行交换
    parent_node1.children[child_idx1] = node2.clone()
    parent_node2.children[child_idx2] = node1.clone()
    
    # 更新元信息
    offspring1.origin = 'crossover'
    offspring1.parent_ids = [parent1.id, parent2.id]
    offspring1.generation = max(parent1.generation, parent2.generation) + 1
    
    offspring2.origin = 'crossover'
    offspring2.parent_ids = [parent1.id, parent2.id]
    offspring2.generation = max(parent1.generation, parent2.generation) + 1
    
    return offspring1, offspring2


def one_point_crossover(
    parent1: GPIndividual,
    parent2: GPIndividual,
    max_depth: int = 5,
) -> Tuple[GPIndividual, GPIndividual]:
    """
    单点交叉（针对二元操作节点）
    
    只在二元操作节点（+、-、*、/）上进行交叉
    """
    offspring1 = parent1.clone()
    offspring2 = parent2.clone()
    
    # 找到所有二元操作节点
    binop_nodes1 = [
        (n, p) for n, p in get_all_nodes(offspring1.root)
        if n.node_type == 'binop' and len(p) > 0
    ]
    binop_nodes2 = [
        (n, p) for n, p in get_all_nodes(offspring2.root)
        if n.node_type == 'binop' and len(p) > 0
    ]
    
    if not binop_nodes1 or not binop_nodes2:
        return offspring1, offspring2
    
    # 随机选择
    node1, path1 = random.choice(binop_nodes1)
    node2, path2 = random.choice(binop_nodes2)
    
    # 检查深度
    depth1 = len(path1) + node2.calculate_depth()
    depth2 = len(path2) + node1.calculate_depth()
    
    if depth1 > max_depth or depth2 > max_depth:
        return offspring1, offspring2
    
    # 执行交换
    parent_path1 = path1[:-1]
    child_idx1 = path1[-1]
    if parent_path1:
        parent_node1 = get_node_at_path(offspring1.root, parent_path1)
    else:
        parent_node1 = offspring1.root
    
    parent_path2 = path2[:-1]
    child_idx2 = path2[-1]
    if parent_path2:
        parent_node2 = get_node_at_path(offspring2.root, parent_path2)
    else:
        parent_node2 = offspring2.root
    
    parent_node1.children[child_idx1] = node2.clone()
    parent_node2.children[child_idx2] = node1.clone()
    
    offspring1.origin = 'crossover'
    offspring1.parent_ids = [parent1.id, parent2.id]
    offspring1.generation = max(parent1.generation, parent2.generation) + 1
    
    offspring2.origin = 'crossover'
    offspring2.parent_ids = [parent1.id, parent2.id]
    offspring2.generation = max(parent1.generation, parent2.generation) + 1
    
    return offspring1, offspring2


# ---------------------------------------------------------------------------
# 变异算子
# ---------------------------------------------------------------------------

def subtree_mutation(
    individual: GPIndividual,
    max_depth: int = 3,
    mutation_rate: float = 0.1,
) -> GPIndividual:
    """
    子树变异
    
    随机选择一个子树，替换为新生成的子树
    """
    offspring = individual.clone()
    
    # 获取所有非根节点
    nodes = [(n, p) for n, p in get_all_nodes(offspring.root) if len(p) > 0]
    
    if not nodes:
        return offspring
    
    # 随机选择变异点
    node, path = random.choice(nodes)
    
    # 替换位置
    parent_path = path[:-1]
    child_idx = path[-1]
    if parent_path:
        parent_node = get_node_at_path(offspring.root, parent_path)
    else:
        parent_node = offspring.root

    # 生成新子树并检查深度
    expected_type = _get_expected_child_type(parent_node, child_idx)
    new_subtree = random_function_node(max_depth=max_depth, expected_type=expected_type)
    new_depth = len(path) + new_subtree.calculate_depth()
    if new_depth > max_depth + 2:  # 允许稍微超过一点
        return offspring
    
    # 检查参数类型兼容性
    # 新子树的根节点类型必须与父节点期望的参数类型匹配
    if not _check_node_compatibility(new_subtree, parent_node, child_idx):
        # 类型不兼容，跳过变异
        return offspring
    
    parent_node.children[child_idx] = new_subtree
    
    offspring.origin = 'mutation'
    offspring.parent_ids = [individual.id]
    offspring.generation = individual.generation + 1
    
    return offspring


def point_mutation(
    individual: GPIndividual,
    mutation_rate: float = 0.1,
) -> GPIndividual:
    """
    点变异
    
    随机选择一个节点，改变其值（不改变结构）
    """
    offspring = individual.clone()
    
    # 获取所有节点
    nodes = get_all_nodes(offspring.root)
    
    if not nodes:
        return offspring
    
    # 随机选择节点
    node, path = random.choice(nodes)
    
    if node.node_type == 'func':
        # 函数节点：换一个同类型的函数
        from quant_engine.factors.registry import FACTOR_REGISTRY
        
        if node.family:
            # 同族函数
            same_family = [
                name for name, meta in FACTOR_REGISTRY.items()
                if meta.family == node.family and name != node.name
            ]
            if same_family and random.random() < mutation_rate:
                node.name = random.choice(same_family)
    
    elif node.node_type == 'binop':
        # 二元操作：换操作符
        if random.random() < mutation_rate:
            node.name = random.choice(['+', '-', '*', '/'])
    
    elif node.node_type == 'const':
        # 常量：微调值
        if random.random() < mutation_rate and node.value is not None:
            # 确保参数类型正确
            # 通过检查父节点判断参数类型
            parent_node = get_node_at_path(offspring.root, path[:-1]) if len(path) > 0 else None
            param_type = None
            
            if parent_node and parent_node.node_type == 'func':
                from quant_engine.factors.registry import FACTOR_REGISTRY
                func_meta = FACTOR_REGISTRY.get(parent_node.name)
                if func_meta:
                    # 找到当前子节点在父节点中的索引
                    child_idx = path[-1] if len(path) > 0 else 0
                    if child_idx < len(func_meta.params):
                        param_name, param_type, param_default = func_meta.params[child_idx]
            
            if param_type == int:
                # 整数类型参数：基于当前值生成随机变体，增加多样性
                if node.value is not None:
                    variation = random.randint(-3, 3)
                    new_value = max(1, int(node.value) + variation)
                else:
                    new_value = random.randint(1, 100)
                # 确保为正数
                new_value = abs(new_value)
            else:
                # 浮点参数：使用微调
                noise = random.uniform(-0.1, 0.1)
                new_value = round(node.value * (1 + noise), 4)

            node.value = new_value
    
    elif node.node_type == 'var':
        # 变量：换变量名
        if random.random() < mutation_rate:
            node.name = random.choice(['open', 'high', 'low', 'close', 'volume'])
    
    offspring.origin = 'mutation'
    offspring.parent_ids = [individual.id]
    offspring.generation = individual.generation + 1
    
    return offspring


def hoist_mutation(
    individual: GPIndividual,
    max_depth: int = 5,
) -> GPIndividual:
    """
    提升变异（Hoist Mutation）
    
    随机选择一个子树，将其提升为根节点
    这有助于简化过深的树
    """
    offspring = individual.clone()
    
    # 获取所有非根节点
    nodes = [(n, p) for n, p in get_all_nodes(offspring.root) if len(p) > 0]
    
    if not nodes:
        return offspring
    
    # 随机选择子树
    node, path = random.choice(nodes)
    
    # 检查新深度
    if node.calculate_depth() > max_depth:
        return offspring
    
    # 替换根节点
    offspring.root = node.clone()
    
    offspring.origin = 'mutation'
    offspring.parent_ids = [individual.id]
    offspring.generation = individual.generation + 1
    
    return offspring


def shrink_mutation(
    individual: GPIndividual,
) -> GPIndividual:
    """
    收缩变异（Shrink Mutation）
    
    随机选择一个函数节点，替换为终端节点
    这有助于简化树结构
    """
    offspring = individual.clone()
    
    # 获取所有函数节点（排除根节点）
    func_nodes = [
        (n, p) for n, p in get_all_nodes(offspring.root)
        if n.node_type == 'func' and len(p) > 0
    ]
    
    if not func_nodes:
        return offspring
    
    # 随机选择
    node, path = random.choice(func_nodes)
    
    # 替换为终端
    terminal = random_terminal()
    
    parent_path = path[:-1]
    child_idx = path[-1]
    if parent_path:
        parent_node = get_node_at_path(offspring.root, parent_path)
    else:
        parent_node = offspring.root
    
    parent_node.children[child_idx] = terminal
    
    offspring.origin = 'mutation'
    offspring.parent_ids = [individual.id]
    offspring.generation = individual.generation + 1
    
    return offspring


# ---------------------------------------------------------------------------
# 组合算子
# ---------------------------------------------------------------------------

def mutate(
    individual: GPIndividual,
    mutation_rate: float = 0.1,
    subtree_rate: float = 0.4,
    point_rate: float = 0.3,
    hoist_rate: float = 0.15,
    shrink_rate: float = 0.15,
) -> GPIndividual:
    """
    综合变异算子
    
    根据概率选择不同的变异方式
    """
    if random.random() > mutation_rate:
        return individual
    
    r = random.random()
    if r < subtree_rate:
        return subtree_mutation(individual)
    elif r < subtree_rate + point_rate:
        return point_mutation(individual)
    elif r < subtree_rate + point_rate + hoist_rate:
        return hoist_mutation(individual)
    else:
        return shrink_mutation(individual)


def crossover(
    parent1: GPIndividual,
    parent2: GPIndividual,
    crossover_rate: float = 0.9,
    subtree_rate: float = 0.7,
) -> Tuple[Optional[GPIndividual], Optional[GPIndividual]]:
    """
    综合交叉算子
    
    根据概率决定是否交叉，以及交叉方式
    """
    if random.random() > crossover_rate:
        return parent1.clone(), parent2.clone()
    
    if random.random() < subtree_rate:
        return subtree_crossover(parent1, parent2)
    else:
        return one_point_crossover(parent1, parent2)


# ---------------------------------------------------------------------------
# 选择算子
# ---------------------------------------------------------------------------

def tournament_selection(
    population: List[GPIndividual],
    tournament_size: int = 3,
) -> GPIndividual:
    """
    锦标赛选择
    
    随机选择tournament_size个个体，返回适应度最高的
    """
    tournament = random.sample(population, min(tournament_size, len(population)))
    return max(tournament, key=lambda ind: ind.penalized_sharpe)


def roulette_selection(
    population: List[GPIndividual],
) -> GPIndividual:
    """
    轮盘赌选择
    
    按适应度比例选择
    """
    # 确保适应度非负
    fitnesses = [max(0, ind.penalized_sharpe) for ind in population]
    total = sum(fitnesses)
    
    if total == 0:
        return random.choice(population)
    
    r = random.uniform(0, total)
    cumsum = 0
    for ind, fit in zip(population, fitnesses):
        cumsum += fit
        if cumsum >= r:
            return ind
    
    return population[-1]


def rank_selection(
    population: List[GPIndividual],
) -> GPIndividual:
    """
    排名选择
    
    按排名选择，避免早熟收敛
    """
    sorted_pop = sorted(population, key=lambda ind: ind.penalized_sharpe, reverse=True)
    n = len(sorted_pop)
    
    # 排名概率：排名越高概率越大
    total_rank = n * (n + 1) / 2
    r = random.uniform(0, total_rank)
    
    cumsum = 0
    for i, ind in enumerate(sorted_pop):
        cumsum += (n - i)
        if cumsum >= r:
            return ind
    
    return sorted_pop[-1]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def get_node_at_path(root: GPNode, path: List[int]) -> GPNode:
    """通过路径获取节点"""
    node = root
    for idx in path:
        node = node.children[idx]
    return node


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from .gp_individual import random_individual
    
    print("=== 测试交叉算子 ===")
    
    # 生成两个父代
    parent1 = random_individual(max_depth=3, generation=0)
    parent2 = random_individual(max_depth=3, generation=0)
    
    print(f"父代1: {parent1.to_expression()}")
    print(f"父代2: {parent2.to_expression()}")
    
    # 交叉
    offspring1, offspring2 = subtree_crossover(parent1, parent2)
    
    print(f"\n子代1: {offspring1.to_expression()}")
    print(f"子代2: {offspring2.to_expression()}")
    
    print("\n=== 测试变异算子 ===")
    
    # 子树变异
    mutated = subtree_mutation(offspring1)
    print(f"子树变异: {mutated.to_expression()}")
    
    # 点变异
    mutated = point_mutation(offspring1)
    print(f"点变异: {mutated.to_expression()}")
    
    # 提升变异
    mutated = hoist_mutation(offspring1)
    print(f"提升变异: {mutated.to_expression()}")
    
    # 收缩变异
    mutated = shrink_mutation(offspring1)
    print(f"收缩变异: {mutated.to_expression()}")
