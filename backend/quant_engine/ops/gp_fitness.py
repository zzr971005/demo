"""
GP适应度评估器

将GP个体通过回测引擎评估适应度
支持：
- 因子表达式编译和执行
- 回测性能指标计算
- 复杂度惩罚（防止过拟合）
- 多目标适应度评估
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from quant_engine.factors.registry import FACTOR_REGISTRY
from quant_engine.validation.engine import BacktestResult, VectorizedBacktestEngine
from quant_engine.validation.fee_model import FeeModel

from .gp_individual import GPIndividual

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 适应度评估配置
# ---------------------------------------------------------------------------

@dataclass
class FitnessConfig:
    """适应度评估配置"""
    
    # 回测参数
    init_capital: float = 1_000_000.0
    risk_free_rate: float = 0.03
    periods_per_year: float = 252 * 5  # 1H数据
    
    # 交易参数
    upper_threshold: float = 0.5
    lower_threshold: float = -0.5
    direction_mode: int = 0  # 0=双向, 1=只多, -1=只空
    max_holding_bars: int = 0  # 0=不限
    position_size_pct: float = 0.95
    contract_value_per_lot: float = 50000.0
    contract_multiplier: float = 10.0  # 每手吨数（螺纹钢=10吨/手）
    tick_size: float = 1.0
    slippage_ticks: float = 1
    use_margin: bool = True
    margin_rate: float = 0.12
    
    # 复杂度惩罚参数
    complexity_penalty_enabled: bool = True
    complexity_penalty_coef: float = 0.01  # 每节点惩罚系数
    max_complexity: int = 50  # 最大允许节点数
    
    # 适应度权重
    sharpe_weight: float = 1.0
    calmar_weight: float = 0.5
    return_weight: float = 0.3
    
    # 最小交易次数要求
    min_trades: int = 10
    min_trades_penalty: float = -1.0  # 不满足时的惩罚值
    
    # 最大回撤限制
    max_drawdown_limit: float = 0.20
    max_drawdown_penalty_coef: float = 2.0
    
    # 因子有效性控制
    max_nan_ratio: float = 0.8  # 允许的最大NaN占比


# ---------------------------------------------------------------------------
# 因子编译器
# ---------------------------------------------------------------------------

class FactorCompiler:
    """将GP个体编译为可执行的因子函数"""
    
    def __init__(self, data_columns: List[str]):
        """
        Parameters
        ----------
        data_columns : List[str]
            可用数据列名，如 ['open', 'high', 'low', 'close', 'volume']
        """
        self.data_columns = data_columns
        self._cache: Dict[str, Callable] = {}
    
    def compile(self, individual: GPIndividual) -> Optional[Callable[[pd.DataFrame], np.ndarray]]:
        """
        编译GP个体为因子计算函数
        
        Returns
        -------
        Callable[[pd.DataFrame], np.ndarray] 或 None（编译失败）
        """
        try:
            # 禁用缓存，为每个个体独立编译
            # 避免不同个体共享同一个函数引用（可能导致并发问题）
            return self._build_function(individual)
            
        except Exception as e:
            logger.warning(f"编译个体 {individual.id} 失败: {e}")
            return None
    
    def _build_function(self, individual: GPIndividual) -> Callable[[pd.DataFrame], np.ndarray]:
        """构建因子计算函数"""
        
        def compute_factor(df: pd.DataFrame) -> np.ndarray:
            """计算因子值"""
            return self._evaluate_node(individual.root, df)
        
        return compute_factor
    
    def _evaluate_node(self, node, df: pd.DataFrame) -> np.ndarray:
        """递归评估节点"""
        if node.node_type == 'var':
            # 变量节点
            col_map = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'open_interest': 'open_interest',
            }
            col = col_map.get(node.name, node.name)
            if col in df.columns:
                return df[col].values
            else:
                # 返回NaN数组
                return np.full(len(df), np.nan)
        
        elif node.node_type == 'const':
            # 常量节点
            value = float(node.value) if node.value is not None else 0.0
            return np.full(len(df), value, dtype=np.float64)
        
        elif node.node_type == 'binop':
            # 二元操作节点
            if len(node.children) != 2:
                return np.full(len(df), np.nan)
            
            left = self._evaluate_node(node.children[0], df)
            right = self._evaluate_node(node.children[1], df)
            
            # 处理NaN
            if np.all(np.isnan(left)) or np.all(np.isnan(right)):
                return np.full(len(df), np.nan)
            
            op = node.name
            if op == '+':
                return np.add(left, right)
            elif op == '-':
                return np.subtract(left, right)
            elif op == '*':
                return np.multiply(left, right)
            elif op == '/':
                # 避免除零，确保结果为浮点数
                left_f = left.astype(np.float64) if left.dtype != np.float64 else left
                right_f = right.astype(np.float64) if right.dtype != np.float64 else right
                return np.divide(left_f, right_f, out=np.full_like(left_f, np.nan), where=right_f != 0)
            elif op == '>':
                return (left > right).astype(float)
            elif op == '<':
                return (left < right).astype(float)
            elif op == '>=':
                return (left >= right).astype(float)
            elif op == '<=':
                return (left <= right).astype(float)
            elif op == '==':
                return (left == right).astype(float)
            elif op == '!=':
                return (left != right).astype(float)
            elif op == 'and':
                return np.logical_and(left > 0, right > 0).astype(float)
            elif op == 'or':
                return np.logical_or(left > 0, right > 0).astype(float)
            else:
                return np.full(len(df), np.nan)
        
        elif node.node_type == 'func':
            # 函数节点
            func_meta = FACTOR_REGISTRY.get(node.name)
            if func_meta is None or func_meta.func is None:
                return np.full(len(df), np.nan)
            
            # 评估子节点
            args = []
            for i, child in enumerate(node.children):
                arg_val = self._evaluate_node(child, df)
                
                # 根据参数定义决定是否需要转换为标量
                if i < len(func_meta.params):
                    param_name, param_type, param_default = func_meta.params[i]
                    if param_type == int and isinstance(arg_val, np.ndarray):
                        # 将数组转换为整数标量
                        if len(arg_val) > 0 and not np.isnan(arg_val[0]):
                            arg_val = int(arg_val[0])
                        else:
                            # 使用默认值
                            arg_val = param_default
                    elif param_type == float and isinstance(arg_val, np.ndarray):
                        # 将数组转换为浮点数标量
                        if len(arg_val) > 0 and not np.isnan(arg_val[0]):
                            arg_val = float(arg_val[0])
                        else:
                            # 使用默认值
                            arg_val = param_default
                
                args.append(arg_val)
            
            if not args:
                return np.full(len(df), np.nan)
            
            try:
                result = func_meta.func(*args)
                return result
            except Exception as e:
                logger.debug(f"函数 {node.name} 执行失败: {e}")
                return np.full(len(df), np.nan)
        
        else:
            return np.full(len(df), np.nan)


# ---------------------------------------------------------------------------
# 适应度评估器
# ---------------------------------------------------------------------------

@dataclass
class FitnessResult:
    """适应度评估结果"""
    
    individual_id: str
    expression: str
    
    # 原始回测指标
    sharpe: float = 0.0
    calmar: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_trade_return: float = 0.0
    turnover_rate: float = 0.0
    
    # 复杂度指标
    node_count: int = 0
    tree_depth: int = 0
    
    # 适应度值
    raw_fitness: float = 0.0
    penalized_fitness: float = 0.0
    
    # 评估状态
    valid: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "individual_id": self.individual_id,
            "expression": self.expression,
            "sharpe": self.sharpe,
            "calmar": self.calmar,
            "max_drawdown": self.max_drawdown,
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "avg_trade_pnl": self.avg_trade_pnl,
            "avg_trade_return": self.avg_trade_return,
            "turnover_rate": self.turnover_rate,
            "node_count": self.node_count,
            "tree_depth": self.tree_depth,
            "raw_fitness": self.raw_fitness,
            "penalized_fitness": self.penalized_fitness,
            "valid": self.valid,
        }


class FitnessEvaluator:
    """GP适应度评估器"""
    
    def __init__(
        self,
        config: Optional[FitnessConfig] = None,
        fee_model: Optional[FeeModel] = None,
    ):
        """
        Parameters
        ----------
        config : FitnessConfig
            适应度评估配置
        fee_model : FeeModel
            手续费模型
        """
        self.config = config or FitnessConfig()
        self.fee_model = fee_model or FeeModel()
        
        # 初始化回测引擎
        self.backtest_engine = VectorizedBacktestEngine(
            fee_model=self.fee_model,
            init_capital=self.config.init_capital,
            risk_free_rate=self.config.risk_free_rate,
            periods_per_year=self.config.periods_per_year,
        )
        
        # 初始化因子编译器（包含所有可能的数据列）
        self.compiler = FactorCompiler(
            data_columns=[
                'open', 'high', 'low', 'close', 'volume', 'open_interest',
                'near_close', 'far_close', 'days_to_expiry',  # 期限结构列
            ]
        )
        # 清除缓存
        self.compiler._cache.clear()

        # 因子值缓存，用于相关性惩罚
        self.factor_cache = {}  # {expression: normalized_factor_values}
        self.correlation_threshold = 0.85  # 相关性惩罚阈值
        self.correlation_penalty_coef = 0.5  # 惩罚系数
    
    def evaluate(
        self,
        individual: GPIndividual,
        data: pd.DataFrame,
        symbol: str = "RB",
    ) -> FitnessResult:
        """
        评估单个GP个体的适应度
        
        Parameters
        ----------
        individual : GPIndividual
            GP个体
        data : pd.DataFrame
            OHLCV数据
        symbol : str
            品种代码
            
        Returns
        -------
        FitnessResult
        """
        expression = individual.to_expression()
        
        # 编译因子
        factor_func = self.compiler.compile(individual)
        if factor_func is None:
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message="编译失败",
            )
        # 调试：输出表达式
        logger.debug(f"个体 {individual.id} 表达式: {expression}")
        
        # 验证参数类型
        if not self._validate_parameter_types(individual):
            logger.debug(f"个体 {individual.id} 参数类型验证失败")
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message="参数类型错误",
            )

        # 计算因子值
        try:
            # 调试：输出数据列信息
            logger.debug(f"个体 {individual.id} 数据列: {list(data.columns)}")
            logger.debug(f"个体 {individual.id} 数据形状: {data.shape}")
            for col in ['high', 'low', 'close', 'volume']:
                if col in data.columns:
                    logger.debug(f"个体 {individual.id} {col} 统计: min={data[col].min():.4f}, max={data[col].max():.4f}, mean={data[col].mean():.4f}, NaN数量={data[col].isna().sum()}")

            factor_values = factor_func(data)
            
            # 检查因子值是否为None
            if factor_values is None:
                logger.warning(f"个体 {individual.id} 因子计算返回None")
                return FitnessResult(
                    individual_id=individual.id,
                    expression=expression,
                    valid=False,
                    error_message="因子计算返回None",
                )

            factor_values = np.asarray(factor_values, dtype=np.float64)
            if factor_values.size == 0:
                logger.warning(f"个体 {individual.id} 因子值为空")
                return FitnessResult(
                    individual_id=individual.id,
                    expression=expression,
                    valid=False,
                    error_message="因子值为空",
                )
            
            finite_values = factor_values[np.isfinite(factor_values)]
            if finite_values.size > 0:
                logger.debug(
                    f"个体 {individual.id} 因子值统计: min={finite_values.min():.4f}, max={finite_values.max():.4f}, "
                    f"mean={finite_values.mean():.4f}, std={finite_values.std():.4f}"
                )

                # 检测常数输出：标准差过小
                std_val = finite_values.std()
                # 使用相对标准差（变异系数）来检测常数输出
                mean_val = np.abs(finite_values.mean())
                if mean_val > 0:
                    cv = std_val / mean_val
                    if cv < 1e-6:
                        logger.debug(f"个体 {individual.id} 因子值变异系数过小 ({cv:.2e})，可能是常数输出，拒绝")
                        return FitnessResult(
                            individual_id=individual.id,
                            expression=expression,
                            valid=False,
                            error_message=f"因子值变异系数过小: {cv:.2e}",
                        )
                else:
                    # 均值为0时，使用绝对标准差
                    if std_val < 1e-8:
                        logger.debug(f"个体 {individual.id} 因子值标准差过小 ({std_val:.2e})，可能是常数输出，拒绝")
                        return FitnessResult(
                            individual_id=individual.id,
                            expression=expression,
                            valid=False,
                            error_message=f"因子值标准差过小: {std_val:.2e}",
                        )
            else:
                logger.debug(f"个体 {individual.id} 因子值统计: 无有限值 (size={factor_values.size})")
            # 检查因子值是否是同一个数组引用
            logger.debug(f"个体 {individual.id} 因子值数组ID: {id(factor_values)}")
        except Exception as e:
            import traceback
            logger.warning(f"个体 {individual.id} 因子计算失败: {e}\n{traceback.format_exc()}")
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message=f"因子计算失败: {e}",
            )
        
        # 尝试对滚动窗口预热期NaN进行LOCF填充
        # 检测连续NaN前缀（预热期）
        nan_mask = np.isnan(factor_values)
        if nan_mask.any():
            # 找到第一个非NaN的位置
            first_valid_idx = np.where(~nan_mask)[0]
            if len(first_valid_idx) == 0:
                # 全NaN，直接拒绝
                logger.debug(f"个体 {individual.id} 因子值全为NaN，拒绝")
                return FitnessResult(
                    individual_id=individual.id,
                    expression=expression,
                    valid=False,
                    error_message="因子值全为NaN",
                )
            warmup_end = first_valid_idx[0]
            # 限制LOCF填充最大长度为30（对应最大滚动窗口）
            max_fill_length = 30
            if warmup_end > 0 and warmup_end <= max_fill_length:
                # 前warmup_end个点可能是预热期NaN，用第一个有效值填充
                first_valid_value = factor_values[warmup_end]
                factor_values[:warmup_end] = first_valid_value
                logger.debug(f"个体 {individual.id} 预热期NaN填充: 前{warmup_end}个点用{first_valid_value:.4f}填充")
            elif warmup_end > max_fill_length:
                # 预热期过长，可能是计算错误或数据问题，拒绝
                logger.debug(f"个体 {individual.id} 预热期NaN过长: {warmup_end}个点 (最大允许{max_fill_length})")
                return FitnessResult(
                    individual_id=individual.id,
                    expression=expression,
                    valid=False,
                    error_message=f"预热期NaN过长 ({warmup_end} > {max_fill_length})",
                )
        
        # 重新计算NaN比例
        nan_ratio = float(np.isnan(factor_values).mean())
        if nan_ratio >= self.config.max_nan_ratio:
            logger.debug(
                f"个体 {individual.id} 因子NaN占比过高: {nan_ratio:.2%} (阈值 {self.config.max_nan_ratio:.2%})"
            )
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message="因子NaN占比过高",
            )
        if not np.isfinite(factor_values).any():
            logger.debug(f"个体 {individual.id} 因子无有限值")
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message="因子无有效值",
            )
        
        # 检查因子有效性
        if np.all(np.isnan(factor_values)):
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message="因子值全为NaN",
            )
        
        # 使用分位数归一化替代z-score标准化
        factor_values = self._normalize_factor_quantile(factor_values)
        # 调试：输出标准化后的因子值统计
        logger.debug(f"个体 {individual.id} 标准化后因子值: min={factor_values.min():.4f}, max={factor_values.max():.4f}, mean={factor_values.mean():.4f}, std={factor_values.std():.4f}")

        # 相关性惩罚：计算与已缓存因子的相关性
        correlation_penalty = 0.0
        if self.factor_cache:
            valid_mask = np.isfinite(factor_values)
            if valid_mask.sum() > 10:  # 至少有10个有效值才计算相关性
                max_corr = 0.0
                for cached_expr, cached_values in self.factor_cache.items():
                    cached_valid_mask = np.isfinite(cached_values)
                    
                    # 处理数据长度不一致的情况
                    min_len = min(len(valid_mask), len(cached_valid_mask))
                    if min_len == 0:
                        continue
                    
                    # 截取到相同长度
                    valid_mask_truncated = valid_mask[:min_len]
                    cached_valid_mask_truncated = cached_valid_mask[:min_len]
                    factor_values_truncated = factor_values[:min_len]
                    cached_values_truncated = cached_values[:min_len]
                    
                    common_valid = valid_mask_truncated & cached_valid_mask_truncated
                    if common_valid.sum() > 10:
                        corr = np.corrcoef(factor_values_truncated[common_valid], cached_values_truncated[common_valid])[0, 1]
                        if not np.isnan(corr):
                            max_corr = max(max_corr, abs(corr))

                if max_corr > self.correlation_threshold:
                    correlation_penalty = self.correlation_penalty_coef * (max_corr - self.correlation_threshold) ** 2
                    logger.debug(f"个体 {individual.id} 相关性惩罚: max_corr={max_corr:.4f}, penalty={correlation_penalty:.4f}")

        # 缓存归一化后的因子值（在相关性惩罚之后，避免自我比较）
        self.factor_cache[expression] = factor_values.copy()

        # 动态交易信号阈值：使用分位数替代固定阈值
        valid_factor = factor_values[np.isfinite(factor_values)]
        if len(valid_factor) > 10:
            dynamic_upper = np.percentile(valid_factor, 75)
            dynamic_lower = np.percentile(valid_factor, 25)
        else:
            # 如果有效值不足，使用默认阈值
            dynamic_upper = self.config.upper_threshold
            dynamic_lower = self.config.lower_threshold

        logger.debug(f"个体 {individual.id} 动态阈值: upper={dynamic_upper:.4f}, lower={dynamic_lower:.4f}")

        # 执行回测
        try:
            backtest_params = {
                "upper_threshold": dynamic_upper,
                "lower_threshold": dynamic_lower,
                "direction_mode": self.config.direction_mode,
                "max_holding_bars": self.config.max_holding_bars,
                "position_size_pct": self.config.position_size_pct,
                "contract_value_per_lot": self.config.contract_value_per_lot,
                "contract_multiplier": self.config.contract_multiplier,
                "tick_size": self.config.tick_size,
                "slippage_ticks": self.config.slippage_ticks,
                "use_margin": self.config.use_margin,
                "margin_rate": self.config.margin_rate,
            }
            
            result = self.backtest_engine.run(
                factor=factor_values,
                open_px=data['open'].values,
                high_px=data['high'].values,
                low_px=data['low'].values,
                close_px=data['close'].values,
                params=backtest_params,
                symbol=symbol,
            )
            # 调试：输出回测结果
            logger.debug(f"个体 {individual.id} 回测结果: sharpe={result.sharpe:.4f}, total_return={result.total_return:.4f}, total_trades={result.total_trades}")
            
        except Exception as e:
            logger.warning(f"个体 {individual.id} 回测失败: {e}")
            return FitnessResult(
                individual_id=individual.id,
                expression=expression,
                valid=False,
                error_message=f"回测失败: {e}",
            )
        
        # 计算适应度
        raw_fitness, penalized_fitness = self._calculate_fitness(
            result, individual
        )

        # 应用相关性惩罚
        penalized_fitness -= correlation_penalty
        
        # 更新个体适应度
        individual.raw_sharpe = result.sharpe
        individual.penalized_sharpe = penalized_fitness
        individual.fitness = {
            "raw": raw_fitness,
            "penalized": penalized_fitness,
            "sharpe": result.sharpe,
            "calmar": result.calmar,
        }
        individual.metrics = {
            "max_drawdown": result.max_drawdown,
            "total_return": result.total_return,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "avg_trade_return": result.avg_trade_return,
        }
        
        return FitnessResult(
            individual_id=individual.id,
            expression=expression,
            sharpe=result.sharpe,
            calmar=result.calmar,
            max_drawdown=result.max_drawdown,
            total_return=result.total_return,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            avg_trade_pnl=result.avg_trade_pnl,
            avg_trade_return=result.avg_trade_return,
            turnover_rate=result.turnover_rate,
            node_count=individual.get_node_count(),
            tree_depth=individual.get_depth(),
            raw_fitness=raw_fitness,
            penalized_fitness=penalized_fitness,
            valid=True,
        )
    
    def evaluate_batch(
        self,
        individuals: List[GPIndividual],
        data: pd.DataFrame,
        symbol: str = "RB",
    ) -> List[FitnessResult]:
        """
        批量评估多个个体
        
        Parameters
        ----------
        individuals : List[GPIndividual]
            GP个体列表
        data : pd.DataFrame
            OHLCV数据
        symbol : str
            品种代码
            
        Returns
        -------
        List[FitnessResult]
        """
        results = []
        for individual in individuals:
            result = self.evaluate(individual, data, symbol)
            results.append(result)
        return results
    
    def _validate_parameter_types(self, individual: GPIndividual) -> bool:
        """
        验证个体的参数类型是否正确

        检查函数节点的子节点类型是否与函数定义匹配
        """
        from quant_engine.factors.registry import FACTOR_REGISTRY

        def validate_node(node: GPNode) -> bool:
            if node.node_type == 'func':
                func_meta = FACTOR_REGISTRY.get(node.name)
                if func_meta is None:
                    return False  # 未知函数

                for i, child in enumerate(node.children):
                    if i >= len(func_meta.params):
                        return False  # 参数数量不匹配

                    param_name, param_type, param_default = func_meta.params[i]

                    if param_type == str:
                        # 字符串类型参数需要变量节点
                        if child.node_type != 'var':
                            return False
                    elif param_type in (int, float):
                        # 数值类型参数需要常量节点
                        if child.node_type != 'const':
                            return False

                        # 验证参数值范围
                        if child.node_type == 'const' and child.value is not None:
                            # 整数类型参数（window, fast, slow等）必须为正数
                            if param_type == int:
                                if not isinstance(child.value, (int, float)):
                                    return False
                                # 必须为正数（严格大于0）
                                if child.value <= 0:
                                    return False
                                # 限制最大值为100
                                if child.value > 100:
                                    return False
                            elif param_type == float:
                                # 浮点参数也必须为正数
                                if child.value <= 0:
                                    return False

                    # 递归验证子节点
                    if not validate_node(child):
                        return False

            return True

        return validate_node(individual.root)

    def _normalize_factor(self, factor: np.ndarray) -> np.ndarray:
        """标准化因子值（z-score）"""
        # 去除NaN和Inf
        clean = factor[np.isfinite(factor)]
        if len(clean) == 0:
            return factor

        mean = np.mean(clean)
        std = np.std(clean)

        if std > 0:
            normalized = (factor - mean) / std
        else:
            normalized = factor - mean

        return normalized

    def _normalize_factor_quantile(self, factor: np.ndarray) -> np.ndarray:
        """使用分位数归一化标准化因子值"""
        # 去除NaN和Inf
        clean = factor[np.isfinite(factor)]
        if len(clean) == 0:
            return factor

        # 使用分位数归一化：将因子值映射到[-1, 1]范围
        # 使用中位数和IQR（四分位距）替代均值和标准差，对异常值更鲁棒
        median = np.median(clean)
        q25 = np.percentile(clean, 25)
        q75 = np.percentile(clean, 75)
        iqr = q75 - q25

        if iqr > 0:
            normalized = (factor - median) / iqr
        else:
            # 如果IQR为0，使用简单的缩放
            min_val = np.min(clean)
            max_val = np.max(clean)
            if max_val > min_val:
                normalized = 2 * (factor - min_val) / (max_val - min_val) - 1
            else:
                normalized = factor - median

        return normalized
    
    def _calculate_fitness(
        self,
        backtest_result: BacktestResult,
        individual: GPIndividual,
    ) -> Tuple[float, float]:
        """
        计算适应度值
        
        Returns
        -------
        (raw_fitness, penalized_fitness)
        """
        # 基础适应度 = 加权综合指标
        # 封顶 total_return：正常累计收益率不可能超过 10000%，封顶防止溢出个体统治种群
        capped_return = max(0, min(backtest_result.total_return, 100.0))
        raw_fitness = (
            self.config.sharpe_weight * max(0, backtest_result.sharpe) +
            self.config.calmar_weight * max(0, backtest_result.calmar) +
            self.config.return_weight * capped_return
        )
        
        # 检查最小交易次数
        if backtest_result.total_trades < self.config.min_trades:
            raw_fitness = self.config.min_trades_penalty
        
        # 检查最大回撤
        if backtest_result.max_drawdown > self.config.max_drawdown_limit:
            excess_dd = backtest_result.max_drawdown - self.config.max_drawdown_limit
            penalty = excess_dd * self.config.max_drawdown_penalty_coef
            raw_fitness -= penalty
        
        # 复杂度惩罚
        penalized_fitness = raw_fitness
        if self.config.complexity_penalty_enabled:
            node_count = individual.get_node_count()
            
            if node_count > self.config.max_complexity:
                # 超过最大复杂度，大幅惩罚
                excess = node_count - self.config.max_complexity
                penalized_fitness = raw_fitness * (0.5 ** (excess / 10))
            else:
                # 正常复杂度惩罚
                penalty = node_count * self.config.complexity_penalty_coef
                penalized_fitness = raw_fitness - penalty
        
        return raw_fitness, penalized_fitness


# ---------------------------------------------------------------------------
# 多品种适应度评估
# ---------------------------------------------------------------------------

class MultiSymbolFitnessEvaluator:
    """多品种适应度评估器"""
    
    def __init__(
        self,
        config: Optional[FitnessConfig] = None,
        fee_model: Optional[FeeModel] = None,
    ):
        self.config = config or FitnessConfig()
        self.fee_model = fee_model or FeeModel()
        self.evaluator = FitnessEvaluator(config, fee_model)
    
    def evaluate(
        self,
        individual: GPIndividual,
        data_dict: Dict[str, pd.DataFrame],
    ) -> Dict[str, FitnessResult]:
        """
        在多个品种上评估个体
        
        Parameters
        ----------
        individual : GPIndividual
            GP个体
        data_dict : Dict[str, pd.DataFrame]
            各品种数据 {symbol: df}
            
        Returns
        -------
        Dict[str, FitnessResult]
        """
        results = {}
        for symbol, data in data_dict.items():
            result = self.evaluator.evaluate(individual, data, symbol)
            results[symbol] = result
        return results
    
    def evaluate_aggregate(
        self,
        individual: GPIndividual,
        data_dict: Dict[str, pd.DataFrame],
        aggregation: str = "mean",
    ) -> Tuple[FitnessResult, Dict[str, FitnessResult]]:
        """
        多品种评估并聚合结果
        
        Parameters
        ----------
        individual : GPIndividual
            GP个体
        data_dict : Dict[str, pd.DataFrame]
            各品种数据
        aggregation : str
            聚合方式: "mean", "min", "median"
            
        Returns
        -------
        (aggregated_result, all_results)
        """
        results = self.evaluate(individual, data_dict)
        
        # 聚合适应度
        valid_results = [r for r in results.values() if r.valid]
        if not valid_results:
            return FitnessResult(
                individual_id=individual.id,
                expression=individual.to_expression(),
                valid=False,
                error_message="所有品种评估失败",
            ), results
        
        sharpe_values = [r.sharpe for r in valid_results]
        calmar_values = [r.calmar for r in valid_results]
        return_values = [r.total_return for r in valid_results]
        
        if aggregation == "mean":
            agg_sharpe = np.mean(sharpe_values)
            agg_calmar = np.mean(calmar_values)
            agg_return = np.mean(return_values)
        elif aggregation == "min":
            agg_sharpe = np.min(sharpe_values)
            agg_calmar = np.min(calmar_values)
            agg_return = np.min(return_values)
        elif aggregation == "median":
            agg_sharpe = np.median(sharpe_values)
            agg_calmar = np.median(calmar_values)
            agg_return = np.median(return_values)
        else:
            agg_sharpe = np.mean(sharpe_values)
            agg_calmar = np.mean(calmar_values)
            agg_return = np.mean(return_values)
        
        # 计算聚合适应度
        agg_fitness = (
            self.config.sharpe_weight * max(0, agg_sharpe) +
            self.config.calmar_weight * max(0, agg_calmar) +
            self.config.return_weight * max(0, agg_return)
        )
        
        # 复杂度惩罚
        node_count = individual.get_node_count()
        if self.config.complexity_penalty_enabled:
            if node_count > self.config.max_complexity:
                excess = node_count - self.config.max_complexity
                penalized = agg_fitness * (0.5 ** (excess / 10))
            else:
                penalty = node_count * self.config.complexity_penalty_coef
                penalized = agg_fitness - penalty
        else:
            penalized = agg_fitness
        
        aggregated = FitnessResult(
            individual_id=individual.id,
            expression=individual.to_expression(),
            sharpe=agg_sharpe,
            calmar=agg_calmar,
            total_return=agg_return,
            node_count=node_count,
            tree_depth=individual.get_depth(),
            raw_fitness=agg_fitness,
            penalized_fitness=penalized,
            valid=True,
        )
        
        return aggregated, results
