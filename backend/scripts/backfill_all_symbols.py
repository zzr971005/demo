"""
批量补齐各品种候选（收盘可跑——仅用历史 K 线，不需要实时撮合）。

对每个规格品种跑一轮有界进化（有限代数 + 停滞早停），产出候选并落库到
Candidate 表。已有候选的品种默认跳过（可用 --force 重跑）。

用法：
    cd backend && PYTHONPATH=$PWD poetry run python scripts/backfill_all_symbols.py \
        [--generations 12] [--population 100] [--symbols RB,MA] [--force]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.db import get_session  # noqa: E402
from app.models import Candidate  # noqa: E402
from quant_engine.data.hub import DataPipeline, TimescaleHub  # noqa: E402
from quant_engine.data.unified_hub import DataHub  # noqa: E402
from quant_engine.ops.evolution_center import (  # noqa: E402
    EvolutionCenter,
    EvolutionTaskConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("backfill")

# 12 个规格品种
SPEC_SYMBOLS = ["RB", "MA", "TA", "FG", "SR", "SA", "CU", "AU", "M", "PP", "SC", "IF"]

# 每手吨数/乘数（近似；只影响 PnL 量纲，不改变同品种内因子相对排序）
CONTRACT_MULT = {
    "RB": 10, "MA": 10, "TA": 5, "FG": 20, "SR": 10, "SA": 20,
    "CU": 5, "AU": 1000, "M": 10, "PP": 5, "SC": 1000, "IF": 300,
}


def existing_symbols() -> set:
    with get_session() as s:
        rows = s.execute(
            select(Candidate.symbol).where(Candidate.formula.isnot(None)).distinct()
        ).scalars().all()
    return set(rows)


def candidate_count(symbol: str) -> int:
    with get_session() as s:
        return s.execute(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.symbol == symbol)
        ).scalar() or 0


def clear_candidates(symbol: str) -> int:
    """删除该品种的 SEED 候选（重跑前清场，避免旧的退化/雷同候选残留）。"""
    from app.models import CandidateStatus
    with get_session() as s:
        rows = s.query(Candidate).filter(
            Candidate.symbol == symbol,
            Candidate.status == CandidateStatus.SEED,
        ).all()
        n = len(rows)
        for r in rows:
            s.delete(r)
        s.commit()
    return n


def _fp(sh, tr, t, wr) -> tuple:
    return (round(float(sh or 0), 4), round(float(tr or 0), 4),
            int(t or 0), round(float(wr or 0), 4))


def dedup_fingerprints(symbol: str) -> int:
    """最终绩效指纹去重：同一指纹只保留 sharpe_train 最高的一个。

    兜底机制——进化过程中的逐代去重会因指标截断/跨保存调用边界而漏掉少量
    "不同表达式、表现完全相同"的雷同因子；此处对已落库结果做一次性彻底去重。
    """
    from app.models import CandidateStatus
    removed = 0
    with get_session() as s:
        rows = s.query(Candidate).filter(
            Candidate.symbol == symbol,
            Candidate.status == CandidateStatus.SEED,
        ).all()
        best: dict = {}
        for c in rows:
            key = _fp(c.sharpe_train, c.total_return, c.total_trades, c.win_rate)
            keep = best.get(key)
            if keep is None or (c.sharpe_train or 0) > (keep.sharpe_train or 0):
                if keep is not None:
                    s.delete(keep)
                    removed += 1
                best[key] = c
            else:
                s.delete(c)
                removed += 1
        s.commit()
    if removed:
        logger.info("[指纹去重] %s 删除雷同因子 %d 个，剩余唯一 %d 个", symbol, removed, len(best))
    return removed


def ensure_history(symbol: str, years: int) -> None:
    """Fix 1：从天勤下载更长历史(默认5年)并入库（收盘可下载历史K线）。

    insert_ohlcv 走 ON CONFLICT DO UPDATE，重复下载幂等、不产生重复行。
    """
    from app.config import get_settings
    from quant_engine.data.source import TqDataSource

    settings = get_settings()
    th = TimescaleHub()
    before = th.get_record_count(symbol, 3600)
    tq = TqDataSource(
        account=settings.tqsdk_account,
        password=settings.tqsdk_password,
        sim=True,
    )
    pipeline = DataPipeline(timescale_hub=th, tq_data_source=tq)
    end_dt = pd.Timestamp.now()
    start_dt = end_dt - pd.Timedelta(days=365 * years + 10)
    try:
        pipeline.download_and_save(
            symbol=symbol,
            start_dt=start_dt,
            end_dt=end_dt,
            duration_seconds=3600,
            use_cache=False,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("%s 历史下载失败(沿用库内已有数据): %s", symbol, e)
    finally:
        import contextlib
        with contextlib.suppress(Exception):
            tq.close()  # 关闭天勤连接，避免 asyncio 事件循环关闭时的清理告警
    after = th.get_record_count(symbol, 3600)
    mn, mx = th.get_available_range(symbol, 3600)
    logger.info("[历史] %s 1H bars %d -> %d，范围 %s .. %s", symbol, before, after, mn, mx)


def run_symbol(symbol: str, generations: int, population: int, data_hub: DataHub) -> None:
    before = candidate_count(symbol)
    config = EvolutionTaskConfig(
        task_id=f"{symbol}_backfill_{int(time.time())}",
        symbol=symbol,
        description=f"{symbol} 批量补齐",
        population_size=population,
        max_generations=generations,
        max_stagnation=5,  # 早停（>0，避免无限进化）
        enable_overfitting_check=True,
        pbo_threshold=0.3,
        dsr_threshold=0.6,
        wfe_threshold=0.7,
        init_capital=1_000_000,
        position_size_pct=0.95,
        contract_value_per_lot=50000,
        contract_multiplier=CONTRACT_MULT.get(symbol, 10),
        save_top_n=20,
        save_path="./output/factors",
    )
    center = EvolutionCenter(config, data_hub=data_hub)
    t0 = time.time()
    logger.info("==== 开始进化 %s（代数<=%d, 种群=%d）====", symbol, generations, population)
    center.run_evolution()
    after = candidate_count(symbol)
    logger.info(
        "==== 完成 %s：候选 %d -> %d（+%d），耗时 %.1fs ====",
        symbol, before, after, after - before, time.time() - t0,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--symbols", type=str, default="")
    parser.add_argument("--force", action="store_true",
                        help="对已有候选的品种也重跑")
    parser.add_argument("--clear", action="store_true",
                        help="重跑前删除该品种已有 SEED 候选（清场）")
    parser.add_argument("--history-years", type=int, default=5,
                        help="Fix 1：补齐前下载的历史年数(0=跳过下载)")
    args = parser.parse_args()

    if args.symbols:
        targets = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        targets = list(SPEC_SYMBOLS)

    have = existing_symbols()
    if not args.force and not args.clear:
        skip = [s for s in targets if s in have]
        targets = [s for s in targets if s not in have]
        if skip:
            logger.info("跳过已有候选的品种: %s（如需重跑加 --force/--clear）", ",".join(skip))

    if not targets:
        logger.info("没有需要补齐的品种。")
        return

    logger.info("待补齐品种: %s", ",".join(targets))
    data_hub = DataHub()
    logger.info("DataHub 初始化完成")

    ok, failed = [], []
    for sym in targets:
        try:
            if args.history_years > 0:
                ensure_history(sym, args.history_years)
            if args.clear:
                n = clear_candidates(sym)
                logger.info("[清场] %s 删除旧 SEED 候选 %d 个", sym, n)
            run_symbol(sym, args.generations, args.population, data_hub)
            dedup_fingerprints(sym)
            ok.append(sym)
        except Exception as e:  # noqa: BLE001
            logger.error("品种 %s 进化失败: %s", sym, e, exc_info=True)
            failed.append(sym)

    logger.info("全部完成。成功: %s  失败: %s", ",".join(ok) or "-", ",".join(failed) or "-")


if __name__ == "__main__":
    main()
