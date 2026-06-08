"""启动RB进化任务并监控"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import requests
import time
from datetime import datetime

print("=== 启动RB进化任务 ===")

# 检查是否有运行中的任务
try:
    response = requests.get("http://localhost:8000/api/evolution/tasks")
    tasks = response.json()
    print(f"当前任务: {tasks}")
    
    rb_running = any(t.get("symbol") == "RB" and t.get("status") in ["PENDING", "RUNNING"] for t in tasks)
    
    if rb_running:
        print("RB任务已在运行中")
    else:
        # 启动RB任务
        print("启动RB进化任务...")
        response = requests.post("http://localhost:8000/api/evolution/start", json={"symbols": ["RB"]})
        print(f"启动结果: {response.json()}")
except Exception as e:
    print(f"API调用失败: {e}")

print("\n等待60秒...")
for i in range(60):
    time.sleep(1)
    if i % 10 == 0:
        print(f"已等待 {i} 秒")

print("\n=== 检查candidates表内容 ===")

from app.models import Candidate
from app.db import get_session
from sqlalchemy import select, desc

with get_session() as session:
    # 查询RB的所有因子
    stmt = select(Candidate).where(Candidate.symbol == "RB").order_by(desc(Candidate.created_at))
    candidates = session.execute(stmt).scalars().all()
    
    print(f"RB因子总数: {len(candidates)}")
    
    if candidates:
        print("\n最新的10个因子:")
        for i, c in enumerate(candidates[:10]):
            print(f"\n{i+1}. ID: {c.id}")
            print(f"   公式: {c.formula}")
            print(f"   状态: {c.status}")
            print(f"   世代: {c.generation}")
            print(f"   Sharpe: {c.sharpe_train}")
            print(f"   Calmar: {c.calmar}")
            print(f"   Max Drawdown: {c.max_drawdown}")
            print(f"   Total Return: {c.total_return}")
            print(f"   Total Trades: {c.total_trades}")
            print(f"   Win Rate: {c.win_rate}")
            print(f"   创建时间: {c.created_at}")
    else:
        print("candidates表中没有RB因子")

print("\n=== 完成 ===")
