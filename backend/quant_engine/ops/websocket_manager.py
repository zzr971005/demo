"""
WebSocket管理器
实时数据推送和通知
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    PING = "ping"
    PONG = "pong"
    SYSTEM = "system"
    EVOLUTION = "evolution"
    EVOLUTION_PROGRESS = "evolution_progress"
    SYMBOL_UPDATE = "symbol_update"
    SIGNAL = "signal"
    POSITION = "position"
    TRADE = "trade"
    RISK = "risk"
    NOTIFICATION = "notification"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class WebSocketMessage:
    """WebSocket消息"""
    
    def __init__(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        client_id: Optional[str] = None,
        broadcast: bool = True
    ):
        self.message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.message_type = message_type
        self.payload = payload
        self.priority = priority
        self.client_id = client_id
        self.broadcast = broadcast
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（与前端 WSMessage 接口对齐）"""
        return {
            "type": self.message_type.value,
            "data": self.payload,
            "timestamp": int(self.timestamp.timestamp() * 1000)
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict())


class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, client_id: str, websocket):
        self.client_id = client_id
        self.websocket = websocket
        self.connected = True
        self.subscriptions: List[str] = []
        self.connect_time = datetime.now()
        self.last_message_time = datetime.now()
    
    async def send(self, message: WebSocketMessage):
        """发送消息"""
        if self.connected:
            try:
                await self.websocket.send_text(message.to_json())
                self.last_message_time = datetime.now()
            except Exception as e:
                logger.error(f"Failed to send message to client {self.client_id}: {e}")
                self.connected = False
    
    async def receive(self) -> Optional[str]:
        """接收消息"""
        try:
            return await self.websocket.receive_text()
        except Exception as e:
            logger.error(f"Failed to receive message from client {self.client_id}: {e}")
            self.connected = False
            return None
    
    def subscribe(self, channel: str):
        """订阅频道"""
        if channel not in self.subscriptions:
            self.subscriptions.append(channel)
            logger.info(f"Client {self.client_id} subscribed to {channel}")
    
    def unsubscribe(self, channel: str):
        """取消订阅频道"""
        if channel in self.subscriptions:
            self.subscriptions.remove(channel)
            logger.info(f"Client {self.client_id} unsubscribed from {channel}")


