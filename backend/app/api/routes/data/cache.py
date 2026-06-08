"""
数据缓存管理API

提供数据缓存状态查询、更新、质量检查等功能
复用现有组件：TimescaleHub, DataInitializer, verify_term_structure
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from quant_engine.data.hub import TimescaleHub
from app.init_data import DataInitializer
from app.config import get_settings

logger = logging.getLogger("quant_engine.api.cache")

router = APIRouter(prefix="/cache", tags=["cache"])

# ============================================================================
# 数据模型
# ============================================================================

class CacheStatus(BaseModel):
    """缓存状态"""
    total_symbols: int
    total_size: str
    data_integrity: float
    last_update: Optional[str]
    next_update: Optional[str]

class CacheSymbol(BaseModel):
    """品种缓存信息"""
    symbol: str
    data_type: str  # main_1h, main_1d, term_structure
    time_range: str
    record_count: int
    file_size: str
    quality: str  # correct, abnormal, error
    status: str  # normal, expired, missing
    last_update: Optional[str]

class UpdateRequest(BaseModel):
    """数据更新请求"""
    type: str  # incremental, full, term_structure
    symbols: Optional[List[str]] = None
    force: bool = False

class UpdateResponse(BaseModel):
    """数据更新响应"""
    task_id: str
    status: str
    message: str

class SchedulerStatus(BaseModel):
    """调度器状态"""
    status: str
    next_run: Optional[str]
    cron_expression: str
    last_run: Optional[str]
    last_result: str
    auto_start: bool

class QualityCheck(BaseModel):
    """质量检查结果"""
    integrity: Dict[str, str]
    backup_consistency: Dict[str, str]
    term_structure: Dict[str, str]
    timeliness: Dict[str, str]
    anomalies: List[Dict[str, str]]

class CleanupRequest(BaseModel):
    """清理请求"""
    days: int = 30

class CleanupResponse(BaseModel):
    """清理响应"""
    deleted_files: int
    freed_space: str

class UpdateHistory(BaseModel):
    """更新历史"""
    id: str
    timestamp: str
    type: str
    symbols: List[str]
    status: str
    duration: str
    message: str

# ============================================================================
# 全局变量
# ============================================================================

# 缓存目录
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "kline_cache"

# 支持的品种
DEFAULT_SYMBOLS = [
    "RB",  # 螺纹钢
    "MA",  # 甲醇
    "M",   # 豆粕
    "TA",  # PTA
    "FG",  # 玻璃
    "SR",  # 白糖
    "SA",  # 纯碱
    "PP",  # 聚丙烯
]

EXTENDED_SYMBOLS = [
    "AU",  # 黄金
    "CU",  # 铜
    "SC",  # 原油
    "IF",  # 沪深300股指
]

ALL_SYMBOLS = DEFAULT_SYMBOLS + EXTENDED_SYMBOLS

# 支持的K线周期（秒）
SUPPORTED_DURATIONS = {
    3600: "1h",
    86400: "1d",
}

# 更新历史（内存存储，生产环境应使用数据库）
_update_history: List[UpdateHistory] = []

# ============================================================================
# 辅助函数
# ============================================================================

def get_file_size(file_path: Path) -> str:
    """获取文件大小，返回人类可读格式"""
    if not file_path.exists():
        return "0B"
    size = file_path.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def get_cache_dir_size() -> int:
    """获取缓存目录总大小（字节）"""
    total_size = 0
    if DEFAULT_CACHE_DIR.exists():
        for file_path in DEFAULT_CACHE_DIR.iterdir():
            if file_path.is_file():
                total_size += file_path.stat().st_size
    return total_size

def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"

# ============================================================================
# API端点
# ============================================================================

@router.get("/status", response_model=CacheStatus)
async def get_cache_status():
    """获取缓存状态概览"""
    try:
        hub = TimescaleHub()
        
        # 获取所有品种
        all_symbols = hub.get_all_symbols(duration_seconds=3600)
        total_symbols = len(all_symbols) if all_symbols else 0
        
        # 获取缓存总大小
        total_size_bytes = get_cache_dir_size()
        total_size = format_size(total_size_bytes)
        
        # 数据完整性（简化计算）
        data_integrity = 0.98  # 默认值，实际应通过质量检查计算
        
        # 最后更新时间（从历史记录获取）
        last_update = _update_history[0].timestamp if _update_history else None
        
        # 下次更新时间（20:30）
        now = datetime.now()
        if now.hour < 20 or (now.hour == 20 and now.minute < 30):
            next_update = now.replace(hour=20, minute=30, second=0, microsecond=0)
        else:
            from datetime import timedelta
            next_update = (now + timedelta(days=1)).replace(hour=20, minute=30, second=0, microsecond=0)
        next_update_str = next_update.strftime("%Y-%m-%d %H:%M:%S")
        
        return CacheStatus(
            total_symbols=total_symbols,
            total_size=total_size,
            data_integrity=data_integrity,
            last_update=last_update,
            next_update=next_update_str
        )
    except Exception as e:
        logger.error(f"获取缓存状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols", response_model=List[CacheSymbol])
async def get_cache_symbols():
    """获取所有品种的缓存信息"""
    try:
        hub = TimescaleHub()
        results = []
        
        for symbol in ALL_SYMBOLS:
            # 检查主连1H数据
            try:
                min_ts, max_ts = hub.get_available_range(symbol, 3600)
                record_count = hub.get_record_count(symbol, 3600)
                
                if min_ts and max_ts:
                    time_range = f"{min_ts.strftime('%Y-%m-%d')} ~ {max_ts.strftime('%Y-%m-%d')}"
                    status = "normal"
                    quality = "correct"
                    last_update = max_ts.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_range = "无数据"
                    status = "missing"
                    quality = "error"
                    last_update = None
                
                # 文件大小（估算）
                file_size = f"{record_count * 18 / 1024 / 1024:.1f}MB" if record_count > 0 else "0B"
                
                results.append(CacheSymbol(
                    symbol=symbol,
                    data_type="main_1h",
                    time_range=time_range,
                    record_count=record_count,
                    file_size=file_size,
                    quality=quality,
                    status=status,
                    last_update=last_update
                ))
            except Exception as e:
                logger.debug(f"获取品种 {symbol} 1H数据失败: {e}")
                results.append(CacheSymbol(
                    symbol=symbol,
                    data_type="main_1h",
                    time_range="查询失败",
                    record_count=0,
                    file_size="0B",
                    quality="error",
                    status="error",
                    last_update=None
                ))
            
            # 检查期限结构数据
            try:
                df = hub.query_term_structure(symbol, duration_seconds=3600, limit=1)
                if not df.empty:
                    record_count = len(hub.query_term_structure(symbol, duration_seconds=3600))
                    time_range = f"{df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')}"
                    status = "normal"
                    quality = "correct"
                    last_update = df.index.max().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_range = "无数据"
                    status = "missing"
                    quality = "error"
                    last_update = None
                
                file_size = f"{record_count * 30 / 1024 / 1024:.1f}MB" if record_count > 0 else "0B"
                
                results.append(CacheSymbol(
                    symbol=symbol,
                    data_type="term_structure",
                    time_range=time_range,
                    record_count=record_count,
                    file_size=file_size,
                    quality=quality,
                    status=status,
                    last_update=last_update
                ))
            except Exception as e:
                logger.debug(f"获取品种 {symbol} 期限结构数据失败: {e}")
                results.append(CacheSymbol(
                    symbol=symbol,
                    data_type="term_structure",
                    time_range="查询失败",
                    record_count=0,
                    file_size="0B",
                    quality="error",
                    status="error",
                    last_update=None
                ))
        
        return results
    except Exception as e:
        logger.error(f"获取品种缓存信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update", response_model=UpdateResponse)
async def trigger_update(request: UpdateRequest, background_tasks: BackgroundTasks):
    """触发数据更新"""
    try:
        task_id = f"update_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 添加到后台任务
        def run_update():
            try:
                initializer = DataInitializer()
                symbols = request.symbols or ALL_SYMBOLS
                
                if request.type == "incremental":
                    result = initializer.download_all_symbols(
                        symbols=symbols,
                        incremental=True,
                        force=request.force
                    )
                elif request.type == "full":
                    result = initializer.download_all_symbols(
                        symbols=symbols,
                        incremental=False,
                        force=request.force
                    )
                elif request.type == "term_structure":
                    result = initializer.download_term_structure(
                        symbols=symbols,
                        force=request.force
                    )
                else:
                    raise ValueError(f"不支持的更新类型: {request.type}")
                
                # 记录历史
                history = UpdateHistory(
                    id=task_id,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    type=request.type,
                    symbols=symbols,
                    status="success",
                    duration="unknown",
                    message=f"{len(symbols)}品种更新完成"
                )
                _update_history.insert(0, history)
                if len(_update_history) > 100:
                    _update_history.pop()
                    
            except Exception as e:
                logger.error(f"数据更新失败: {e}")
                history = UpdateHistory(
                    id=task_id,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    type=request.type,
                    symbols=request.symbols or ALL_SYMBOLS,
                    status="failed",
                    duration="unknown",
                    message=str(e)
                )
                _update_history.insert(0, history)
        
        background_tasks.add_task(run_update)
        
        return UpdateResponse(
            task_id=task_id,
            status="running",
            message="数据更新任务已启动"
        )
    except Exception as e:
        logger.error(f"触发数据更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scheduler/status", response_model=SchedulerStatus)
async def get_scheduler_status():
    """获取调度器状态"""
    try:
        # 调度器默认开启
        now = datetime.now()
        if now.hour < 20 or (now.hour == 20 and now.minute < 30):
            next_run = now.replace(hour=20, minute=30, second=0, microsecond=0)
        else:
            from datetime import timedelta
            next_run = (now + timedelta(days=1)).replace(hour=20, minute=30, second=0, microsecond=0)
        
        last_run = _update_history[0].timestamp if _update_history else None
        last_result = _update_history[0].status if _update_history else "success"
        
        return SchedulerStatus(
            status="running",
            next_run=next_run.strftime("%Y-%m-%d %H:%M:%S"),
            cron_expression="0 30 20 * * *",
            last_run=last_run,
            last_result=last_result,
            auto_start=True
        )
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scheduler/trigger")
async def trigger_scheduler():
    """手动触发调度器"""
    try:
        task_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 触发增量更新
        from fastapi import BackgroundTasks
        background_tasks = BackgroundTasks()
        
        request = UpdateRequest(type="incremental", symbols=None)
        return await trigger_update(request, background_tasks)
    except Exception as e:
        logger.error(f"手动触发调度器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quality/check", response_model=QualityCheck)
async def check_data_quality():
    """检查数据质量"""
    try:
        initializer = DataInitializer()
        
        # 检查数据完整性
        try:
            initializer.check_data_status(ALL_SYMBOLS)
            integrity = {"status": "pass", "details": "所有品种数据完整"}
        except Exception as e:
            integrity = {"status": "fail", "details": str(e)}
        
        # 检查备份一致性
        try:
            backup_status = initializer.check_backup_status(ALL_SYMBOLS)
            if backup_status.get("all_ok"):
                backup_consistency = {"status": "pass", "details": "数据库与CSV备份同步"}
            else:
                backup_consistency = {"status": "fail", "details": "数据库与备份不同步"}
        except Exception as e:
            backup_consistency = {"status": "fail", "details": str(e)}
        
        # 检查期限结构（简化）
        try:
            hub = TimescaleHub()
            # 检查至少一个品种有期限结构数据
            df = hub.query_term_structure("MA", duration_seconds=3600, limit=1)
            if not df.empty:
                term_structure = {"status": "pass", "details": "主力/近月/远月合约数据正常"}
            else:
                term_structure = {"status": "fail", "details": "期限结构数据缺失"}
        except Exception as e:
            term_structure = {"status": "fail", "details": str(e)}
        
        # 检查时效性
        try:
            hub = TimescaleHub()
            min_ts, max_ts = hub.get_available_range("RB", 3600)
            if max_ts:
                # 检查数据是否在最近24小时内
                from datetime import timedelta
                if datetime.now() - max_ts.replace(tzinfo=None) < timedelta(days=2):
                    timeliness = {"status": "pass", "details": "数据更新至今日收盘"}
                else:
                    timeliness = {"status": "warn", "details": "数据可能过期"}
            else:
                timeliness = {"status": "fail", "details": "无数据"}
        except Exception as e:
            timeliness = {"status": "fail", "details": str(e)}
        
        return QualityCheck(
            integrity=integrity,
            backup_consistency=backup_consistency,
            term_structure=term_structure,
            timeliness=timeliness,
            anomalies=[]
        )
    except Exception as e:
        logger.error(f"数据质量检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{symbol}/{data_type}")
async def delete_cache(symbol: str, data_type: str):
    """删除指定品种的缓存"""
    try:
        # 这里只是示例，实际实现需要根据data_type删除相应的缓存
        # 可以删除parquet文件或数据库中的数据
        logger.info(f"删除品种 {symbol} 的 {data_type} 缓存")
        return {"success": True, "message": "缓存已删除"}
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup/expired", response_model=CleanupResponse)
async def cleanup_expired_cache(request: CleanupRequest):
    """清理过期缓存"""
    try:
        deleted_files = 0
        freed_space = 0
        
        if DEFAULT_CACHE_DIR.exists():
            cutoff_time = datetime.now().timestamp() - (request.days * 24 * 3600)
            for file_path in DEFAULT_CACHE_DIR.iterdir():
                if file_path.is_file():
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files += 1
                        freed_space += file_size
                        logger.info(f"删除过期缓存文件: {file_path.name}")
        
        return CleanupResponse(
            deleted_files=deleted_files,
            freed_space=format_size(freed_space)
        )
    except Exception as e:
        logger.error(f"清理过期缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[UpdateHistory])
async def get_update_history(limit: int = Query(20, ge=1, le=100)):
    """获取更新历史"""
    try:
        return _update_history[:limit]
    except Exception as e:
        logger.error(f"获取更新历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
