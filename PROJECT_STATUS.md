# 项目状态 (PROJECT STATUS)

> 给本地 AI 接手用的现状快照。仓库: https://github.com/zzr971005/demo PR #1 (分支 `devin/1780928158-import-project`)

## 1. 项目目标
期货自动进化因子挖掘 + 多因子策略系统:12 品种独立 DEAP 遗传编程挖因子 → 组合成低相关多因子策略 → 每品种跑模拟盘 → 选 top2 低相关策略可转实盘。支持单品种/跨品种、HRP/IC_IR 组合权重、策略相关度矩阵。保留"未来一键切实盘",当前仅模拟盘(TQSDK_SIM=true)。

12 品种: RB MA TA FG SR SA(CZCE/SHFE) CU AU(SHFE) M PP(DCE) SC(INE) IF(CFFEX)。

## 2. 技术栈 / 运行
- 后端 FastAPI(:8000) + Poetry(py3.11) + PostgreSQL/TimescaleDB + Redis + SQLite(进化因子库)
- 前端 Vite + React/TS(:5173)
- 行情/交易: 天勤 TQSDK(凭据在 `backend/.env`: TQSDK_ACCOUNT/PASSWORD/SIM)
- 本地起步: `cd backend && poetry install` → 起 PG/Redis → `poetry run uvicorn app.main:app`;`cd frontend && npm install && npm run dev`

