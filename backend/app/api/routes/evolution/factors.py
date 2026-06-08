"""
因子库管理API

提供因子原语的查询、验证、测试功能
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from quant_engine.factors.registry import (
    FACTOR_REGISTRY,
    PrimitiveFamily,
    list_primitives,
)
from quant_engine.factors.formula_dsl import (
    compile_expr,
    evaluate_expr,
    parse_expr,
    serialize,
)
from quant_engine.factors.semantic_validator import validate_expression

router = APIRouter(tags=["factors"])


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class PrimitiveParam(BaseModel):
    name: str
    type: str
    default: Any
    description: Optional[str] = None


class PrimitiveInfo(BaseModel):
    name: str
    family: str
    family_code: str
    description: str
    params: List[PrimitiveParam]
    supports: List[str]  # 1H, 1D, etc.


class FactorLibraryResponse(BaseModel):
    total: int
    families: Dict[str, int]
    primitives: List[PrimitiveInfo]


class FactorDetailResponse(BaseModel):
    primitive: PrimitiveInfo
    example: str
    related_primitives: List[str]


class FactorValidateRequest(BaseModel):
    expression: str = Field(..., description="因子表达式，如: ts_mean(close, 20)")
    symbol: Optional[str] = Field(default=None, description="品种代码，用于品种特定约束检查")


class FactorValidateResponse(BaseModel):
    is_valid: bool
    penalty_factor: float
    violations: List[Dict[str, Any]]
    ast: Optional[Dict[str, Any]] = None
    expression: str


class FactorTestRequest(BaseModel):
    expression: str = Field(..., description="因子表达式")
    data: Dict[str, List[float]] = Field(..., description="测试数据，包含open/high/low/close/volume等")


class FactorTestResponse(BaseModel):
    success: bool
    result: Optional[List[float]] = None
    error: Optional[str] = None
    execution_time_ms: float


# ---------------------------------------------------------------------------
# API端点
# ---------------------------------------------------------------------------

@router.get(
    "/factors",
    response_model=FactorLibraryResponse,
    summary="获取因子库列表",
    description="获取所有可用的因子原语，可按族筛选",
)
async def get_factor_library(
    family: Optional[str] = None,
) -> FactorLibraryResponse:
    """
    获取因子库列表
    
    - **family**: 可选，按族筛选 (F1动量族/F2均值回归族/F3波动率族/F4价量族/F5期限结构族/F6持仓量族/F7微观结构族/F8宏观映射族)
    """
    primitives = []
    families_count: Dict[str, int] = {}
    
    for name, meta in FACTOR_REGISTRY.items():
        # 统计各族数量
        family_name = meta.family.value
        families_count[family_name] = families_count.get(family_name, 0) + 1
        
        # 如果指定了族，进行筛选
        if family and family not in meta.family.value:
            continue
        
        # 构建参数列表
        params = []
        for param_name, param_type, param_default in meta.params:
            params.append(PrimitiveParam(
                name=param_name,
                type=param_type.__name__,
                default=param_default,
            ))
        
        primitives.append(PrimitiveInfo(
            name=name,
            family=meta.family.value,
            family_code=meta.family.name,
            description=meta.description,
            params=params,
            supports=meta.supports,
        ))
    
    return FactorLibraryResponse(
        total=len(primitives),
        families=families_count,
        primitives=primitives,
    )


@router.get(
    "/factors/ic-filtered",
    summary="获取IC筛选的因子",
    description="获取通过IC筛选的前50个因子",
)
async def get_ic_filtered_factors(
    symbol: Optional[str] = None,
    generation: Optional[int] = None,
) -> Dict[str, Any]:
    """
    获取通过IC筛选的前50个因子

    Args:
        symbol: 品种代码（可选）
        generation: 代数（可选）

    Returns:
        IC筛选的因子列表
    """
    from app.db import get_session
    from app.models import Candidate, CandidateStatus
    from sqlalchemy import select, desc

    with get_session() as session:
        query = select(Candidate).where(
            Candidate.status == CandidateStatus.VALIDATED,
            Candidate.ic_mean_24h.isnot(None)
        )

        if symbol:
            query = query.where(Candidate.symbol == symbol)
        if generation:
            query = query.where(Candidate.generation == generation)

        # 按IC综合评分排序（这里使用ic_mean_24h作为简单排序依据）
        query = query.order_by(desc(Candidate.ic_mean_24h)).limit(50)

        result = session.execute(query)
        candidates = result.scalars().all()

        factors = []
        for candidate in candidates:
            factors.append({
                "id": candidate.id,
                "symbol": candidate.symbol,
                "expression": candidate.expression,
                "generation": candidate.generation,
                "sharpe_test": float(candidate.sharpe_test) if candidate.sharpe_test else 0.0,
                "ic_mean_24h": float(candidate.ic_mean_24h) if candidate.ic_mean_24h else 0.0,
                "ic_ir": float(candidate.ic_ir) if candidate.ic_ir else 0.0,
            })

        return {
            "total": len(factors),
            "factors": factors,
        }


@router.get(
    "/factors/{name}",
    response_model=FactorDetailResponse,
    summary="获取因子详情",
    description="获取指定因子原语的详细信息",
)
async def get_factor_detail(name: str) -> FactorDetailResponse:
    """
    获取因子详情
    
    - **name**: 因子原语名称，如 ts_mean, zscore 等
    """
    if name not in FACTOR_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"因子原语 '{name}' 不存在",
        )
    
    meta = FACTOR_REGISTRY[name]
    
    # 构建参数列表
    params = []
    for param_name, param_type, param_default in meta.params:
        params.append(PrimitiveParam(
            name=param_name,
            type=param_type.__name__,
            default=param_default,
        ))
    
    primitive = PrimitiveInfo(
        name=name,
        family=meta.family.value,
        family_code=meta.family.name,
        description=meta.description,
        params=params,
        supports=meta.supports,
    )
    
    # 生成示例表达式
    example_params = []
    for param_name, param_type, param_default in meta.params:
        if param_name == "window":
            example_params.append("20")
        elif param_type == int:
            example_params.append(str(param_default))
        elif param_type == float:
            example_params.append(str(param_default))
        else:
            example_params.append(str(param_default))
    
    # 根据参数类型构建示例
    if name in ["ts_mean", "ts_std", "ts_return", "zscore", "ts_rank", "ts_delta"]:
        example = f"{name}(close, {example_params[0] if example_params else 20})"
    elif name in ["ts_corr", "oi_price_corr"]:
        example = f"{name}(close, volume, {example_params[0] if example_params else 20})"
    elif name in ["atr", "ts_range"]:
        example = f"{name}(high, low, close, {example_params[0] if example_params else 14})"
    elif name == "obv":
        example = f"{name}(close, volume)"
    elif name == "vwap_ratio":
        example = f"{name}(close, volume, {example_params[0] if example_params else 20})"
    elif name in ["basis", "basis_annualized"]:
        example = f"{name}(spot, close{', ' + example_params[0] if example_params else ''})"
    elif name == "spread_near_far":
        example = f"{name}(near_contract, far_contract)"
    elif name in ["oi_change", "oi_trend", "oi_price_corr"]:
        example = f"{name}(open_interest{', ' + example_params[0] if len(meta.params) > 0 and meta.params[0][0] == 'window' else ''})"
    elif name == "night_gap":
        example = f"{name}(open, close)"
    elif name in ["trend_strength", "vol_regime"]:
        example = f"{name}(close, {example_params[0] if example_params else 20})"
    else:
        example = f"{name}({', '.join(example_params)})"
    
    # 查找相关原语（同族的其他原语）
    related = [
        k for k, v in FACTOR_REGISTRY.items()
        if v.family == meta.family and k != name
    ][:5]  # 最多5个
    
    return FactorDetailResponse(
        primitive=primitive,
        example=example,
        related_primitives=related,
    )


@router.post(
    "/factors/validate",
    response_model=FactorValidateResponse,
    summary="验证因子表达式",
    description="验证因子表达式的语法和语义约束",
)
async def validate_factor(request: FactorValidateRequest) -> FactorValidateResponse:
    """
    验证因子表达式
    
    检查表达式的语法正确性和语义约束（如树深度、族嵌套等）
    """
    try:
        # 解析表达式
        ast = parse_expr(request.expression)
        
        # 语义验证
        result = validate_expression(request.expression, symbol=request.symbol)
        
        return FactorValidateResponse(
            is_valid=result.is_valid,
            penalty_factor=result.penalty_factor,
            violations=[v.to_dict() for v in result.violations],
            ast=serialize(ast),
            expression=request.expression,
        )
    except SyntaxError as e:
        return FactorValidateResponse(
            is_valid=False,
            penalty_factor=0.0,
            violations=[{
                "code": "SYNTAX_ERROR",
                "message": str(e),
                "severity": "fatal",
                "penalty": 0.0,
            }],
            expression=request.expression,
        )
    except Exception as e:
        return FactorValidateResponse(
            is_valid=False,
            penalty_factor=0.0,
            violations=[{
                "code": "UNKNOWN_ERROR",
                "message": str(e),
                "severity": "fatal",
                "penalty": 0.0,
            }],
            expression=request.expression,
        )


@router.post(
    "/factors/test",
    response_model=FactorTestResponse,
    summary="测试因子表达式",
    description="使用测试数据执行因子表达式",
)
async def test_factor(request: FactorTestRequest) -> FactorTestResponse:
    """
    测试因子表达式
    
    使用提供的测试数据执行因子表达式，返回计算结果
    """
    import time
    
    start_time = time.time()
    
    try:
        # 解析表达式
        ast = parse_expr(request.expression)
        
        # 编译为可执行函数
        func = compile_expr(ast)
        
        # 准备数据
        data = {k: np.array(v) for k, v in request.data.items()}
        
        # 执行计算
        result = func(**data)
        
        # 转换为列表
        result_list = result.tolist() if hasattr(result, 'tolist') else list(result)
        
        execution_time = (time.time() - start_time) * 1000
        
        return FactorTestResponse(
            success=True,
            result=result_list,
            error=None,
            execution_time_ms=round(execution_time, 2),
        )
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return FactorTestResponse(
            success=False,
            result=None,
            error=str(e),
            execution_time_ms=round(execution_time, 2),
        )


@router.get(
    "/families",
    summary="获取因子族列表",
    description="获取所有因子族的定义和统计信息",
)
async def get_families() -> Dict[str, Any]:
    """获取因子族列表"""
    families = {}

    for family in PrimitiveFamily:
        primitives = list_primitives(family)
        families[family.name] = {
            "name": family.value,
            "code": family.name,
            "count": len(primitives),
            "primitives": primitives,
        }

    return {
        "total_families": len(families),
        "families": families,
    }
