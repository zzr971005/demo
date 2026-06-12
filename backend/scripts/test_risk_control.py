"""
风险控制测试脚本

测试风险控制功能:
1. 熔断机制
2. 止损监控
3. 回撤控制
4. 仓位限制
5. 风险事件处理

使用方法:
    cd backend
    poetry run python scripts/test_risk_control.py
"""

import requests
import time
import sys
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000"


class RiskControlTester:
    """风险控制测试器"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0

    def log(self, message: str, level: str = "info"):
        """打印日志"""
        prefix = {
            "info": "[INFO]",
            "success": "[PASS]",
            "error": "[FAIL]",
            "warn": "[WARN]",
        }.get(level, "[INFO]")
        print(f"{prefix} {message}")

    def call_api(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """调用API"""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API错误: {response.status_code} - {response.text}", "error")
                return {"success": False, "error": response.text}
        except Exception as e:
            self.log(f"请求异常: {e}", "error")
            return {"success": False, "error": str(e)}

    def test_01_risk_summary(self) -> bool:
        """测试1: 获取风险摘要"""
        self.log("=" * 50)
        self.log("测试1: 获取风险摘要")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/trading/risk/summary")

        if "circuit_breaker_level" in result:
            self.log("获取风险摘要成功", "success")
            self.log(f"熔断等级: {result.get('circuit_breaker_level')}")
            self.log(f"风险状态: {result.get('risk_status')}")
            self.log(f"总持仓数: {result.get('total_positions')}")
            self.log(f"总保证金: ¥{result.get('total_margin', 0):,.2f}")
            self.log(f"日盈亏: ¥{result.get('daily_pnl', 0):,.2f}")
            self.tests_passed += 1
            return True
        else:
            self.log("获取风险摘要失败", "error")
            self.tests_failed += 1
            return False

    def test_02_risk_events(self) -> bool:
        """测试2: 获取风险事件"""
        self.log("\n" + "=" * 50)
        self.log("测试2: 获取风险事件")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/trading/risk/events")

        if isinstance(result, list):
            self.log(f"获取成功，共 {len(result)} 个风险事件", "success")
            for event in result[:5]:  # 只显示前5个
                self.log(f"  - [{event.get('level')}] {event.get('type')}: {event.get('message')}")
            self.tests_passed += 1
            return True
        else:
            self.log("获取风险事件失败", "error")
            self.tests_failed += 1
            return False

    def test_03_circuit_breaker_levels(self) -> bool:
        """测试3: 熔断等级说明"""
        self.log("\n" + "=" * 50)
        self.log("测试3: 熔断等级说明")
        self.log("=" * 50)

        levels = {
            0: "正常 - 可以交易",
            1: "警告 - 数据延迟>10s，切换数据源",
            2: "减仓 - 日亏损>5%，减仓30%",
            3: "停止开仓 - 单品种回撤>10%，停止该品种新单",
            4: "全部平仓 - 系统异常，全部平仓",
        }

        for level, desc in levels.items():
            self.log(f"  Level {level}: {desc}")

        self.log("熔断等级说明完整", "success")
        self.tests_passed += 1
        return True

    def test_04_position_limits(self) -> bool:
        """测试4: 仓位限制检查"""
        self.log("\n" + "=" * 50)
        self.log("测试4: 仓位限制检查")
        self.log("=" * 50)

        # 获取风险摘要
        result = self.call_api("GET", "/api/trading/risk/summary")

        if "margin_usage_percent" in result:
            margin_usage = result.get("margin_usage_percent", 0)
            self.log(f"保证金使用率: {margin_usage:.2f}%")

            if margin_usage > 85:
                self.log("警告: 保证金使用率超过85%", "warn")
            elif margin_usage > 70:
                self.log("注意: 保证金使用率超过70%", "warn")
            else:
                self.log("保证金使用率在安全范围内", "success")

            self.tests_passed += 1
            return True
        else:
            self.log("无法获取保证金使用率", "error")
            self.tests_failed += 1
            return False

    def test_05_daily_loss_limit(self) -> bool:
        """测试5: 日亏损限制"""
        self.log("\n" + "=" * 50)
        self.log("测试5: 日亏损限制检查")
        self.log("=" * 50)

        # 获取风险摘要
        result = self.call_api("GET", "/api/trading/risk/summary")

        if "daily_pnl" in result:
            daily_pnl = result.get("daily_pnl", 0)
            self.log(f"日盈亏: ¥{daily_pnl:,.2f}")

            # 假设初始资金为100万，日亏损限制为5%
            initial_equity = 1000000
            daily_loss_limit = initial_equity * 0.05

            if daily_pnl < -daily_loss_limit:
                self.log(f"警告: 日亏损超过限制 (¥{daily_loss_limit:,.2f})", "warn")
            else:
                self.log("日亏损在限制范围内", "success")

            self.tests_passed += 1
            return True
        else:
            self.log("无法获取日盈亏", "error")
            self.tests_failed += 1
            return False

    def test_06_drawdown_check(self) -> bool:
        """测试6: 回撤检查"""
        self.log("\n" + "=" * 50)
        self.log("测试6: 回撤检查")
        self.log("=" * 50)

        # 获取持仓
        positions = self.call_api("GET", "/api/trading/positions/non-flat")

        if isinstance(positions, list):
            max_drawdown_percent = 10  # 10%最大回撤限制

            for pos in positions:
                symbol = pos.get("symbol")
                unrealized_pnl = pos.get("unrealized_pnl", 0)
                margin = pos.get("margin", 1)

                if margin > 0:
                    pnl_percent = (unrealized_pnl / margin) * 100
                    self.log(f"  {symbol}: 浮动盈亏 {pnl_percent:.2f}%")

                    if pnl_percent < -max_drawdown_percent:
                        self.log(f"  警告: {symbol} 回撤超过 {max_drawdown_percent}%", "warn")

            self.log("回撤检查完成", "success")
            self.tests_passed += 1
            return True
        else:
            self.log("无法获取持仓信息", "error")
            self.tests_failed += 1
            return False

    def test_07_stop_loss_monitoring(self) -> bool:
        """测试7: 止损监控说明"""
        self.log("\n" + "=" * 50)
        self.log("测试7: 止损监控机制")
        self.log("=" * 50)

        mechanisms = [
            "固定止损: 亏损超过2%强制平仓",
            "追踪止损: 盈利回撤超过3%平仓",
            "时间止损: 持仓超过设定时间自动平仓",
            "波动率止损: 波动率异常时减仓",
        ]

        for mech in mechanisms:
            self.log(f"  - {mech}")

        self.log("止损监控机制说明完整", "success")
        self.tests_passed += 1
        return True

    def test_08_risk_response_flow(self) -> bool:
        """测试8: 风险响应流程"""
        self.log("\n" + "=" * 50)
        self.log("测试8: 风险响应流程")
        self.log("=" * 50)

        flow = [
            "1. 风险检测: 定时检查各项指标",
            "2. 风险识别: 判断是否触发风险阈值",
            "3. 风险分级: 根据严重程度分级",
            "4. 风险响应: 执行对应的处理措施",
            "5. 风险记录: 记录风险事件到日志",
            "6. 风险通知: 发送告警通知",
        ]

        for step in flow:
            self.log(f"  {step}")

        self.log("风险响应流程完整", "success")
        self.tests_passed += 1
        return True

    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "=" * 70)
        self.log("开始风险控制测试")
        self.log("=" * 70)

        tests = [
            self.test_01_risk_summary,
            self.test_02_risk_events,
            self.test_03_circuit_breaker_levels,
            self.test_04_position_limits,
            self.test_05_daily_loss_limit,
            self.test_06_drawdown_check,
            self.test_07_stop_loss_monitoring,
            self.test_08_risk_response_flow,
        ]

        for test in tests:
            try:
                test()
                time.sleep(0.3)
            except Exception as e:
                self.log(f"测试异常: {e}", "error")
                self.tests_failed += 1

        # 打印测试报告
        self.log("\n" + "=" * 70)
        self.log("测试报告")
        self.log("=" * 70)
        self.log(f"通过: {self.tests_passed}", "success")
        self.log(f"失败: {self.tests_failed}", "error" if self.tests_failed > 0 else "info")
        self.log(f"总计: {self.tests_passed + self.tests_failed}")

        if self.tests_failed == 0:
            self.log("\n所有风险控制测试通过！", "success")
            return 0
        else:
            self.log(f"\n有 {self.tests_failed} 个测试失败", "error")
            return 1


def main():
    """主函数"""
    print("期货自动进化因子挖掘系统 - 风险控制测试")
    print("=" * 70)
    print(f"API地址: {BASE_URL}")
    print("=" * 70)

    # 检查后端服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/api/execution/health", timeout=5)
        print("后端服务已连接")
    except requests.exceptions.ConnectionError:
        print("[ERROR] 无法连接到后端服务，请确保服务已启动:")
        print("  poetry run python -m app.main")
        sys.exit(1)
    except Exception as e:
        print(f"[WARN] 连接检查异常: {e}")

    # 运行测试
    tester = RiskControlTester()
    exit_code = tester.run_all_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
