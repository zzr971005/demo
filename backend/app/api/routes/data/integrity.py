from __future__ import annotations

from typing import Dict, List, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_db
from scripts.data_integrity_check import DataIntegrityChecker

router = APIRouter(tags=["data-integrity"])


class IntegrityIssue(BaseModel):
    type: str
    table: str
    severity: str
    details: Dict[str, Any]


class IntegrityCheckResult(BaseModel):
    duplicate_expressions: List[IntegrityIssue]
    missing_ic_fields: List[IntegrityIssue]
    abnormal_factor_values: List[IntegrityIssue]
    inconsistent_generations: List[IntegrityIssue]
    total_issues: int
    summary: Dict[str, int]


@router.get(
    "/data-integrity/check",
    response_model=IntegrityCheckResult,
    summary="Run complete data integrity check"
)
async def run_integrity_check(db=Depends(get_db)) -> IntegrityCheckResult:
    """执行完整的数据完整性检查"""
    checker = DataIntegrityChecker()
    results = checker.check_all()
    
    # 转换为API响应格式
    def convert_issues(issues: List[Dict[str, Any]]) -> List[IntegrityIssue]:
        return [
            IntegrityIssue(
                type=issue["type"],
                table=issue.get("table", ""),
                severity=issue.get("severity", "medium"),
                details=issue
            )
            for issue in issues
        ]
    
    total_issues = sum(len(v) if isinstance(v, list) else 1 for v in results.values())
    
    return IntegrityCheckResult(
        duplicate_expressions=convert_issues(results.get("duplicate_expressions", [])),
        missing_ic_fields=convert_issues(results.get("missing_ic_fields", [])),
        abnormal_factor_values=convert_issues(results.get("abnormal_factor_values", [])),
        inconsistent_generations=convert_issues(results.get("inconsistent_generations", [])),
        total_issues=total_issues,
        summary={
            "duplicate_expressions": len(results.get("duplicate_expressions", [])),
            "missing_ic_fields": len(results.get("missing_ic_fields", [])),
            "abnormal_factor_values": len(results.get("abnormal_factor_values", [])),
            "inconsistent_generations": len(results.get("inconsistent_generations", [])),
        }
    )


@router.get(
    "/data-integrity/duplicates",
    response_model=List[IntegrityIssue],
    summary="Check for duplicate factor expressions"
)
async def check_duplicates(db=Depends(get_db)) -> List[IntegrityIssue]:
    """检查重复的因子表达式"""
    checker = DataIntegrityChecker()
    issues = checker.check_duplicate_expressions()
    
    return [
        IntegrityIssue(
            type=issue["type"],
            table=issue.get("table", ""),
            severity=issue.get("severity", "medium"),
            details=issue
        )
        for issue in issues
    ]


@router.get(
    "/data-integrity/missing-ic",
    response_model=List[IntegrityIssue],
    summary="Check for missing IC fields"
)
async def check_missing_ic(db=Depends(get_db)) -> List[IntegrityIssue]:
    """检查缺失的IC字段"""
    checker = DataIntegrityChecker()
    issues = checker.check_missing_ic_fields()
    
    return [
        IntegrityIssue(
            type=issue["type"],
            table=issue.get("table", ""),
            severity=issue.get("severity", "medium"),
            details=issue
        )
        for issue in issues
    ]


@router.get(
    "/data-integrity/abnormal-values",
    response_model=List[IntegrityIssue],
    summary="Check for abnormal factor values"
)
async def check_abnormal_values(db=Depends(get_db)) -> List[IntegrityIssue]:
    """检查异常的因子值"""
    checker = DataIntegrityChecker()
    issues = checker.check_abnormal_factor_values()
    
    return [
        IntegrityIssue(
            type=issue["type"],
            table=issue.get("table", ""),
            severity=issue.get("severity", "medium"),
            details=issue
        )
        for issue in issues
    ]


@router.get(
    "/data-integrity/generations",
    response_model=List[IntegrityIssue],
    summary="Check for inconsistent generation data"
)
async def check_generations(db=Depends(get_db)) -> List[IntegrityIssue]:
    """检查不一致的代数数据"""
    checker = DataIntegrityChecker()
    issues = checker.check_inconsistent_generations()
    
    return [
        IntegrityIssue(
            type=issue["type"],
            table=issue.get("table", ""),
            severity=issue.get("severity", "medium"),
            details=issue
        )
        for issue in issues
    ]
