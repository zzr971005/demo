# 期货自动进化因子挖掘系统 — 规则总览

## 规则文件

| 文件 | 说明 | 优先级 |
|------|------|--------|
| [project-management.md](./project-management.md) | **开发进度管理规则（每次任务前必读）** | **P0** |
| [core-rules.md](./core-rules.md) | 核心规则：数据真实性、TQSDK使用、代码质量、风控、因子挖掘、保证金规则 | P0 |
| [architecture-deployment.md](./architecture-deployment.md) | 服务架构、数据库管理、回测一致性规则 | P1 |

## 关键规则速查

### 开发前必读

```
每次任务前必须阅读 docs/specs/v1.0-working.md
每次任务前必须阅读 docs/development-logs/INDEX.md
进展记录必须新建md文件，禁止修改旧文件
```

### 核心规则

```
1. 禁止虚假数据 - 必须来自TQSDK
2. TQSDK初始化后才能操作
3. 保证金用 broker_margin
4. 时序纪律：进化只能用T-1及以前数据
5. 实盘前模拟>=2周，PBO<0.3, DSR>0.6
6. 单品种回撤>10%自动降级，单日亏损>5%熔断
7. IF禁止CLOSE_TODAY
8. 主力合约换月前5天停止新开仓
```

## 优先级说明

- **P0**: 必须遵守，违反将导致代码不通过、功能回滚、实盘权限暂停
- **P1**: 重要规范，影响开发效率和代码质量

---

## 开发文档快速链接

| 文档 | 路径 | 用途 |
|------|------|------|
| **工作规格书** | `docs/specs/v1.0-working.md` | 当前开发参考，包含需求和进度 |
| **进展索引** | `docs/development-logs/INDEX.md` | 开发进展记录索引 |
| **文档中心** | `docs/README.md` | 项目文档总览 |
| **规格书变更** | `docs/specs/CHANGELOG.md` | 规格书变更历史 |

---

**最后更新：2026-05-28**
