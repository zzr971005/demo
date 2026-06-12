"""
事件总线 — Task 11

职责：
- Redis Pub/Sub 事件发布与订阅
- 事件分类和路由
- 与 candidate_core、risk_monitor 联动
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 事件类型定义
# ---------------------------------------------------------------------------

class EventCategory(str, Enum):
    SYSTEM = "system"
    CANDIDATE = "candidate"
    RISK = "risk"
    TRADE = "trade"
    SYMBOL = "symbol"
    EVOLUTION = "evolution"
    LOOP = "loop"
    PAPER = "paper"


class EventType(str, Enum):
    # 系统
    SYSTEM_START = "system:start"
    SYSTEM_STOP = "system:stop"
    SYSTEM_HEARTBEAT = "system:heartbeat"

    # 候选策略
    CANDIDATE_STATE_CHANGE = "candidate:state_change"
    CANDIDATE_PROMOTION = "candidate:promotion"
    CANDIDATE_DEGRADATION = "candidate:degradation"
    CANDIDATE_RETIRE = "candidate:retire"

    # 风控
    RISK_ALERT = "risk:alert"
    RISK_CIRCUIT_BREAKER = "risk:circuit_breaker"
    RISK_PAUSE = "risk:pause"

    # 交易
    TRADE_ORDER = "trade:order"
    TRADE_FILL = "trade:fill"
    TRADE_POSITION_CHANGE = "trade:position_change"

    # 品种
    SYMBOL_MODE_SWITCH = "symbol:mode_switch"
    SYMBOL_DELIVERY_WARNING = "symbol:delivery_warning"

    # 进化
    EVOLUTION_START = "evolution:start"
    EVOLUTION_COMPLETE = "evolution:complete"
    EVOLUTION_GENERATION = "evolution:generation"

    # 主循环
    LOOP_STATE_CHANGE = "loop:state_change"
    LOOP_RECOVER = "loop:recover"

    # 模拟盘
    PAPER_HEARTBEAT = "paper:heartbeat"
    PAPER_PROMOTION = "paper:promotion"


# ---------------------------------------------------------------------------
# 事件数据模型
# ---------------------------------------------------------------------------

@dataclass
class QuantEvent:
    """量化系统事件"""

    event_type: EventType
    category: EventCategory
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "category": self.category.value,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuantEvent":
        return cls(
            event_type=EventType(data["event_type"]),
            category=EventCategory(data["category"]),
            payload=data.get("payload", {}),
            source=data.get("source", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
        )


# ---------------------------------------------------------------------------
# 事件总线
# ---------------------------------------------------------------------------

class EventBus:
    """
    事件总线

    基于 Redis Pub/Sub 实现的事件发布/订阅系统：
    - 支持按事件类型和分类路由
    - 支持本地内存回调（无 Redis 时降级）
    - 异步发布与订阅
    """

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        self.redis = redis_client
        self._local_subscribers: Dict[str, List[Callable[[QuantEvent], Coroutine[Any, Any, Any]]]] = {}
        self._running = False
        self._pubsub_task: Optional[asyncio.Task] = None

    # -----------------------------------------------------------------------
    # 发布
    # -----------------------------------------------------------------------

    async def publish(self, event: QuantEvent, channel: Optional[str] = None) -> None:
        """
        发布事件。

        优先通过 Redis 发布，无 Redis 时触发本地回调。
        """
        # 本地回调
        await self._notify_local(event)

        # Redis 发布
        if self.redis is not None:
            ch = channel or self._default_channel(event)
            try:
                await self.redis.publish(ch, event.to_json())
            except Exception as e:
                logger.warning(f"Redis事件发布失败 [{ch}]: {e}")

    async def publish_dict(
        self,
        event_type: EventType,
        category: EventCategory,
        payload: Dict[str, Any],
        source: str = "",
        correlation_id: Optional[str] = None,
    ) -> None:
        """便捷方法：从字典参数发布事件。"""
        event = QuantEvent(
            event_type=event_type,
            category=category,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
        )
        await self.publish(event)

    # -----------------------------------------------------------------------
    # 订阅
    # -----------------------------------------------------------------------

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[QuantEvent], Coroutine[Any, Any, Any]],
    ) -> None:
        """订阅指定事件类型（本地回调）。"""
        key = event_type.value
        if key not in self._local_subscribers:
            self._local_subscribers[key] = []
        self._local_subscribers[key].append(handler)
        logger.debug(f"事件订阅已注册: {key}")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[QuantEvent], Coroutine[Any, Any, Any]],
    ) -> bool:
        """取消订阅。"""
        key = event_type.value
        handlers = self._local_subscribers.get(key, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    async def start_redis_listener(self, channels: Optional[List[str]] = None) -> None:
        """
        启动 Redis 订阅监听器。

        监听指定频道，收到消息后转换为 QuantEvent 并触发本地回调。
        """
        if self.redis is None:
            logger.warning("Redis未配置，无法启动监听器")
            return

        if self._running:
            return
        self._running = True

        default_channels = [
            "system:*",
            "candidate:*",
            "risk:*",
            "trade:*",
            "symbol:*",
            "evolution:*",
            "loop:*",
            "paper:*",
        ]
        channels = channels or default_channels

        self._pubsub_task = asyncio.create_task(self._redis_listen_loop(channels))
        logger.info(f"Redis事件监听器已启动，频道: {channels}")

    async def stop_redis_listener(self) -> None:
        """停止 Redis 订阅监听器。"""
        self._running = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
            self._pubsub_task = None
        logger.info("Redis事件监听器已停止")

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    async def _notify_local(self, event: QuantEvent) -> None:
        """触发本地订阅回调。"""
        handlers = self._local_subscribers.get(event.event_type.value, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.exception(f"本地事件处理失败 [{event.event_type.value}]: {e}")

    async def _redis_listen_loop(self, channels: List[str]) -> None:
        """Redis 订阅循环。"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)

            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    event = QuantEvent.from_dict(data)
                    await self._notify_local(event)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Redis消息解析失败: {e}")
        except Exception as e:
            logger.exception(f"Redis监听异常: {e}")
        finally:
            try:
                await pubsub.unsubscribe(*channels)
            except Exception:
                pass

    def _default_channel(self, event: QuantEvent) -> str:
        """根据事件类型生成默认频道名。"""
        return event.event_type.value.split(":")[0] + ":*"

    # -----------------------------------------------------------------------
    # 便捷工厂方法
    # -----------------------------------------------------------------------

    @staticmethod
    def candidate_state_change(
        candidate_id: str,
        symbol: str,
        from_status: str,
        to_status: str,
        reason: str = "",
    ) -> QuantEvent:
        return QuantEvent(
            event_type=EventType.CANDIDATE_STATE_CHANGE,
            category=EventCategory.CANDIDATE,
            payload={
                "candidate_id": candidate_id,
                "symbol": symbol,
                "from_status": from_status,
                "to_status": to_status,
                "reason": reason,
            },
            source="candidate_core",
        )

    @staticmethod
    def risk_alert(
        rule_name: str,
        level: str,
        symbol: Optional[str],
        message: str,
        metric_value: float,
        action_taken: str,
    ) -> QuantEvent:
        return QuantEvent(
            event_type=EventType.RISK_ALERT,
            category=EventCategory.RISK,
            payload={
                "rule_name": rule_name,
                "level": level,
                "symbol": symbol,
                "message": message,
                "metric_value": metric_value,
                "action_taken": action_taken,
            },
            source="risk_monitor",
        )

    @staticmethod
    def symbol_mode_switch(
        symbol: str,
        from_mode: str,
        to_mode: str,
        operator: str,
        position_action: str = "",
    ) -> QuantEvent:
        return QuantEvent(
            event_type=EventType.SYMBOL_MODE_SWITCH,
            category=EventCategory.SYMBOL,
            payload={
                "symbol": symbol,
                "from_mode": from_mode,
                "to_mode": to_mode,
                "operator": operator,
                "position_action": position_action,
            },
            source="manual_switch",
        )

    @staticmethod
    def loop_state_change(
        state: str,
        checkpoint: Optional[Dict[str, Any]] = None,
    ) -> QuantEvent:
        return QuantEvent(
            event_type=EventType.LOOP_STATE_CHANGE,
            category=EventCategory.LOOP,
            payload={"state": state, "checkpoint": checkpoint or {}},
            source="infinite_loop",
        )


