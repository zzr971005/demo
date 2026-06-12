"""
遗传编程进化主循环

实现标准GP进化流程：
- 种群初始化
- 选择、交叉、变异
- 适应度评估
- 精英保留
- 终止条件检查
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .gp_fitness import FitnessConfig, FitnessEvaluator, FitnessResult
from .gp_individual import GPIndividual, GPNode, random_individual
from .gp_operators import (
    crossover,
    mutate,
    tournament_selection,
    roulette_selection,
    rank_selection,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 进化统计
# ---------------------------------------------------------------------------

@dataclass
class GenerationStats:
    """单代统计信息"""
    generation: int
    population_size: int
    valid_count: int
    
    # 适应度统计
    min_fitness: float
    max_fitness: float
    mean_fitness: float
    std_fitness: float
    
    # 夏普比率统计
    min_sharpe: float
    max_sharpe: float
    mean_sharpe: float
    
    # 复杂度统计
    min_nodes: int
    max_nodes: int
    mean_nodes: float
    
    # 多样性
    unique_expressions: int
    offspring_generated: int  # 本代实际生成的后代总数
    
    # 时间
    evaluation_time: float
    evolution_time: float
    total_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": self.population_size,
            "valid_count": self.valid_count,
            "min_fitness": self.min_fitness,
            "max_fitness": self.max_fitness,
            "mean_fitness": self.mean_fitness,
            "std_fitness": self.std_fitness,
            "min_sharpe": self.min_sharpe,
            "max_sharpe": self.max_sharpe,
            "mean_sharpe": self.mean_sharpe,
            "min_nodes": self.min_nodes,
            "max_nodes": self.max_nodes,
            "mean_nodes": self.mean_nodes,
            "unique_expressions": self.unique_expressions,
            "evaluation_time": self.evaluation_time,
            "evolution_time": self.evolution_time,
            "total_time": self.total_time,
        }


@dataclass
class EvolutionResult:
    """完整进化结果"""
    final_population: List[GPIndividual]
    best_individuals: List[GPIndividual]
    history: List[GenerationStats]
    total_generations: int
    total_time: float
    best_fitness: float
    best_sharpe: float
    
    def get_best_individual(self) -> Optional[GPIndividual]:
        """获取最佳个体"""
        if not self.best_individuals:
            return None
        return self.best_individuals[0]
    
    def get_unique_best(self, n: int = 10) -> List[GPIndividual]:
        """获取前N个不重复的最佳个体"""
        seen = set()
        unique = []
        for ind in self.best_individuals:
            expr = ind.to_expression()
            if expr not in seen:
                seen.add(expr)
                unique.append(ind)
                if len(unique) >= n:
                    break
        return unique


# ---------------------------------------------------------------------------
# 进化配置
# ---------------------------------------------------------------------------

@dataclass
class EvolutionConfig:
    """进化配置"""
    
    # 种群
    population_size: int = 100
    max_generations: int = 99999999
    
    # 选择
    selection_method: str = "tournament"  # tournament | roulette | rank
    tournament_size: int = 5
    elite_size: int = 5  # 精英保留数量
    
    # 遗传算子概率
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    base_mutation_rate: float = 0.2  # 基础变异率（用于自适应调整）
    
    # 变异类型概率
    subtree_mutation_rate: float = 0.4
    point_mutation_rate: float = 0.3
    hoist_mutation_rate: float = 0.15
    shrink_mutation_rate: float = 0.15
    
    # 深度约束
    max_tree_depth: int = 6
    max_node_count: int = 50
    
    # 初始化
    init_max_depth: int = 3
    
    # 终止条件
    target_fitness: Optional[float] = None  # 达到此适应度则停止
    max_stagnation: int = 0  # 连续N代无改进则停止（0=禁用，持续进化）
    
    # 适应度配置
    fitness_config: FitnessConfig = field(default_factory=FitnessConfig)
    
    # 多样性维护
    diversity_penalty: float = 0.0  # 重复个体惩罚系数
    min_unique_ratio: float = 0.3  # 最小唯一个体比例
    
    # 持续挖掘机制
    enable_adaptive_mutation: bool = True  # 启用自适应变异率
    adaptive_mutation_threshold: int = 30  # 停滞N代后开始增加变异率
    max_mutation_rate: float = 0.6  # 最大变异率
    enable_population_restart: bool = True  # 启用种群重启
    restart_threshold: int = 50  # 停滞N代后触发种群重启
    restart_elite_count: int = 5  # 重启时保留的精英数量


# ---------------------------------------------------------------------------
# 种群管理器
# ---------------------------------------------------------------------------

class PopulationManager:
    """种群管理器"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.population: List[GPIndividual] = []
        self.expression_history: Dict[str, int] = {}  # 表达式出现次数
    
    def initialize(self, seed: Optional[int] = None, seeds: Optional[List] = None) -> None:
        """初始化种群
        
        Parameters
        ----------
        seed : int, optional
            随机种子
        seeds : List[GPIndividual], optional
            种子个体列表，将注入到初始种群中
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.population = []
        self.expression_history = {}
        
        # 计算需要随机生成的个体数量
        seed_count = len(seeds) if seeds else 0
        random_count = self.config.population_size - seed_count
        
        # 注入种子个体
        if seeds:
            for i, individual in enumerate(seeds[:self.config.population_size]):
                individual.generation = 0
                individual.origin = 'seed'
                self.population.append(individual)
                
                expr = individual.to_expression()
                self.expression_history[expr] = self.expression_history.get(expr, 0) + 1
            
            logger.info(f"注入 {len(self.population)} 个种子个体")
        
        # 随机生成剩余个体
        attempts = 0
        max_attempts = random_count * 50  # 增加尝试次数到50倍
        random_generated = 0
        while len(self.population) < self.config.population_size and attempts < max_attempts:
            individual = random_individual(
                max_depth=self.config.init_max_depth,
                generation=0,
            )
            individual.id = f"gen0_{random_generated:04d}"
            individual.origin = 'random'

            # 检查表达式是否已存在
            expr = individual.to_expression()
            if expr not in self.expression_history:
                self.population.append(individual)
                self.expression_history[expr] = self.expression_history.get(expr, 0) + 1
                random_generated += 1
            else:
                # 允许少量重复（最多重复3次），避免无限循环
                count = self.expression_history.get(expr, 0)
                if count < 3:
                    self.population.append(individual)
                    self.expression_history[expr] = count + 1
                    random_generated += 1
            attempts += 1
        
        logger.info(f"种群初始化完成，大小: {len(self.population)} (种子: {seed_count}, 随机: {random_count})")
    
    def evaluate_fitness(
        self,
        data: pd.DataFrame,
        symbol: str = "RB",
        evaluator: Optional[FitnessEvaluator] = None,
    ) -> Tuple[List[FitnessResult], float]:
        """评估种群适应度
        
        Returns
        -------
        (results, evaluation_time)
        """
        start_time = time.time()
        
        if evaluator is None:
            evaluator = FitnessEvaluator(self.config.fitness_config)
        
        results = evaluator.evaluate_batch(self.population, data, symbol)

        # 更新个体适应度并应用多样性惩罚
        for i, result in enumerate(results):
            if result.valid:
                individual = self.population[i]
                individual.fitness["penalized"] = result.penalized_fitness
                individual.fitness["raw"] = result.raw_fitness
                individual.fitness["sharpe"] = result.sharpe
                individual.metrics = {
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "total_trades": result.total_trades,
                    "win_rate": result.win_rate,
                    "avg_trade_return": result.avg_trade_return,
                }

                # 多样性惩罚
                expr = individual.to_expression()
                count = self.expression_history.get(expr, 0)
                if count > 1 and self.config.diversity_penalty > 0:
                    penalty = (count - 1) * self.config.diversity_penalty
                    individual.fitness["penalized"] = max(0, individual.fitness["penalized"] - penalty)
            else:
                # 参数验证失败的个体，标记为无效
                individual = self.population[i]
                individual.fitness["penalized"] = -9999.0
                individual.fitness["raw"] = -9999.0
                individual.fitness["sharpe"] = -9999.0
        
        eval_time = time.time() - start_time
        return results, eval_time
    
    def select_parents(self) -> List[GPIndividual]:
        """选择父代"""
        valid_individuals = [
            ind for ind in self.population
            if ind.fitness.get("penalized", 0) > 0
        ]
        
        if len(valid_individuals) < 2:
            # 方法1 门槛分级：过线父代不足时，不退化成纯随机，而是在「非硬性无效(-9999)」
            # 的个体里按评分保留 top-2 当父代，让薄品种也能朝"最不差"方向继续进化。
            ranked = sorted(
                (ind for ind in self.population if ind.fitness.get("penalized", -9999) > -9000),
                key=lambda x: x.fitness.get("penalized", -9999),
                reverse=True,
            )
            if len(ranked) >= 2:
                logger.warning("有效个体不足，按评分保留top2作为父代（门槛分级）")
                return ranked[:2]
            logger.warning("有效个体不足，返回随机选择")
            return random.sample(self.population, min(2, len(self.population)))
        
        if self.config.selection_method == "tournament":
            # 锦标赛选择：选择两个父代
            parent1 = tournament_selection(
                valid_individuals,
                tournament_size=self.config.tournament_size,
            )
            parent2 = tournament_selection(
                valid_individuals,
                tournament_size=self.config.tournament_size,
            )
            return [parent1, parent2]
        elif self.config.selection_method == "roulette":
            parent1 = roulette_selection(valid_individuals)
            parent2 = roulette_selection(valid_individuals)
            return [parent1, parent2]
        elif self.config.selection_method == "rank":
            parent1 = rank_selection(valid_individuals)
            parent2 = rank_selection(valid_individuals)
            return [parent1, parent2]
        else:
            raise ValueError(f"未知选择方法: {self.config.selection_method}")
    
    def create_next_generation(self, generation: int, stagnation_count: int = 0) -> float:
        """创建下一代种群
        
        Parameters
        ----------
        generation : int
            当前代数
        stagnation_count : int
            停滞代数计数（用于自适应变异率）
        
        Returns
        -------
        evolution_time: float
        """
        start_time = time.time()
        
        # 自适应变异率计算
        current_mutation_rate = self.config.mutation_rate
        if self.config.enable_adaptive_mutation and stagnation_count > self.config.adaptive_mutation_threshold:
            # 停滞超过阈值后，线性增加变异率
            excess = stagnation_count - self.config.adaptive_mutation_threshold
            increase = min(
                self.config.max_mutation_rate - self.config.base_mutation_rate,
                excess * 0.01  # 每停滞一代增加1%变异率
            )
            current_mutation_rate = self.config.base_mutation_rate + increase
            logger.info(f"自适应变异率: 停滞{stagnation_count}代，变异率调整为 {current_mutation_rate:.2%}")
        
        # 种群重启检查
        if self.config.enable_population_restart and stagnation_count >= self.config.restart_threshold:
            logger.warning(f"种群停滞{stagnation_count}代，触发种群重启！")
            return self._restart_population(generation)
        
        # 精英保留
        sorted_pop = sorted(
            self.population,
            key=lambda x: x.fitness.get("penalized", 0),
            reverse=True,
        )
        elites = sorted_pop[:self.config.elite_size]
        for elite in elites:
            elite.origin = "elite"
        
        # 选择父代
        parents = self.select_parents()
        
        # 创建新种群
        new_population: List[GPIndividual] = elites.copy()
        offspring_count = 0
        rejected_count = 0
        
        logger.info(f"开始创建下一代，目标种群大小: {self.config.population_size}, 当前精英数量: {len(elites)}")
        
        while len(new_population) < self.config.population_size:
            # 选择两个父代
            parent1 = random.choice(parents)
            parent2 = random.choice(parents)
            
            # 交叉
            if random.random() < self.config.crossover_rate:
                child1, child2 = crossover(parent1, parent2, self.config.max_tree_depth)
            else:
                child1 = parent1.clone()
                child2 = parent2.clone()
            
            # 变异（使用自适应变异率）
            for child in [child1, child2]:
                if random.random() < current_mutation_rate:
                    child = mutate(
                        child,
                        mutation_rate=1.0,
                        subtree_rate=self.config.subtree_mutation_rate,
                        point_rate=self.config.point_mutation_rate,
                        hoist_rate=self.config.hoist_mutation_rate,
                        shrink_rate=self.config.shrink_mutation_rate,
                    )
                    child.origin = "mutation"
                else:
                    child.origin = "crossover"
                
                # 更新代数和ID
                child.generation = generation
                child.id = f"gen{generation}_{offspring_count:04d}"
                offspring_count += 1
                
                # 检查深度约束和表达式唯一性
                if child.get_node_count() <= self.config.max_node_count:
                    expr = child.to_expression()
                    # 检查表达式是否已存在于新种群或历史中
                    if expr not in self.expression_history:
                        new_population.append(child)
                        self.expression_history[expr] = self.expression_history.get(expr, 0) + 1
                    else:
                        # 允许少量重复（最多重复2次），避免种群大小不足
                        count = self.expression_history.get(expr, 0)
                        if count < 2:
                            new_population.append(child)
                            self.expression_history[expr] = count + 1
                        else:
                            rejected_count += 1
                else:
                    rejected_count += 1
                
                if len(new_population) >= self.config.population_size:
                    break
            
            # 防止无限循环：如果尝试次数过多，强制退出
            if offspring_count > self.config.population_size * 50:
                logger.warning(f"创建下一代时尝试次数过多 ({offspring_count})，强制退出，当前种群大小: {len(new_population)}")
                break
        
        self.population = new_population[:self.config.population_size]
        
        evolution_time = time.time() - start_time
        return evolution_time, offspring_count
    
    def _restart_population(self, generation: int) -> float:
        """种群重启：保留精英，其余随机生成
        
        用于打破局部最优，重新探索搜索空间
        """
        start_time = time.time()
        
        # 保留精英
        sorted_pop = sorted(
            self.population,
            key=lambda x: x.fitness.get("penalized", 0),
            reverse=True,
        )
        elites = sorted_pop[:self.config.restart_elite_count]
        for elite in elites:
            elite.origin = "elite"
        
        # 随机生成新个体
        new_population: List[GPIndividual] = elites.copy()
        random_count = self.config.population_size - len(elites)
        
        for i in range(random_count):
            individual = random_individual(
                max_depth=self.config.init_max_depth,
                generation=generation,
            )
            individual.id = f"gen{generation}_restart_{i:04d}"
            individual.origin = 'restart'

            # 检查表达式唯一性
            expr = individual.to_expression()
            if expr not in self.expression_history:
                new_population.append(individual)
                self.expression_history[expr] = self.expression_history.get(expr, 0) + 1

        self.population = new_population
        
        logger.info(f"种群重启完成：保留 {len(elites)} 个精英，生成 {random_count} 个新个体")
        
        evolution_time = time.time() - start_time
        return evolution_time
    
    def get_sorted_individuals(self, use_penalized: bool = True) -> List[GPIndividual]:
        """获取排序后的个体"""
        key = "penalized" if use_penalized else "raw"
        return sorted(
            self.population,
            key=lambda x: x.fitness.get(key, 0),
            reverse=True,
        )
    
    def compute_stats(
        self,
        generation: int,
        eval_time: float,
        evolution_time: float,
        total_time: float,
        offspring_generated: int = 0,
    ) -> GenerationStats:
        """计算种群统计"""
        valid_individuals = [
            ind for ind in self.population
            if "penalized" in ind.fitness
        ]
        
        if not valid_individuals:
            return GenerationStats(
                generation=generation,
                population_size=len(self.population),
                valid_count=0,
                min_fitness=0,
                max_fitness=0,
                mean_fitness=0,
                std_fitness=0,
                min_sharpe=0,
                max_sharpe=0,
                mean_sharpe=0,
                min_nodes=0,
                max_nodes=0,
                mean_nodes=0,
                unique_expressions=0,
                offspring_generated=offspring_generated,
                evaluation_time=eval_time,
                evolution_time=evolution_time,
                total_time=total_time,
            )
        
        fitness_values = [ind.fitness["penalized"] for ind in valid_individuals]
        sharpe_values = [ind.fitness.get("sharpe", 0) for ind in valid_individuals]
        node_counts = [ind.get_node_count() for ind in self.population]
        expressions = {ind.to_expression() for ind in self.population}
        
        return GenerationStats(
            generation=generation,
            population_size=len(self.population),
            valid_count=len(valid_individuals),
            min_fitness=float(np.min(fitness_values)),
            max_fitness=float(np.max(fitness_values)),
            mean_fitness=float(np.mean(fitness_values)),
            std_fitness=float(np.std(fitness_values)),
            min_sharpe=float(np.min(sharpe_values)),
            max_sharpe=float(np.max(sharpe_values)),
            mean_sharpe=float(np.mean(sharpe_values)),
            min_nodes=int(np.min(node_counts)),
            max_nodes=int(np.max(node_counts)),
            mean_nodes=float(np.mean(node_counts)),
            unique_expressions=len(expressions),
            offspring_generated=offspring_generated,
            evaluation_time=eval_time,
            evolution_time=evolution_time,
            total_time=total_time,
        )


# ---------------------------------------------------------------------------
# 进化算法主循环
# ---------------------------------------------------------------------------

class GeneticProgramming:
    """遗传编程主算法"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.manager = PopulationManager(config)
        self.history: List[GenerationStats] = []
        self.best_individuals: List[GPIndividual] = []
        self.best_fitness_history: List[float] = []
        self.stagnation_count = 0
        self.best_fitness = 0.0
    
    def evolve(
        self,
        data: pd.DataFrame,
        symbol: str = "RB",
        callback: Optional[Callable[[int, GenerationStats], None]] = None,
        seeds: Optional[List] = None,
    ) -> EvolutionResult:
        """执行进化
        
        Parameters
        ----------
        data : pd.DataFrame
            历史数据
        symbol : str
            品种代码
        callback : callable, optional
            每代完成后的回调函数: callback(generation, stats)
        seeds : List[GPIndividual], optional
            种子个体列表，将注入到初始种群中
        
        Returns
        -------
        EvolutionResult
        """
        total_start_time = time.time()
        
        # 初始化种群（注入种子）
        self.manager.initialize(seeds=seeds)
        self.history = []
        self.best_individuals = []
        self.best_fitness_history = []
        self.stagnation_count = 0
        self.best_fitness = 0.0
        
        logger.info(f"========== 开始进化 ==========")
        logger.info(f"品种: {symbol}")
        logger.info(f"种群大小: {self.config.population_size}")
        logger.info(f"最大代数: {self.config.max_generations}")
        logger.info(f"停滞阈值: {self.config.max_stagnation}")
        logger.info(f"最小多样性: {self.config.min_unique_ratio:.0%}")
        if seeds:
            logger.info(f"种子数量: {len(seeds)}")
        
        for generation in range(self.config.max_generations):
            gen_start_time = time.time()
            
            # 评估适应度
            _, eval_time = self.manager.evaluate_fitness(data, symbol)
            
            # 统计
            sorted_individuals = self.manager.get_sorted_individuals()
            current_best_fitness = sorted_individuals[0].fitness.get("penalized", 0) if sorted_individuals else 0
            
            # 更新最佳个体
            self.best_individuals = self.manager.get_sorted_individuals(use_penalized=True)
            self.best_fitness_history.append(current_best_fitness)
            
            # 检查停滞
            if current_best_fitness > self.best_fitness + 1e-6:
                self.best_fitness = current_best_fitness
                self.stagnation_count = 0
                logger.debug(f"第{generation}代: 找到更优个体，适应度: {current_best_fitness:.4f}")
            else:
                self.stagnation_count += 1
                logger.debug(f"第{generation}代: 无改进，停滞计数: {self.stagnation_count}")
            
            # 创建下一代（传入停滞计数用于自适应变异率）
            logger.info(f"第{generation}代: 开始创建下一代")
            evolution_time, offspring_count = self.manager.create_next_generation(generation + 1, self.stagnation_count)
            logger.info(f"第{generation}代: 创建下一代完成，耗时 {evolution_time:.2f}s，生成 {offspring_count} 个后代")
            
            # 计算统计
            gen_total_time = time.time() - gen_start_time
            logger.info(f"第{generation}代: 开始计算统计")
            stats = self.manager.compute_stats(
                generation=generation,
                eval_time=eval_time,
                evolution_time=evolution_time,
                total_time=gen_total_time,
                offspring_generated=offspring_count,
            )
            logger.info(f"第{generation}代: 计算统计完成")
            self.history.append(stats)
            
            # 日志
            logger.info(
                f"第{generation}代完成 | "
                f"最佳适应度: {stats.max_fitness:.4f} | "
                f"最佳夏普: {stats.max_sharpe:.4f} | "
                f"有效个体: {stats.valid_count}/{stats.population_size} | "
                f"唯一表达式: {stats.unique_expressions} | "
                f"时间: {stats.total_time:.2f}s"
            )
            
            # 回调
            logger.info(f"准备调用回调函数，callback is not None: {callback is not None}")
            if callback is not None:
                logger.info(f"调用回调函数 callback({generation}, stats)")
                callback(generation, stats)
                logger.info(f"回调函数调用完成")
            
            # 检查终止条件
            if self._check_termination(generation):
                logger.info(f"达到终止条件，进化提前结束")
                break
        
        total_time = time.time() - total_start_time
        
        # 最终评估
        self.manager.evaluate_fitness(data, symbol)
        self.best_individuals = self.manager.get_sorted_individuals(use_penalized=True)
        
        best_sharpe = max(
            ind.fitness.get("sharpe", 0)
            for ind in self.best_individuals
        ) if self.best_individuals else 0
        
        logger.info(f"========== 进化完成 ==========")
        logger.info(f"总代数: {len(self.history)}")
        logger.info(f"总耗时: {total_time:.2f}秒")
        logger.info(f"最佳适应度: {self.best_fitness:.4f}")
        logger.info(f"最佳夏普: {best_sharpe:.4f}")
        
        return EvolutionResult(
            final_population=self.manager.population,
            best_individuals=self.best_individuals,
            history=self.history,
            total_generations=len(self.history),
            total_time=total_time,
            best_fitness=self.best_fitness,
            best_sharpe=best_sharpe,
        )
    
    def _check_termination(self, generation: int) -> bool:
        """检查终止条件"""
        result = False

        # 目标适应度
        if self.config.target_fitness is not None:
            if self.best_fitness >= self.config.target_fitness:
                logger.info(f"达到目标适应度: {self.best_fitness:.4f} >= {self.config.target_fitness:.4f}")
                result = True

        # 停滞检查
        if self.config.max_stagnation > 0:
            if self.stagnation_count >= self.config.max_stagnation:
                logger.info(f"连续{self.stagnation_count}代无改进，终止进化")
                result = True

        # 多样性检查（只警告，不终止）
        if len(self.history) > 0:
            latest = self.history[-1]
            unique_ratio = latest.unique_expressions / latest.population_size
            if unique_ratio < self.config.min_unique_ratio:
                logger.warning(f"种群多样性过低: {unique_ratio:.2%}")

        # 强制终止检查（防止无限循环）
        if generation >= self.config.max_generations - 1:
            logger.info(f"达到最大代数 {self.config.max_generations}，终止进化")
            result = True

        if result:
            logger.info(f"终止条件检查: generation={generation}, stagnation={self.stagnation_count}, best_fitness={self.best_fitness:.4f}")

        return result
    
    def get_evolution_history(self) -> pd.DataFrame:
        """获取进化历史"""
        return pd.DataFrame([stat.to_dict() for stat in self.history])
