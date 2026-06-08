"""
实时监控告警系统 - 多渠道告警（邮件、短信、钉钉、微信）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警等级"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertChannel(Enum):
    """告警渠道"""
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"


class AlertSystem:
    """告警系统"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化告警系统
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.enabled_channels = self.config.get("enabled_channels", ["dingtalk"])
        self.alert_history: List[Dict[str, Any]] = []
        
        # 告警规则
        self.rules = self.config.get("rules", {})
    
    def send_alert(
        self,
        alert_type: str,
        level: AlertLevel,
        message: str,
        channels: Optional[List[AlertChannel]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警
        
        Parameters
        ----------
        alert_type : str
            告警类型
        level : AlertLevel
            告警等级
        message : str
            告警消息
        channels : Optional[List[AlertChannel]]
            告警渠道
        context : Optional[Dict[str, Any]]
            上下文信息
        
        Returns
        -------
        bool
            是否发送成功
        """
        if channels is None:
            channels = [AlertChannel(c) for c in self.enabled_channels]
        
        # 记录告警历史
        alert_record = {
            "alert_type": alert_type,
            "level": level.value,
            "message": message,
            "channels": [c.value for c in channels],
            "context": context,
            "sent_at": datetime.utcnow(),
            "acknowledged": False
        }
        self.alert_history.append(alert_record)
        
        # 发送告警
        success = True
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email(message, level, context)
                elif channel == AlertChannel.SMS:
                    self._send_sms(message, level, context)
                elif channel == AlertChannel.DINGTALK:
                    self._send_dingtalk(message, level, context)
                elif channel == AlertChannel.WECHAT:
                    self._send_wechat(message, level, context)
            except Exception as e:
                logger.error(f"发送告警失败 {channel.value}: {e}")
                success = False
        
        if success:
            logger.info(f"告警发送成功: {alert_type} - {message}")
        
        return success
    
    def _send_email(self, message: str, level: AlertLevel, context: Optional[Dict[str, Any]]):
        """发送邮件告警"""
        # TODO: 实现邮件发送
        logger.info(f"[邮件告警] {level.value}: {message}")
    
    def _send_sms(self, message: str, level: AlertLevel, context: Optional[Dict[str, Any]]):
        """发送短信告警"""
        # TODO: 实现短信发送
        logger.info(f"[短信告警] {level.value}: {message}")
    
    def _send_dingtalk(self, message: str, level: AlertLevel, context: Optional[Dict[str, Any]]):
        """发送钉钉告警"""
        # TODO: 实现钉钉机器人发送
        logger.info(f"[钉钉告警] {level.value}: {message}")
    
    def _send_wechat(self, message: str, level: AlertLevel, context: Optional[Dict[str, Any]]):
        """发送微信告警"""
        # TODO: 实现企业微信发送
        logger.info(f"[微信告警] {level.value}: {message}")
    
    def check_alert_rules(
        self,
        metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        检查告警规则
        
        Parameters
        ----------
        metrics : Dict[str, float]
            指标字典
        
        Returns
        -------
        List[Dict[str, Any]]
            触发的告警列表
        """
        triggered_alerts = []
        
        for rule_name, rule_config in self.rules.items():
            metric_name = rule_config.get("metric")
            threshold = rule_config.get("threshold")
            operator = rule_config.get("operator", ">")
            level = rule_config.get("level", "WARNING")
            message_template = rule_config.get("message", f"{metric_name} 触发告警")
            
            if metric_name not in metrics:
                continue
            
            metric_value = metrics[metric_name]
            
            # 检查条件
            triggered = False
            if operator == ">":
                triggered = metric_value > threshold
            elif operator == "<":
                triggered = metric_value < threshold
            elif operator == ">=":
                triggered = metric_value >= threshold
            elif operator == "<=":
                triggered = metric_value <= threshold
            elif operator == "==":
                triggered = metric_value == threshold
            
            if triggered:
                message = message_template.format(
                    metric=metric_name,
                    value=metric_value,
                    threshold=threshold
                )
                
                alert = {
                    "rule_name": rule_name,
                    "alert_type": rule_config.get("type", "RULE_TRIGGERED"),
                    "level": level,
                    "message": message,
                    "metric_value": metric_value,
                    "threshold": threshold
                }
                
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def acknowledge_alert(self, alert_index: int, acknowledged_by: str):
        """
        确认告警
        
        Parameters
        ----------
        alert_index : int
            告警索引
        acknowledged_by : str
            确认人
        """
        if 0 <= alert_index < len(self.alert_history):
            alert = self.alert_history[alert_index]
            alert["acknowledged"] = True
            alert["acknowledged_at"] = datetime.utcnow()
            alert["acknowledged_by"] = acknowledged_by
            logger.info(f"告警已确认: {alert['alert_type']}")
    
    def get_alert_history(
        self,
        level: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取告警历史
        
        Parameters
        ----------
        level : Optional[str]
            告警等级
        acknowledged : Optional[bool]
            是否已确认
        limit : int
            返回数量限制
        
        Returns
        -------
        List[Dict[str, Any]]
            告警历史
        """
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a["level"] == level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
        
        # 按时间倒序
        alerts = sorted(alerts, key=lambda x: x["sent_at"], reverse=True)
        
        return alerts[:limit]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        获取告警摘要
        
        Returns
        -------
        Dict[str, Any]
            告警摘要
        """
        total = len(self.alert_history)
        unacknowledged = len([a for a in self.alert_history if not a["acknowledged"]])
        critical = len([a for a in self.alert_history if a["level"] == AlertLevel.CRITICAL.value])
        error = len([a for a in self.alert_history if a["level"] == AlertLevel.ERROR.value])
        
        return {
            "total_alerts": total,
            "unacknowledged": unacknowledged,
            "critical": critical,
            "error": error,
            "enabled_channels": self.enabled_channels
        }