# ---------------------------------------------------------------------------
# 事件路由器
# ---------------------------------------------------------------------------

class EventRouter:
    """
    事件路由器

    根据事件类型将事件分发到不同的处理管道。
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._routes: Dict[str, List[str]] = {}
        self._handlers: Dict[str, Callable[[QuantEvent], Coroutine[Any, Any, Any]]] = {}

    def register_route(
        self,
        event_type: EventType,
        handler: Callable[[QuantEvent], Coroutine[Any, Any, Any]],
        handler_id: Optional[str] = None,
    ) -> str:
        """注册事件路由。"""
        hid = handler_id or f"{event_type.value}_{id(handler)}"
        self._handlers[hid] = handler

        key = event_type.value
        if key not in self._routes:
            self._routes[key] = []
        self._routes[key].append(hid)

        self.bus.subscribe(event_type, handler)
        logger.info(f"路由已注册: {key} -> {hid}")
        return hid

    def unregister_route(self, handler_id: str) -> bool:
        """注销路由。"""
        if handler_id not in self._handlers:
            return False
        del self._handlers[handler_id]
        for key, hids in self._routes.items():
            if handler_id in hids:
                hids.remove(handler_id)
        return True

    async def route(self, event: QuantEvent) -> None:
        """手动路由事件（通常由 EventBus 自动触发）。"""
        hids = self._routes.get(event.event_type.value, [])
        for hid in hids:
            handler = self._handlers.get(hid)
            if handler:
                try:
                    await handler(event)
                except Exception as e:
                    logger.exception(f"路由处理失败 [{hid}]: {e}")
