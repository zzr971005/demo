"""
测试行情数据服务
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/market"


def test_subscribe():
    """测试订阅行情"""
    print("\n=== 测试订阅行情 ===")
    
    symbols = ["KQ.m@SHFE.rb", "KQ.m@SHFE.hc"]
    
    response = requests.post(
        f"{BASE_URL}/subscribe",
        json={"symbols": symbols, "kline_period": 60}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_ticks():
    """测试获取所有Tick"""
    print("\n=== 测试获取所有Tick ===")
    
    response = requests.get(f"{BASE_URL}/ticks")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Tick数量: {len(data)}")
    
    if data:
        print(f"示例数据: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_tick():
    """测试获取单个Tick"""
    print("\n=== 测试获取单个Tick ===")
    
    symbol = "KQ.m@SHFE.rb"
    response = requests.get(f"{BASE_URL}/tick/{symbol}")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_subscribed():
    """测试获取已订阅品种"""
    print("\n=== 测试获取已订阅品种 ===")
    
    response = requests.get(f"{BASE_URL}/subscribed")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_unsubscribe():
    """测试取消订阅"""
    print("\n=== 测试取消订阅 ===")
    
    symbols = ["KQ.m@SHFE.hc"]
    
    response = requests.post(
        f"{BASE_URL}/unsubscribe",
        json=symbols
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_klines():
    """测试获取K线数据"""
    print("\n=== 测试获取K线数据 ===")
    
    symbol = "KQ.m@SHFE.rb"
    response = requests.get(f"{BASE_URL}/klines/{symbol}?n=10")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"K线数量: {len(data)}")
    
    if data:
        print(f"示例数据: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def main():
    """主函数"""
    print("开始测试行情数据服务...")
    
    # 等待服务启动
    time.sleep(1)
    
    try:
        # 测试订阅
        if not test_subscribe():
            print("❌ 订阅测试失败")
            return
        print("✅ 订阅测试通过")
        
        # 等待数据更新
        time.sleep(2)
        
        # 测试获取已订阅品种
        if not test_get_subscribed():
            print("❌ 获取已订阅品种测试失败")
            return
        print("✅ 获取已订阅品种测试通过")
        
        # 测试获取所有Tick
        if not test_get_ticks():
            print("❌ 获取所有Tick测试失败")
            return
        print("✅ 获取所有Tick测试通过")
        
        # 测试获取单个Tick
        if not test_get_tick():
            print("❌ 获取单个Tick测试失败")
            return
        print("✅ 获取单个Tick测试通过")
        
        # 测试获取K线
        if not test_get_klines():
            print("❌ 获取K线测试失败")
            return
        print("✅ 获取K线测试通过")
        
        # 测试取消订阅
        if not test_unsubscribe():
            print("❌ 取消订阅测试失败")
            return
        print("✅ 取消订阅测试通过")
        
        print("\n🎉 所有测试通过!")
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
