"""
交易流程测试脚本

测试完整的交易链路:
1. 启动交易网关
2. 查询账户信息
3. 下单
4. 查询订单状态
5. 查询持仓
6. 平仓
7. 紧急平仓
8. 停止网关

使用方法:
    cd backend
    poetry run python scripts/test_trading_flow.py
"""

import requests
import time
import sys
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000"

# 测试合约
TEST_SYMBOL = "KQ.m@SHFE.rb"


class TradingFlowTester:
    """交易流程测试器"""

    def __init__(self):
        self.order_id = None
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

    def test_01_health_check(self) -> bool:
        """测试1: 健康检查"""
        self.log("=" * 50)
        self.log("测试1: 健康检查")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/execution/health")

        if result.get("status") == "healthy":
            self.log(f"服务状态: {result.get('status')}", "success")
            self.log(f"连接状态: {result.get('connected')}")
            self.tests_passed += 1
            return True
        else:
            self.log("健康检查失败", "error")
            self.tests_failed += 1
            return False

    def test_02_start_gateway(self) -> bool:
        """测试2: 启动交易网关"""
        self.log("\n" + "=" * 50)
        self.log("测试2: 启动交易网关 (MOCK模式)")
        self.log("=" * 50)

        result = self.call_api("POST", "/api/execution/start?mode=mock")

        if result.get("success"):
            self.log("网关启动成功", "success")
            self.log(f"交易模式: {result.get('status', {}).get('mode')}")
            self.log(f"运行状态: {result.get('status', {}).get('running')}")
            self.tests_passed += 1
            return True
        else:
            self.log(f"网关启动失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_03_get_status(self) -> bool:
        """测试3: 获取交易状态"""
        self.log("\n" + "=" * 50)
        self.log("测试3: 获取交易状态")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/execution/status")

        if result.get("running"):
            self.log("网关运行中", "success")
            self.log(f"连接状态: {result.get('connected')}")
            self.log(f"交易模式: {result.get('mode')}")
            self.log(f"风险状态: {result.get('risk_status')}")
            self.log(f"熔断等级: {result.get('circuit_breaker_level')}")
            self.log(f"可以交易: {result.get('can_trade')}")
            self.tests_passed += 1
            return True
        else:
            self.log("网关未运行", "error")
            self.tests_failed += 1
            return False

    def test_04_get_account(self) -> bool:
        """测试4: 获取账户信息"""
        self.log("\n" + "=" * 50)
        self.log("测试4: 获取账户信息")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/execution/account")

        if "balance" in result:
            self.log("获取账户信息成功", "success")
            self.log(f"总资产: ¥{result.get('balance', 0):,.2f}")
            self.log(f"可用资金: ¥{result.get('available', 0):,.2f}")
            self.log(f"占用保证金: ¥{result.get('margin', 0):,.2f}")
            self.log(f"浮动盈亏: ¥{result.get('float_profit', 0):,.2f}")
            self.tests_passed += 1
            return True
        else:
            self.log(f"获取账户信息失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_05_place_order(self) -> bool:
        """测试5: 下单"""
        self.log("\n" + "=" * 50)
        self.log("测试5: 下单 (买入开仓)")
        self.log("=" * 50)

        params = {
            "symbol": TEST_SYMBOL,
            "direction": "buy",
            "offset": "open",
            "volume": 1,
            "price": 3500,
            "order_type": "limit",
        }

        result = self.call_api("POST", "/api/execution/order", params=params)

        if result.get("success"):
            self.order_id = result.get("order_id")
            self.log(f"下单成功", "success")
            self.log(f"订单ID: {self.order_id}")
            self.log(f"订单状态: {result.get('status')}")
            self.tests_passed += 1
            return True
        else:
            self.log(f"下单失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_06_get_orders(self) -> bool:
        """测试6: 查询订单"""
        self.log("\n" + "=" * 50)
        self.log("测试6: 查询活跃订单")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/trading/orders/active")

        if isinstance(result, list):
            self.log(f"查询成功，共 {len(result)} 个活跃订单", "success")
            for order in result:
                self.log(f"  - {order.get('order_id')}: {order.get('symbol')} "
                        f"{order.get('direction')} {order.get('volume')}手 "
                        f"@{order.get('price')} [{order.get('status')}]")
            self.tests_passed += 1
            return True
        else:
            self.log("查询订单失败", "error")
            self.tests_failed += 1
            return False

    def test_07_get_positions(self) -> bool:
        """测试7: 查询持仓"""
        self.log("\n" + "=" * 50)
        self.log("测试7: 查询持仓")
        self.log("=" * 50)

        result = self.call_api("GET", "/api/trading/positions/non-flat")

        if isinstance(result, list):
            self.log(f"查询成功，共 {len(result)} 个持仓", "success")
            for pos in result:
                direction = "多" if pos.get('is_long') else "空"
                self.log(f"  - {pos.get('symbol')}: {direction} {pos.get('volume')}手 "
                        f"@¥{pos.get('avg_price', 0):.2f} "
                        f"盈亏: ¥{pos.get('total_pnl', 0):.2f}")
            self.tests_passed += 1
            return True
        else:
            self.log("查询持仓失败", "error")
            self.tests_failed += 1
            return False

    def test_08_close_position(self) -> bool:
        """测试8: 平仓"""
        self.log("\n" + "=" * 50)
        self.log("测试8: 平仓")
        self.log("=" * 50)

        # 先查询持仓
        positions = self.call_api("GET", "/api/trading/positions/non-flat")
        if not positions:
            self.log("没有持仓需要平仓", "warn")
            return True

        # 平仓第一个持仓
        symbol = positions[0].get("symbol")
        result = self.call_api("POST", f"/api/execution/position/{requests.utils.quote(symbol)}/close")

        if result.get("success"):
            self.log(f"平仓指令已发送: {symbol}", "success")
            self.tests_passed += 1
            return True
        else:
            self.log(f"平仓失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_09_cancel_order(self) -> bool:
        """测试9: 撤单"""
        self.log("\n" + "=" * 50)
        self.log("测试9: 撤单")
        self.log("=" * 50)

        # 先查询活跃订单
        orders = self.call_api("GET", "/api/trading/orders/active")
        if not orders:
            self.log("没有活跃订单需要撤销", "warn")
            return True

        # 撤销第一个订单
        order_id = orders[0].get("order_id")
        result = self.call_api("POST", f"/api/execution/order/{order_id}/cancel")

        if result.get("success"):
            self.log(f"撤单成功: {order_id}", "success")
            self.tests_passed += 1
            return True
        else:
            self.log(f"撤单失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_10_emergency_close(self) -> bool:
        """测试10: 紧急平仓"""
        self.log("\n" + "=" * 50)
        self.log("测试10: 紧急平仓")
        self.log("=" * 50)

        result = self.call_api("POST", "/api/execution/emergency-close")

        if result.get("success"):
            self.log("紧急平仓执行成功", "success")
            self.log(f"取消订单数: {result.get('orders_cancelled', 0)}")
            self.log(f"平仓品种数: {result.get('positions_closed', 0)}")
            self.tests_passed += 1
            return True
        else:
            self.log(f"紧急平仓失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def test_11_stop_gateway(self) -> bool:
        """测试11: 停止交易网关"""
        self.log("\n" + "=" * 50)
        self.log("测试11: 停止交易网关")
        self.log("=" * 50)

        result = self.call_api("POST", "/api/execution/stop")

        if result.get("success"):
            self.log("网关停止成功", "success")
            self.tests_passed += 1
            return True
        else:
            self.log(f"网关停止失败: {result.get('error')}", "error")
            self.tests_failed += 1
            return False

    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "=" * 70)
        self.log("开始交易流程测试")
        self.log("=" * 70)

        tests = [
            self.test_01_health_check,
            self.test_02_start_gateway,
            self.test_03_get_status,
            self.test_04_get_account,
            self.test_05_place_order,
            self.test_06_get_orders,
            self.test_07_get_positions,
            self.test_08_close_position,
            self.test_09_cancel_order,
            self.test_10_emergency_close,
            self.test_11_stop_gateway,
        ]

        for test in tests:
            try:
                test()
                time.sleep(0.5)  # 短暂延迟，避免请求过快
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
            self.log("\n所有测试通过！", "success")
            return 0
        else:
            self.log(f"\n有 {self.tests_failed} 个测试失败", "error")
            return 1


def main():
    """主函数"""
    print("期货自动进化因子挖掘系统 - 交易流程测试")
    print("=" * 70)
    print(f"API地址: {BASE_URL}")
    print(f"测试合约: {TEST_SYMBOL}")
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
    tester = TradingFlowTester()
    exit_code = tester.run_all_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
