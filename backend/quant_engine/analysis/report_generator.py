"""
自动化报告生成系统 - 生成策略绩效、风控、交易成本等报告
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化生成器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.report_format = self.config.get("report_format", "json")
    
    def generate_strategy_performance_report(
        self,
        strategy_id: str,
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成策略绩效报告
        
        Parameters
        ----------
        strategy_id : str
            策略ID
        performance_data : Dict[str, Any]
            绩效数据
        
        Returns
        -------
        Dict[str, Any]
            报告
        """
        report = {
            "report_type": "strategy_performance",
            "strategy_id": strategy_id,
            "generated_at": datetime.utcnow(),
            "period": {
                "start": performance_data.get("start_date"),
                "end": performance_data.get("end_date")
            },
            "metrics": {
                "total_return": performance_data.get("total_return"),
                "annual_return": performance_data.get("annual_return"),
                "sharpe_ratio": performance_data.get("sharpe_ratio"),
                "max_drawdown": performance_data.get("max_drawdown"),
                "win_rate": performance_data.get("win_rate"),
                "total_trades": performance_data.get("total_trades")
            },
            "risk_metrics": {
                "volatility": performance_data.get("volatility"),
                "var_95": performance_data.get("var_95"),
                "cvar_95": performance_data.get("cvar_95")
            },
            "summary": self._generate_performance_summary(performance_data)
        }
        
        return report
    
    def generate_risk_report(
        self,
        risk_events: List[Dict[str, Any]],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成风控报告
        
        Parameters
        ----------
        risk_events : List[Dict[str, Any]]
            风控事件列表
        account_info : Dict[str, Any]
            账户信息
        
        Returns
        -------
        Dict[str, Any]
            报告
        """
        total_events = len(risk_events)
        critical_events = [e for e in risk_events if e.get("level") == "CRITICAL"]
        unresolved_events = [e for e in risk_events if not e.get("is_resolved", False)]
        
        report = {
            "report_type": "risk_management",
            "generated_at": datetime.utcnow(),
            "account_info": account_info,
            "risk_summary": {
                "total_events": total_events,
                "critical_events": len(critical_events),
                "unresolved_events": len(unresolved_events),
                "risk_level": self._calculate_risk_level(risk_events)
            },
            "recent_events": risk_events[:10],
            "recommendations": self._generate_risk_recommendations(risk_events)
        }
        
        return report
    
    def generate_transaction_cost_report(
        self,
        cost_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成交易成本报告
        
        Parameters
        ----------
        cost_data : Dict[str, Any]
            成本数据
        
        Returns
        -------
        Dict[str, Any]
            报告
        """
        report = {
            "report_type": "transaction_cost",
            "generated_at": datetime.utcnow(),
            "period": cost_data.get("period"),
            "total_cost": cost_data.get("total_cost"),
            "cost_breakdown": cost_data.get("cost_breakdown"),
            "cost_by_symbol": cost_data.get("cost_by_symbol"),
            "cost_trend": cost_data.get("cost_trend"),
            "recommendations": self._generate_cost_recommendations(cost_data)
        }
        
        return report
    
    def generate_portfolio_report(
        self,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成组合报告
        
        Parameters
        ----------
        portfolio_data : Dict[str, Any]
            组合数据
        
        Returns
        -------
        Dict[str, Any]
            报告
        """
        report = {
            "report_type": "portfolio",
            "generated_at": datetime.utcnow(),
            "portfolio_id": portfolio_data.get("portfolio_id"),
            "total_value": portfolio_data.get("total_value"),
            "allocation": portfolio_data.get("allocation"),
            "performance": portfolio_data.get("performance"),
            "risk_metrics": portfolio_data.get("risk_metrics"),
            "diversification": portfolio_data.get("diversification"),
            "recommendations": self._generate_portfolio_recommendations(portfolio_data)
        }
        
        return report
    
    def _generate_performance_summary(self, performance_data: Dict[str, Any]) -> str:
        """生成绩效摘要"""
        sharpe = performance_data.get("sharpe_ratio", 0)
        return_rate = performance_data.get("annual_return", 0)
        max_dd = performance_data.get("max_drawdown", 0)
        
        if sharpe > 2 and return_rate > 0.2 and max_dd < 0.1:
            return "策略表现优秀"
        elif sharpe > 1 and return_rate > 0.1 and max_dd < 0.2:
            return "策略表现良好"
        elif sharpe > 0.5:
            return "策略表现一般"
        else:
            return "策略表现较差"
    
    def _calculate_risk_level(self, risk_events: List[Dict[str, Any]]) -> str:
        """计算风险等级"""
        critical_count = len([e for e in risk_events if e.get("level") == "CRITICAL"])
        high_count = len([e for e in risk_events if e.get("level") == "HIGH"])
        
        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 2:
            return "HIGH"
        elif high_count > 0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_risk_recommendations(self, risk_events: List[Dict[str, Any]]) -> List[str]:
        """生成风控建议"""
        recommendations = []
        
        critical_events = [e for e in risk_events if e.get("level") == "CRITICAL"]
        if critical_events:
            recommendations.append("立即处理所有严重风控事件")
        
        unresolved_events = [e for e in risk_events if not e.get("is_resolved", False)]
        if len(unresolved_events) > 5:
            recommendations.append("及时处理未解决的风控事件")
        
        return recommendations
    
    def _generate_cost_recommendations(self, cost_data: Dict[str, Any]) -> List[str]:
        """生成成本建议"""
        recommendations = []
        
        cost_breakdown = cost_data.get("cost_breakdown", {})
        slippage_ratio = cost_breakdown.get("slippage_ratio", 0)
        
        if slippage_ratio > 0.5:
            recommendations.append("滑点成本过高，考虑优化订单执行策略")
        
        return recommendations
    
    def _generate_portfolio_recommendations(self, portfolio_data: Dict[str, Any]) -> List[str]:
        """生成组合建议"""
        recommendations = []
        
        diversification = portfolio_data.get("diversification", {})
        correlation = diversification.get("avg_correlation", 0)
        
        if correlation > 0.7:
            recommendations.append("策略间相关性过高，建议增加分散化")
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], output_path: str):
        """
        保存报告
        
        Parameters
        ----------
        report : Dict[str, Any]
            报告数据
        output_path : str
            输出路径
        """
        if self.report_format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
        else:
            # TODO: 支持其他格式（PDF、HTML等）
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
        
        logger.info(f"报告已保存: {output_path}")