class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}
        self._channels: Dict[str, List[str]] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._connect_callbacks: List[Callable] = []
        self._disconnect_callbacks: List[Callable] = []
    
    def register_client(self, client_id: str, websocket) -> WebSocketClient:
        """注册客户端"""
        client = WebSocketClient(client_id, websocket)
        self._clients[client_id] = client
        
        logger.info(f"Client registered: {client_id}, total clients: {len(self._clients)}")
        
        # 触发连接回调
        for callback in self._connect_callbacks:
            try:
                callback(client_id)
            except Exception as e:
                logger.error(f"Connect callback error: {e}")
        
        return client
    
    def unregister_client(self, client_id: str):
        """注销客户端"""
        if client_id in self._clients:
            client = self._clients[client_id]
            client.connected = False
            
            # 从所有频道中移除
            for channel in self._channels:
                if client_id in self._channels[channel]:
                    self._channels[channel].remove(client_id)
            
            del self._clients[client_id]
            
            logger.info(f"Client unregistered: {client_id}, total clients: {len(self._clients)}")
            
            # 触发断开回调
            for callback in self._disconnect_callbacks:
                try:
                    callback(client_id)
                except Exception as e:
                    logger.error(f"Disconnect callback error: {e}")
    
    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        """获取客户端"""
        return self._clients.get(client_id)
    
    def get_all_clients(self) -> List[WebSocketClient]:
        """获取所有客户端"""
        return list(self._clients.values())
    
    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """发送消息给指定客户端"""
        client = self._clients.get(client_id)
        if client and client.connected:
            await client.send(message)
    
    async def broadcast(self, message: WebSocketMessage, channel: Optional[str] = None):
        """广播消息"""
        if channel:
            # 发送到指定频道
            client_ids = self._channels.get(channel, [])
            for client_id in client_ids:
                await self.send_to_client(client_id, message)
        else:
            # 广播到所有客户端
            for client in self._clients.values():
                if client.connected:
                    await client.send(message)
    
    async def queue_message(self, message: WebSocketMessage):
        """将消息加入队列"""
        await self._message_queue.put(message)
    
    async def _process_messages(self):
        """处理消息队列"""
        while self._running:
            try:
                message = await self._message_queue.get()
                
                # 处理消息
                if message.broadcast:
                    await self.broadcast(message)
                elif message.client_id:
                    await self.send_to_client(message.client_id, message)
                
                # 调用消息处理器
                handlers = self._message_handlers.get(message.message_type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")
                
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Process message error: {e}")
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
        logger.info(f"Registered handler for {message_type.value}")
    
    def register_connect_callback(self, callback: Callable):
        """注册连接回调"""
        self._connect_callbacks.append(callback)
    
    def register_disconnect_callback(self, callback: Callable):
        """注册断开回调"""
        self._disconnect_callbacks.append(callback)
    
    def subscribe_to_channel(self, client_id: str, channel: str):
        """客户端订阅频道"""
        if channel not in self._channels:
            self._channels[channel] = []
        
        if client_id not in self._channels[channel]:
            self._channels[channel].append(client_id)
            
            # 更新客户端订阅列表
            client = self._clients.get(client_id)
            if client:
                client.subscribe(channel)
    
    def unsubscribe_from_channel(self, client_id: str, channel: str):
        """客户端取消订阅频道"""
        if channel in self._channels and client_id in self._channels[channel]:
            self._channels[channel].remove(client_id)
            
            # 更新客户端订阅列表
            client = self._clients.get(client_id)
            if client:
                client.unsubscribe(channel)
    
    def get_channel_clients(self, channel: str) -> List[str]:
        """获取频道订阅者"""
        return self._channels.get(channel, [])
    
    async def start(self):
        """启动管理器"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._process_messages())
        logger.info("WebSocket manager started")
    
    async def stop(self):
        """停止管理器"""
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        # 断开所有客户端连接
        for client_id in list(self._clients.keys()):
            self.unregister_client(client_id)
        
        logger.info("WebSocket manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "running": self._running,
            "connected_clients": len(self._clients),
            "channels": len(self._channels),
            "message_queue_size": self._message_queue.qsize(),
            "registered_handlers": {
                k.value: len(v) for k, v in self._message_handlers.items()
            }
        }
    
    # 便捷方法发送各种类型消息
    async def send_system_notification(self, message: str, level: str = "info"):
        """发送系统通知"""
        msg = WebSocketMessage(
            message_type=MessageType.SYSTEM,
            payload={
                "message": message,
                "level": level
            },
            priority=MessagePriority.HIGH if level == "error" else MessagePriority.NORMAL
        )
        await self.queue_message(msg)
    
    async def send_signal(self, symbol: str, signal_data: Dict):
        """发送交易信号"""
        msg = WebSocketMessage(
            message_type=MessageType.SIGNAL,
            payload={
                "symbol": symbol,
                **signal_data
            },
            priority=MessagePriority.HIGH,
            channel="signals"
        )
        await self.queue_message(msg)
    
    async def send_position_update(self, symbol: str, position_data: Dict):
        """发送持仓更新"""
        msg = WebSocketMessage(
            message_type=MessageType.POSITION,
            payload={
                "symbol": symbol,
                **position_data
            },
            priority=MessagePriority.NORMAL,
            channel="positions"
        )
        await self.queue_message(msg)
    
    async def send_trade_notification(self, trade_data: Dict):
        """发送交易通知"""
        msg = WebSocketMessage(
            message_type=MessageType.TRADE,
            payload=trade_data,
            priority=MessagePriority.HIGH,
            channel="trades"
        )
        await self.queue_message(msg)
    
    async def send_risk_alert(self, alert_level: str, message: str, details: Dict = None):
        """发送风险告警"""
        msg = WebSocketMessage(
            message_type=MessageType.RISK,
            payload={
                "alert_level": alert_level,
                "message": message,
                "details": details or {}
            },
            priority=MessagePriority.CRITICAL if alert_level == "critical" else MessagePriority.HIGH
        )
        await self.queue_message(msg)


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()


def get_ws_manager() -> WebSocketManager:
    """获取全局WebSocket管理器实例"""
    return ws_manager
