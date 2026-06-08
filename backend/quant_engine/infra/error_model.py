"""
错误分类与告警 — Task 11

职责：
- 错误分级（INFO/WARNING/ERROR/CRITICAL/FATAL）
- 错误分类（系统/网络/数据/交易/策略）
- 告警通道（日志/Redis/可扩展Webhook）
- 与 risk_monitor 联动
- 错误聚合与去重
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 错误分级与分类
# ---------------------------------------------------------------------------

class ErrorSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class ErrorCategory(str, Enum):
    SYSTEM = "SYSTEM"          # 系统内部错误
    NETWORK = "NETWORK"        # 网络连接错误
    DATA = "DATA"              # 数据错误
    TRADE = "TRADE"            # 交易执行错误
    STRATEGY = "STRATEGY"      # 策略错误
    RISK = "RISK"              # 风控触发
    INFRA = "INFRA"            # 基础设施错误


# ---------------------------------------------------------------------------
# 错误记录
# ---------------------------------------------------------------------------

@dataclass
class ErrorRecord:
    """错误记录"""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    symbol: Optional[str] = None
    candidate_id: Optional[str] = None
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    resolution: str = ""
    count: int = 1
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "detail": self.detail,
            "source": self.source,
            "symbol": self.symbol,
            "candidate_id": self.candidate_id,
            "occurred_at": self.occurred_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_resolved": self.is_resolved,
            "resolution": self.resolution,
            "count": self.count,
            "fingerprint": self.fingerprint,
        }

    @property
    def is_alert_worthy(self) -> bool:
        """是否需要触发告警。"""
        return self.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.FATAL)


# ---------------------------------------------------------------------------
# 告警通道
# ---------------------------------------------------------------------------

class AlertChannel:
    """告警通道基类"""

    async def send(self, record: ErrorRecord) -> bool:
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """日志告警通道"""

    async def send(self, record: ErrorRecord) -> bool:
        msg = (
            f"[{record.severity.value}] [{record.category.value}] "
            f"{record.message} | source={record.source}"
        )
        if record.severity == ErrorSeverity.FATAL:
            logging.getLogger("alert.fatal").critical(msg)
        elif record.severity == ErrorSeverity.CRITICAL:
            logging.getLogger("alert.critical").critical(msg)
        elif record.severity == ErrorSeverity.ERROR:
            logging.getLogger("alert.error").error(msg)
        elif record.severity == ErrorSeverity.WARNING:
            logging.getLogger("alert.warning").warning(msg)
        else:
            logging.getLogger("alert.info").info(msg)
        return True


class RedisAlertChannel(AlertChannel):
    """Redis 告警通道"""

    def __init__(self, redis_client: Any, channel: str = "system:alerts") -> None:
        self.redis = redis_client
        self.channel = channel

    async def send(self, record: ErrorRecord) -> bool:
        if self.redis is None:
            return False
        try:
            await self.redis.publish(self.channel, json.dumps(record.to_dict(), ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"Redis告警发送失败: {e}")
            return False


# ---------------------------------------------------------------------------
# 错误管理器
# ---------------------------------------------------------------------------

class ErrorManager:
    """
    错误分类与告警管理器

    职责：
    - 接收、分类、记录错误
    - 错误指纹去重（相同错误聚合计数）
    - 按严重程度路由到不同告警通道
    - 与 risk_monitor 联动（CRITICAL/FATAL 自动触发风控）
    """

    DEDUP_WINDOW_MINUTES: int = 30
    MAX_HISTORY: int = 10000

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        self.redis = redis_client
        self._records: Dict[str, ErrorRecord] = {}
        self._history: List[str] = []
        self._channels: List[AlertChannel] = []
        self._lock = asyncio.Lock()
        self._risk_callback: Optional[Callable[[ErrorRecord], Coroutine[Any, Any, Any]]] = None

        # 默认添加日志通道
        self.add_channel(LogAlertChannel())
        if redis_client:
            self.add_channel(RedisAlertChannel(redis_client))

    # -----------------------------------------------------------------------
    # 通道管理
    # -----------------------------------------------------------------------

    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警通道。"""
        self._channels.append(channel)

    def remove_channel(self, channel: AlertChannel) -> bool:
        """移除告警通道。"""
        if channel in self._channels:
            self._channels.remove(channel)
            return True
        return False

    def set_risk_callback(
        self,
        callback: Callable[[ErrorRecord], Coroutine[Any, Any, Any]],
    ) -> None:
        """设置风控联动回调。CRITICAL/FATAL 错误会触发此回调。"""
        self._risk_callback = callback

    # -----------------------------------------------------------------------
    # 错误处理
    # -----------------------------------------------------------------------

    async def report(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        source: str = "",
        symbol: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> ErrorRecord:
        """
        报告一个错误。

        流程：
        1. 生成指纹并去重
        2. 记录错误
        3. 触发告警通道
        4. CRITICAL/FATAL 联动风控
        """
        fingerprint = self._generate_fingerprint(category, severity, message, source, symbol)
        error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{fingerprint[:8]}"

        async with self._lock:
            # 去重检查
            existing = self._find_duplicate(fingerprint)
            if existing:
                existing.count += 1
                existing.detail.update(detail or {})
                logger.debug(f"错误聚合: {existing.error_id} count={existing.count}")
                return existing

            # 新建记录
            record = ErrorRecord(
                error_id=error_id,
                category=category,
                severity=severity,
                message=message,
                detail=detail or {},
                source=source,
                symbol=symbol,
                candidate_id=candidate_id,
                fingerprint=fingerprint,
            )

            self._records[error_id] = record
            self._history.append(error_id)
            self._trim_history()

        # 触发告警
        await self._dispatch_alert(record)

        # 风控联动
        if record.is_alert_worthy and self._risk_callback:
            try:
                await self._risk_callback(record)
            except Exception as e:
                logger.exception(f"风控联动回调失败: {e}")

        return record

    async def resolve(
        self,
        error_id: str,
        resolution: str = "",
    ) -> bool:
        """标记错误为已解决。"""
        record = self._records.get(error_id)
        if record is None:
            return False
        record.is_resolved = True
        record.resolved_at = datetime.utcnow()
        record.resolution = resolution
        return True

    async def resolve_by_fingerprint(self, fingerprint: str, resolution: str = "") -> int:
        """按指纹批量解决错误。"""
        count = 0
        for record in self._records.values():
            if record.fingerprint == fingerprint and not record.is_resolved:
                record.is_resolved = True
                record.resolved_at = datetime.utcnow()
                record.resolution = resolution
                count += 1
        return count

    # -----------------------------------------------------------------------
    # 便捷方法
    # -----------------------------------------------------------------------

    async def info(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **kwargs: Any,
    ) -> ErrorRecord:
        return await self.report(category, ErrorSeverity.INFO, message, **kwargs)

    async def warning(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **kwargs: Any,
    ) -> ErrorRecord:
        return await self.report(category, ErrorSeverity.WARNING, message, **kwargs)

    async def error(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **kwargs: Any,
    ) -> ErrorRecord:
        return await self.report(category, ErrorSeverity.ERROR, message, **kwargs)

    async def critical(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **kwargs: Any,
    ) -> ErrorRecord:
        return await self.report(category, ErrorSeverity.CRITICAL, message, **kwargs)

    async def fatal(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **kwargs: Any,
    ) -> ErrorRecord:
        return await self.report(category, ErrorSeverity.FATAL, message, **kwargs)

    # -----------------------------------------------------------------------
    # 查询接口
    # -----------------------------------------------------------------------

    def get_record(self, error_id: str) -> Optional[ErrorRecord]:
        """获取单条错误记录。"""
        return self._records.get(error_id)

    def list_records(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        unresolved_only: bool = False,
        limit: int = 100,
    ) -> List[ErrorRecord]:
        """列出错误记录。"""
        records = list(self._records.values())
        if category:
            records = [r for r in records if r.category == category]
        if severity:
            records = [r for r in records if r.severity == severity]
        if unresolved_only:
            records = [r for r in records if not r.is_resolved]
        records.sort(key=lambda r: r.occurred_at, reverse=True)
        return records[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计。"""
        total = len(self._records)
        unresolved = sum(1 for r in self._records.values() if not r.is_resolved)
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for r in self._records.values():
            by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1
            by_category[r.category.value] = by_category.get(r.category.value, 0) + 1

        return {
            "total": total,
            "unresolved": unresolved,
            "by_severity": by_severity,
            "by_category": by_category,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _generate_fingerprint(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        source: str,
        symbol: Optional[str],
    ) -> str:
        """生成错误指纹用于去重。"""
        import hashlib
        content = f"{category.value}|{severity.value}|{message}|{source}|{symbol or ''}"
        return hashlib.md5(content.encode()).hexdigest()

    def _find_duplicate(self, fingerprint: str) -> Optional[ErrorRecord]:
        """在窗口期内查找相同指纹的错误。"""
        cutoff = datetime.utcnow() - timedelta(minutes=self.DEDUP_WINDOW_MINUTES)
        for record in reversed(self._history[-500:]):
            r = self._records.get(record)
            if r is None:
                continue
            if r.fingerprint == fingerprint and r.occurred_at >= cutoff and not r.is_resolved:
                return r
        return None

    def _trim_history(self) -> None:
        """修剪历史记录防止内存无限增长。"""
        while len(self._history) > self.MAX_HISTORY:
            old_id = self._history.pop(0)
            self._records.pop(old_id, None)

    async def _dispatch_alert(self, record: ErrorRecord) -> None:
        """分发告警到所有通道。"""
        for channel in self._channels:
            try:
                await channel.send(record)
            except Exception as e:
                logger.warning(f"告警通道发送失败: {e}")


# ---------------------------------------------------------------------------
# 装饰器：自动捕获异常并报告
# ---------------------------------------------------------------------------

class ErrorContext:
    """
    错误上下文管理器

    用法：
        async with ErrorContext(error_manager, category=ErrorCategory.TRADE, source="gateway"):
            await risky_operation()
    """

    def __init__(
        self,
        manager: ErrorManager,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        source: str = "",
        symbol: Optional[str] = None,
        candidate_id: Optional[str] = None,
        severity_on_error: ErrorSeverity = ErrorSeverity.ERROR,
        reraise: bool = True,
    ) -> None:
        self.manager = manager
        self.category = category
        self.source = source
        self.symbol = symbol
        self.candidate_id = candidate_id
        self.severity_on_error = severity_on_error
        self.reraise = reraise

    async def __aenter__(self) -> "ErrorContext":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_val is not None:
            await self.manager.report(
                category=self.category,
                severity=self.severity_on_error,
                message=str(exc_val),
                detail={"exc_type": exc_type.__name__ if exc_type else None},
                source=self.source,
                symbol=self.symbol,
                candidate_id=self.candidate_id,
            )
            return not self.reraise
        return True


def auto_report(
    manager: ErrorManager,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    source: str = "",
    severity: ErrorSeverity = ErrorSeverity.ERROR,
):
    """
    装饰器：自动捕获异步函数异常并报告。

    用法：
        @auto_report(error_manager, category=ErrorCategory.STRATEGY, source="runner")
        async def my_func():
            ...
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await manager.report(
                    category=category,
                    severity=severity,
                    message=f"{func.__name__} 异常: {e}",
                    detail={"func": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    source=source,
                )
                raise
        return wrapper
    return decorator
