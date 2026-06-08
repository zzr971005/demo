from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from quant_engine.ops.websocket_manager import get_ws_manager, MessageType, WebSocketMessage
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# SQLAlchemy 引擎日志默认设为 WARNING，避免 Backend API 窗口被正常 SQL 查询刷屏
# 如需 debug 数据库操作，设置环境变量 DEBUG_SQL=1
sql_log_level = logging.DEBUG if os.environ.get("DEBUG_SQL", "0") == "1" else logging.WARNING
logging.getLogger("sqlalchemy.engine").setLevel(sql_log_level)
logging.getLogger("sqlalchemy.pool").setLevel(sql_log_level)
# 保持 sqlalchemy.engine.base.Engine 的日志级别也一致
for name in ["sqlalchemy.engine.base.Engine", "sqlalchemy.engine.Engine"]:
    logging.getLogger(name).setLevel(sql_log_level)


from app.api.routes import (
    analysis,
    data,
    evolution,
    risk,
    strategy,
    system,
    trading,
)
from app.config import get_settings
from app.db import check_health as check_db_health
from app.redis_client import check_redis_health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    active_connections: List[WebSocket] = []
    app.state.active_connections = active_connections
    app.state.settings = settings

    print(f"[{settings.app_name}] Starting...")
    print(f"  Database: {settings.database_url.split('@')[-1]}")
    print(f"  Redis: {settings.redis_url}")
    print(f"  Symbols: {len(settings.system.symbols.all_symbols)}")

    # 初始化数据库（创建 evolution_tasks 等新表）
    try:
        from app.db import init_db
        init_db()
        print("  数据库表已初始化（含 evolution_tasks）")
    except Exception as e:
        print(f"  [WARN] 数据库初始化失败: {e}")

    # 预热进化线程池（lazy 启动也行，但提前启动可减少首次提交延迟）
    # 默认禁用进化线程池，只在用户手动启动时启用
    # 若设置 ENABLE_EVOLUTION_POOL=1，则启用进化池初始化
    if os.environ.get("ENABLE_EVOLUTION_POOL", "0") == "1":
        print("  [INFO] ENABLE_EVOLUTION_POOL=1，启用进化线程池初始化")
        try:
            from quant_engine.ops.evolution_pool import (
                get_evolution_pool,
                heartbeat_monitor_loop,
                set_evolution_pool_instance,
            )
            pool = get_evolution_pool()
            set_evolution_pool_instance(pool)  # 设置全局实例供心跳监控使用
            print(f"  进化线程池已就绪 max_workers={pool._max_workers}")

            # 启动心跳监控后台任务
            monitor_task = asyncio.create_task(
                heartbeat_monitor_loop(interval_seconds=5, timeout_seconds=120)
            )
            app.state.heartbeat_monitor = monitor_task
            print("  心跳监控已启动")
        except Exception as e:
            print(f"  [WARN] 进化线程池初始化失败: {e}")
            app.state.heartbeat_monitor = None
    else:
        print("  [INFO] 进化线程池已禁用（默认模式，需要手动启动）")
        app.state.heartbeat_monitor = None

    # 初始化策略轮换调度器（默认禁用，避免自动启动）
    if os.environ.get("ENABLE_SCHEDULER", "0") == "1":
        try:
            from quant_engine.ops.evolution_scheduler import EvolutionScheduler
            from quant_engine.ops.strategy_rotation_scheduler import StrategyRotationTask

            scheduler = EvolutionScheduler()
            app.state.scheduler = scheduler

            # 注册策略轮换任务（每14天触发）
            rotation_task = StrategyRotationTask(
                task_id="strategy_rotation",
                interval_days=14,
                enabled=True
            )
            scheduler.register_task(rotation_task, callback=lambda task: rotation_task.execute())
            print("  策略轮换调度器已注册（每14天）")

            # 启动调度器（异步启动）
            asyncio.create_task(scheduler.start())
            print("  调度器已启动")
        except Exception as e:
            print(f"  [WARN] 调度器初始化失败: {e}")
            app.state.scheduler = None
    else:
        print("  [INFO] 调度器已禁用（默认模式）")
        app.state.scheduler = None

    # 初始化TQSDK交易引擎（如果配置了凭证）
    try:
        from quant_engine.ops.tqsdk_trading import init_trading_engine, TradingMode
        if settings.tqsdk_account and settings.tqsdk_password:
            mode = TradingMode.PAPER if settings.tqsdk_sim else TradingMode.LIVE
            success = init_trading_engine(
                mode=mode,
                account_id=settings.tqsdk_account,
                password=settings.tqsdk_password
            )
            if success:
                print(f"  TQSDK交易引擎已初始化（模式: {mode.value}）")
            else:
                print(f"  [WARN] TQSDK交易引擎初始化失败")
        else:
            print("  [INFO] 未配置TQSDK凭证，交易引擎未初始化")
    except Exception as e:
        print(f"  [WARN] TQSDK交易引擎初始化失败: {e}")

    yield

    print(f"[{settings.app_name}] Shutdown...")

    # 关闭调度器
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        try:
            scheduler.stop()
            print("  调度器已停止")
        except Exception as e:
            print(f"  [WARN] 关闭调度器失败: {e}")

    # 关闭心跳监控
    monitor_task = getattr(app.state, "heartbeat_monitor", None)
    if monitor_task is not None:
        monitor_task.cancel()
        try:
            await monitor_task
        except (asyncio.CancelledError, Exception):
            pass

    # 关闭进化线程池（不等待，让 worker 线程被强制终止）
    try:
        from quant_engine.ops.evolution_pool import EvolutionThreadPool
        if EvolutionThreadPool._instance is not None:
            EvolutionThreadPool._instance.shutdown(wait=False)
            print("  进化线程池已关闭")
    except Exception as e:
        print(f"  [WARN] 关闭进化线程池失败: {e}")

    # 关闭TQSDK交易引擎
    try:
        from quant_engine.ops.tqsdk_trading import shutdown_trading_engine
        shutdown_trading_engine()
        print("  TQSDK交易引擎已关闭")
    except Exception as e:
        print(f"  [WARN] 关闭TQSDK交易引擎失败: {e}")

    for ws in list(active_connections):
        try:
            await ws.close()
        except Exception:
            pass
    active_connections.clear()


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "Internal server error",
                "detail": str(exc) if settings.debug else None,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": 400,
                "message": "Invalid request parameters",
                "detail": str(exc),
            },
        )

    # Evolution routes
    app.include_router(evolution.evolution.router, prefix="/api")
    app.include_router(evolution.evolution_cycles.router, prefix="/api")
    app.include_router(evolution.candidates.router, prefix="/api")
    app.include_router(evolution.factors.router, prefix="/api")
    app.include_router(evolution.factors_realtime.router, prefix="/api")
    app.include_router(evolution.joint_evolution.router, prefix="/api/evolution")
    app.include_router(evolution.generalization.router, prefix="/api/evolution")
    app.include_router(evolution.classification.router, prefix="/api/evolution")

    # Strategy routes
    app.include_router(strategy.evaluation.router, prefix="/api")
    app.include_router(strategy.management.router)  # Has prefix in router
    app.include_router(strategy.monitor.router)
    app.include_router(strategy.replacement.router, prefix="/api")
    app.include_router(strategy.switch.router)

    # Trading routes
    app.include_router(trading.trading.router, prefix="/api")
    app.include_router(trading.execution.router, prefix="/api")
    app.include_router(trading.simulation.router)
    app.include_router(trading.trades.router, prefix="/api")
    app.include_router(trading.live_trading.router, prefix="/api")
    app.include_router(trading.live_transition.router)
    app.include_router(trading.order_types.router)
    app.include_router(trading.transaction_cost.router)  # Has prefix /api/transaction-cost
    app.include_router(trading.position_reconciliation.router, prefix="/api")
    app.include_router(trading.replay_engine.router)
    app.include_router(trading.report_generation.router)

    # Risk routes
    app.include_router(risk.risk.router, prefix="/api")
    app.include_router(risk.risk_management.router)
    app.include_router(risk.capital.router)
    app.include_router(risk.liquidity.router)
    app.include_router(risk.position.router)
    app.include_router(risk.alerts.router)

    # Data routes
    app.include_router(data.cache.router, prefix="/api")  # Has prefix /cache, so becomes /api/cache
    app.include_router(data.integrity.router, prefix="/api")
    app.include_router(data.quality.router)
    app.include_router(data.market.router, prefix="/api")

    # Analysis routes
    app.include_router(analysis.baseline.router, prefix="/api")
    app.include_router(analysis.correlation.router)
    app.include_router(analysis.microstructure.router)
    app.include_router(analysis.portfolio.router)
    app.include_router(analysis.backtest_live_comparison.router)  # Has prefix /api/backtest-live-comparison
    app.include_router(analysis.ab_testing.router)
    app.include_router(analysis.anomaly_detection.router)
    app.include_router(analysis.cross_market_trading.router)

    # System routes
    app.include_router(system.dashboard.router, prefix="/api")
    app.include_router(system.symbols.router, prefix="/api")
    app.include_router(system.scheduler.router, prefix="/api")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        ws_manager = get_ws_manager()
        
        # 首先接受 WebSocket 连接
        await websocket.accept()
        
        # 确保管理器已启动
        if not ws_manager._running:
            await ws_manager.start()
        
        client_id = f"client_{id(websocket)}"
        client = ws_manager.register_client(client_id, websocket)
        
        try:
            # 发送欢迎消息
            welcome_msg = WebSocketMessage(
                message_type=MessageType.SYSTEM,
                payload={
                    "message": "Connected successfully",
                    "client_id": client_id
                }
            )
            await client.send(welcome_msg)
            
            # 处理客户端消息
            while True:
                data = await websocket.receive_text()
                try:
                    import json
                    msg_data = json.loads(data)
                    msg_type = msg_data.get("type")
                    
                    if msg_type == "ping":
                        pong_msg = WebSocketMessage(
                            message_type=MessageType.PONG,
                            payload={"timestamp": msg_data.get("timestamp")},
                            broadcast=False,
                            client_id=client_id
                        )
                        await ws_manager.queue_message(pong_msg)
                    elif msg_type == "subscribe":
                        channel = msg_data.get("channel")
                        if channel:
                            ws_manager.subscribe_to_channel(client_id, channel)
                    elif msg_type == "unsubscribe":
                        channel = msg_data.get("channel")
                        if channel:
                            ws_manager.unsubscribe_from_channel(client_id, channel)
                except json.JSONDecodeError:
                    pass
                    
        except WebSocketDisconnect:
            ws_manager.unregister_client(client_id)
        except Exception as e:
            ws_manager.unregister_client(client_id)

    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        from app.db import get_pool_status
        db_healthy = check_db_health()
        redis_healthy = check_redis_health()
        
        all_healthy = db_healthy and redis_healthy
        status_str = "healthy" if all_healthy else "degraded"
        
        return {
            "status": status_str,
            "version": settings.app_version,
            "services": {
                "database": db_healthy,
                "redis": redis_healthy,
            },
            "db_pool": get_pool_status() if db_healthy else None,
        }

    @app.get("/")
    async def root() -> Dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    return app


app = create_application()
