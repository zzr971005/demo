"""
策略轮换调度器
定期执行策略轮换任务
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from quant_engine.ops.evolution_scheduler import ScheduledTask
from quant_engine.ops.strategy_rotation import StrategyRotator

logger = logging.getLogger(__name__)


class StrategyRotationTask(ScheduledTask):
    """策略轮换任务"""

    def __init__(
        self,
        task_id: str,
        interval_days: int = 14,
        enabled: bool = True
    ):
        super().__init__(
            task_id=task_id,
            name="策略轮换",
            symbol="ALL",
            cron_expression=f"0 0 */{interval_days} * *",
            task_type="rotation",
            next_run_time=datetime.utcnow() + timedelta(days=interval_days),
            enabled=enabled
        )
        self.interval_days = interval_days
        self.rotator = StrategyRotator()

    def execute(self) -> bool:
        """
        执行策略轮换

        Returns:
            是否执行成功
        """
        try:
            logger.info(f"开始执行策略轮换任务: {self.task_id}")

            # 执行策略轮换
            result = self.rotator.execute_rotation()

            logger.info(f"策略轮换完成: {result}")
            return True
        except Exception as e:
            logger.error(f"策略轮换失败: {e}", exc_info=True)
            return False

    def get_next_run_time(self, last_run_time: Optional[datetime] = None) -> datetime:
        """
        计算下次运行时间

        Args:
            last_run_time: 上次运行时间

        Returns:
            下次运行时间
        """
        if last_run_time is None:
            return datetime.utcnow() + timedelta(days=self.interval_days)
        return last_run_time + timedelta(days=self.interval_days)

    def should_run(self, last_run_time: Optional[datetime] = None) -> bool:
        """
        判断是否应该运行

        Args:
            last_run_time: 上次运行时间

        Returns:
            是否应该运行
        """
        if not self.enabled:
            return False

        if last_run_time is None:
            return True

        next_run_time = self.get_next_run_time(last_run_time)
        return datetime.utcnow() >= next_run_time
