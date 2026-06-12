"""导入云端导出的候选因子到本地数据库。

用途：把 Devin 在云端挖出的候选因子（公式 + 夏普/收益/交易数等指标）一次性导入
本地 Postgres，免去本地重跑数小时 backfill。数据文件默认 backend/seed_data/seed_candidates.json。

用法：
    cd backend
    poetry run python scripts/import_candidates.py                  # 导入默认文件
    poetry run python scripts/import_candidates.py --file path.json # 指定文件
    poetry run python scripts/import_candidates.py --replace        # 先清空同品种再导入

按主键 id upsert（session.merge），重复导入幂等、不产生重复行。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from app.db import get_session  # noqa: E402
from app.models import Candidate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FILE = Path(__file__).resolve().parents[1] / "seed_data" / "seed_candidates.json"


def _coerce(rows: list[dict]) -> list[dict]:
    """按模型列类型做最小类型还原（主要是 DateTime 字段从字符串解析回时间）。"""
    mapper = inspect(Candidate).mapper
    dt_cols = {c.key for c in mapper.column_attrs if c.columns[0].type.__class__.__name__ in ("DateTime", "Date")}
    valid_cols = {c.key for c in mapper.column_attrs}
    out = []
    for r in rows:
        d = {k: v for k, v in r.items() if k in valid_cols}
        for c in dt_cols:
            if d.get(c) in (None, "", "None"):
                d[c] = None
            else:
                try:
                    d[c] = pd.to_datetime(d[c]).to_pydatetime()
                except Exception:
                    d[c] = None
        out.append(d)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_FILE), help="候选因子 JSON 文件路径")
    ap.add_argument("--replace", action="store_true", help="导入前先清空文件中涉及的品种")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"找不到数据文件: {path}")

    rows = _coerce(json.loads(path.read_text(encoding="utf-8")))
    symbols = sorted({r.get("symbol") for r in rows if r.get("symbol")})
    logger.info("待导入 %d 个候选，覆盖品种: %s", len(rows), symbols)

    with get_session() as s:
        if args.replace:
            deleted = s.query(Candidate).filter(Candidate.symbol.in_(symbols)).delete(synchronize_session=False)
            logger.info("[替换] 已删除同品种旧候选 %d 个", deleted)
        for d in rows:
            s.merge(Candidate(**d))
        s.commit()
    logger.info("导入完成：%d 个候选已写入数据库", len(rows))


if __name__ == "__main__":
    main()