## 3. 已完成
- **导入+整理**: 目录规整、README/.gitignore 重写、poetry.lock 入库。
- **静默 bug 大批修复**(都在 PR #1): TQSDK 导入错误(曾静默退回 mock)、42 张表建不出、~18 个 500 接口(get_session 误用/枚举缺失/模型列不存在/路由顺序)、DSL float window 让 numba 崩。
- **消除样本内泄漏**: 因子归一化/阈值改为只用训练集(扩张窗口)拟合,不再用全样本分位。
- **前视偏差**: 向量化回测 + 天勤交叉验证统一改 T-1(用上一根因子值成交)。
- **交易时段时区**: 服务器 UTC → 北京时区(修复"开盘被判休市/逐合约下载被跳过/期限结构退化")。
- **多因子策略全流程 PR-A..E**:
  - 策略×策略实时相关度矩阵 API + 前端"策略相关度"Tab(热力图/高相关对/收益雷同告警)
  - 每品种 top2 低相关选择器(质量分+DSR>0 硬门槛) + paper→live 6 道硬门控
  - IC_IR 加权 + HRP(López de Prado) 组合权重
  - 跨品种 A(一套因子广播多品种) + B(多品种多因子加权)
- **退化因子过滤 + 绩效指纹去重**(防"不同表达式表现完全相同"静默错误): 拒绝裸常数/不引用数据列/零交易因子;按(夏普/收益/交易数/胜率)指纹去重;并修了一个让 DB 级指纹比对静默失效的作用域 bug;落库后再加一道兜底去重。
- **历史窗口拉长**: 补齐前从天勤下载 ~5 年历史(从 ~2 年/3357根 增到 ~8453根, 2021-06~2026-06)。

## 4. 当前候选库状态(云端 DB,不在 git)
已验证: **0 裸常数 / 0 零交易 / 每品种候选数==不同绩效指纹数(无雷同重复)**。
计数随重跑参数变化(代数/种群越大越多);本会话用代数50/种群200 重跑后:RB 18 · CU 19 · TA 34 · FG 19 · AU 19 · PP 10 · M 9 · SC 4 · IF 4 · SR 4 · MA 7 · SA 8(经方法1/2救活)。薄品种已不再≈0。
> 注意:候选数据只在云端 DB,**git 里只有代码**。本地需自行跑(建议高参数):
> `cd backend && poetry run python scripts/backfill_all_symbols.py --clear --history-years 5 --generations 50 --population 200`

## 5. 已知问题 / 下一步
1. **薄品种有效因子曾≈0**(SA/MA),已用第6节方法1(门槛分级)+方法2(跨品种热启动)救活(MA 7 / SA 8)。后续若要更高质量,见第6节"后续方法"(多次重跑合并/自适应阈值/多周期原语)。
2. **盘中端到端实跑未做**: 真实模拟盘撮合下单闭环、期限结构表(`ohlcv_term_*`)实时入库需盘中。
3. **季节性因子缺失**: DSL 无日历原语(月份/年内相位/距换月天数),无法挖"固定月份趋势"类 alpha;若做需加日历原语 + 按年留一交叉验证防过拟合。
4. **pyproject.toml 的 GPU torch 是 Windows nightly 链接且已 404**: `-E gpu/full` 安装会失败,普通 install 不受影响,本地需换可用 wheel。

## 6. 增加"有效因子少"品种的有效因子 —— 已做的实验 + 后续方法
"有效个体" = 适应度(扣费+T-1后)>0 的个体。

### 已验证的实验(本会话)
- **加大搜索预算**(代数50/种群200,0 改代码): RB 1→18、CU 3→19。结论:对"本就有 alpha"的品种,之前少是搜索不足,堆算力即可解决。
- **但 SA/MA 堆算力无效**(仍≈0),且 4 品种历史一样厚(~5年),→ 它们瓶颈不是数据/算力,而是当前"分位阈值信号+扣费+T-1"下扣费后还赚钱的因子稀少。
- **方法1 门槛分级(已实现)**: 见 `gp_evolution.select_parents`(过线父代不足时按评分保留 top2 当父代,而非随机)+ `evolution_center` 保存端(过线不足时兜底保留 top-K probation 半成品,config `min_keep_top_k` 默认5)。效果: MA 0→7、SA 1→8,且**真进化出正夏普因子**(MA 1.40 / SA 0.87)。对 RB/CU 等达标品种无影响。
- **方法2 跨品种 SEED 热启动(已实现)**: `evolution_center._load_seeds_from_database` 同品种种子不足时,补入其它品种的优质因子(夏普>0.5)作为起始基因,在本品种数据上重新评分(无前视/泄漏)。
- **probation 质量护栏(已实现)**: probation 只收交易数≥`probation_min_trades`(默认10)的半成品,剔除"几笔交易高夏普"的过拟合假象。

### 这些方法对各品种的适用性(重要)
- **方法1/2/护栏都是全局代码,已对 12 品种自动生效,无需"按品种再加"**。区别只在触发与收益:
  - 方法1门槛分级 + probation护栏:**只在"过线个体<5"时触发**。RB/CU/TA 等达标品种不会触发 → 对它们无影响(不变好也不变差),仅作薄品种安全网。
  - 方法2跨品种热启动:**对所有品种都可能触发**(同品种种子<20 时)。富品种可能略有提升(起点更高、收敛更快),但边际有限、无坏处(种子在本品种数据重新评分,无前视/泄漏)。
- **副作用需盯防**:跨品种热启动若让多品种从同几个"通用因子"出发,可能使**不同品种因子趋同、相关度升高**,与"低相关多因子组合"目标冲突。缓冲有指纹去重+变异+重新评分;建议在"策略相关度矩阵"里观察,若跨品种相关度普遍偏高就调低跨品种种子比例。
- **想让富品种更好,更对路的杠杆是下面的"多次重跑合并"与"自适应阈值/多周期原语",而非方法1/2**。
- 可做的对照实验(本地):挑富品种(如 TA),对比开/关跨品种热启动的「因子数 / 最高夏普 / 跨品种相关度」,用数据决定富品种是否值得用方法2。

### 后续可继续提质的方法
1. **多次独立重跑后合并**: 不同随机种子各跑几轮,合并去重(指纹去重已就位)——RB 当初的 328 就是这么累积的。**这是扩充富品种优质池最有效的办法**。
2. **自适应阈值**: 现统一分位阈值可能让 MA/SA 大量个体"几乎不交易/全程同方向";改按因子自适应阈值。
3. **多周期/多因子原语**: 引入更多算子与 D1/H1/5min 多周期特征,扩大可表达空间。
4. **(进阶)季节性原语**: 对农产品/建材类补日历因子(月份/年内相位/距换月天数),按年留一交叉验证防过拟合,扩充正交 alpha。

## 7. 关键文件
- 进化核心: `backend/quant_engine/ops/evolution_center.py`(含退化过滤/指纹去重 `_reject_candidate`/`_load_existing_fingerprints`)
- GP: `backend/quant_engine/ops/gp_evolution.py`(有效个体/门槛分级父代 `select_parents`)、`gp_fitness.py`(适应度/min_trades/阈值)
- 种子热启动: `evolution_center._load_seeds_from_database`(同品种 + 跨品种热启动)
- 批量补齐脚本: `backend/scripts/backfill_all_symbols.py`(--history-years/--clear/最终指纹去重)
- 多因子/组合: `quant_engine/ops/{combo_search,combo_search_prune,combo_tune,strategy_selector,cross_symbol}.py`、`quant_engine/analysis/{strategy_correlation,portfolio_optimizer}.py`
- 相关度 API/前端: `app/api/routes/analysis/strategy_correlation.py` + 前端"相关性分析→策略相关度"Tab
- 规格(完成标准): `.devin/specs/auto-evolve-factor-mining/`

## 8. 下载到本地 / 复现
代码都在 PR #1,分支 `devin/1780928158-import-project`(https://github.com/zzr971005/demo/pull/1)。

**方式A(推荐,合并后用 main):**
1. 在 GitHub 打开 PR #1 点 **Merge**(合并到 main)。
2. 本地全新克隆: `git clone https://github.com/zzr971005/demo.git`(或已有仓库 `git pull`)。

**方式B(不合并,直接拿分支):**
```
git fetch origin
git checkout devin/1780928158-import-project
```

**拿到代码后本地启动(候选数据需本地重新生成):**
1. 后端依赖: `cd backend && poetry install`
2. 起 PostgreSQL/TimescaleDB + Redis(本地或 docker)。
3. 配 `backend/.env`:填 `TQSDK_ACCOUNT / TQSDK_PASSWORD / TQSDK_SIM=true` 及数据库连接(`.env.example` 有模板)。
4. **获取候选库**(二选一):
   - **(快,推荐)直接导入云端已挖好的 201 个候选**(随仓库附带 `backend/seed_data/seed_candidates.json`):
     ```
     cd backend
     poetry run python scripts/import_candidates.py            # 幂等 upsert
     # poetry run python scripts/import_candidates.py --replace  # 先清空同品种再导入
     ```
   - **(慢,本地自挖)从天勤下载 ~5 年历史并对 12 品种重新挖因子**(收盘也能跑,只有实时模拟盘撮合需盘中):
     ```
     cd backend
     poetry run python scripts/backfill_all_symbols.py --clear --history-years 5 --generations 50 --population 200
     ```
5. 起后端: `poetry run uvicorn app.main:app --port 8000`
6. 起前端: `cd frontend && npm install && npm run dev`(默认 :5173)
7. 打开前端 →「相关性分析 → 策略相关度」Tab 查看每品种 Top2 / 组合权重 / 跨品种 / 相关度矩阵。

> 注意:`.env`(天勤账号)与 `backend/output/`(生成数据)按 .gitignore 不入库,你本地这些文件原样保留、不受影响。GPU torch 见第5节第4点(普通 install 不受影响)。
