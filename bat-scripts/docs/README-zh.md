# 🚀 启动脚本使用指南 - 中文版

> 📅 更新日期: 2025-05-16
> 📦 版本: v2.0 增强版

## 📁 文件结构

```
bat-scripts/
├── start-dev.bat          # 基础开发模式
├── start-dev-pro.bat      # 增强版开发模式 ⭐推荐
├── start-backend-only.bat # 仅启动后端
├── start-frontend-only.bat # 仅启动前端
├── start.bat               # 完整启动模式
├── start.ps1               # PowerShell 菜单版
├── init-data.bat           # 数据初始化（下载历史K线）
├── stop-all.bat            # 停止所有服务
├── restart-all.bat         # 一键重启
├── check-status.bat        # 检查服务状态
├── clean-ports.bat         # 清理端口占用
├── start-frontend.bat      # 前端单独启动
├── README.md               # 英文说明
└── README-zh.md            # 本文档
```

---

## 🌟 快速开始

### 🎯 推荐方式：增强版开发模式

**双击运行** `start-dev-pro.bat` 或：

```powershell
.\bat-scripts\start-dev-pro.bat
```

**功能特点：**
- ✅ 自动检测并安装缺失依赖
- ✅ 智能检测已有服务状态
- ✅ 支持只启动缺失的服务
- ✅ 彩色输出，友好提示
- ✅ 自动清理端口占用

### ⚡ 三步骤完整启动

**第一次使用：**

1. **配置天勤账号**（必须）
   ```bash
   # 编辑 backend/.env 文件
   TQSDK_ACCOUNT=你的天勤账号
   TQSDK_PASSWORD=你的天勤密码
   ```

2. **启动基础设施**
   ```powershell
   .\bat-scripts\start-dev-pro.bat
   # 选择 [2] 仅启动基础设施
   ```

3. **下载历史数据**（重要）
   ```powershell
   .\bat-scripts\init-data.bat
   # 选择 [1] 增量更新
   ```

4. **启动完整服务**
   ```powershell
   .\bat-scripts\start-dev-pro.bat
   # 选择 [1] 全部启动
   ```

---

## 📋 脚本详细说明

### 🛠️ 开发模式脚本

| 脚本 | 说明 | 适用场景 |
|------|------|---------|
| `start-dev-pro.bat` | **增强版开发模式** - 智能检测、彩色输出、多选项 | 日常开发 ⭐推荐 |
| `start-dev.bat` | 基础开发模式 - 一键启动所有服务 | 快速启动 |
| `start-backend-only.bat` | 仅启动后端 + 基础设施 | 后端开发、API 调试 |
| `start-frontend-only.bat` | 仅启动前端 | 前端开发、UI 调试 |

### 🏭 完整启动模式

| 脚本 | 说明 |
|------|------|
| `start.bat` | 全服务启动菜单 |
| `start.ps1` | PowerShell 版本（支持中文输出） |

### 🔧 工具脚本

| 脚本 | 说明 | 常用场景 |
|------|------|---------|
| `init-data.bat` | 数据初始化 - 下载历史K线 | 首次使用、数据更新 |
| `check-status.bat` | 检查所有服务状态 | 调试、排错 |
| `stop-all.bat` | 停止所有服务 + 清理端口 | 开发结束、重启前 |
| `restart-all.bat` | 一键重启（停止 + 清理 + 启动） | 服务异常、代码更新后 |
| `clean-ports.bat` | 清理开发常用端口 | 端口冲突时使用 |

---

## 🔄 完整工作流

### 每日开发流程

```
早上:
├── check-status.bat    # 检查服务状态
├── start-dev-pro.bat   # 智能启动缺失服务
└── init-data.bat       # [可选] 增量更新数据

开发中:
├── 修改代码自动热重载
├── 后端: http://localhost:8000/docs
└── 前端: http://localhost:5173

结束:
└── stop-all.bat        # 停止所有服务
```

### 首次使用完整流程

```
1. 安装本地服务
   ├── 安装 PostgreSQL 17
   └── 安装 Redis

2. 配置天勤账号
   └── 编辑 backend/.env，填入真实账号密码

3. 启动基础设施
   └── start-dev-pro.bat → 选择 [2]

4. 下载历史数据
   └── init-data.bat → 选择 [1] 增量更新

5. 启动完整开发环境
   └── start-dev-pro.bat → 选择 [1] 或 [5]
```

---

## 📊 数据初始化详解

### `init-data.bat` 数据下载工具

**功能：**
- ✅ 下载 8 个主力品种的 1小时 和 日线 数据
- ✅ 支持增量更新（从上次结束时间继续）
- ✅ 支持全量覆盖
- ✅ 支持数据状态检查
- ✅ 支持扩展品种（黄金、铜、原油、股指）

**选项说明：**

| 选项 | 功能 | 适用场景 |
|------|------|---------|
| `[1]` 增量更新 | 仅下载新数据 | 日常更新 |
| `[2]` 全量初始化 | 覆盖已有数据 | 首次使用、数据损坏 |
| `[3]` 仅检查状态 | 查看各品种数据范围 | 检查数据完整性 |
| `[4]` 下载扩展品种 | AU/CU/SC/IF | 资金充足后 |

**包含品种：**

| 组别 | 品种代码 | 品种名称 | 保证金估算 |
|------|---------|---------|-----------|
| 首批 | RB | 螺纹钢 | ~4000 |
| 首批 | MA | 甲醇 | ~3000 |
| 首批 | M | 豆粕 | ~3500 |
| 首批 | TA | PTA | ~3500 |
| 首批 | FG | 玻璃 | ~4000 |
| 首批 | SR | 白糖 | ~4500 |
| 首批 | SA | 纯碱 | ~4000 |
| 首批 | PP | 聚丙烯 | ~4000 |
| 扩展 | AU | 黄金 | ~65000 |
| 扩展 | CU | 铜 | ~45000 |
| 扩展 | SC | 原油 | ~55000 |
| 扩展 | IF | 沪深300 | ~140000 |

---

## 🌐 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端界面** | http://localhost:5173 | React + Vite 开发服务器 |
| **后端 API** | http://localhost:8000 | FastAPI 接口服务 |
| **API 文档** | http://localhost:8000/docs | Swagger 在线文档 |
| **健康检查** | http://localhost:8000/health | 服务状态检查 |
| **数据库** | localhost:5432 | TimescaleDB/PostgreSQL |
| **缓存** | localhost:6379 | Redis |

---

## 🔍 状态检查详解

### `check-status.bat` 检查项

```
[1/5] Docker 状态
[2/5] TimescaleDB 容器 + 端口 5432
[3/5] Redis 容器 + 端口 6379
[4/5] 后端服务 端口 8000 + 健康检查
[5/5] 前端服务 端口 5173
```

**状态说明：**
- `[OK]` 绿色：服务正常运行
- `[WARN]` 黄色：警告，需要关注
- `[ERR]` 红色：错误，需要处理
- `[INFO]` 蓝色：信息提示

---

## ⚠️ 常见问题解决

### ❌ 端口被占用

**症状：** 启动时提示端口已被占用

**解决：**
```powershell
# 方法 1：一键清理
.\bat-scripts\clean-ports.bat

# 方法 2：手动查找并终止
netstat -ano | findstr "8000"
taskkill /F /PID <进程ID>
```

### ❌ Docker 未启动

**症状：** 提示 Docker not found

**解决：**
1. 启动 Docker Desktop
2. 等待 Docker 完全启动（状态栏鲸鱼图标停止转动）
3. 重新运行脚本

### ❌ Poetry 虚拟环境找不到

**症状：** 提示 Python 虚拟环境未找到

**解决：**
```powershell
cd backend
poetry install
```

### ❌ node_modules 不存在

**症状：** 前端启动失败

**解决：**
```powershell
cd frontend
npm install
```

### ❌ 天勤数据下载失败

**症状：** 数据下载为空或报错

**检查：**
1. `backend/.env` 中账号密码是否正确
2. 天勤账号是否有权限
3. 网络连接是否正常
4. 是否有防火墙拦截

### ❌ 数据库连接失败

**症状：** 健康检查失败，数据库无法连接

**解决：**
```powershell
# 检查容器状态
docker-compose ps

# 重启容器
docker-compose restart timescaledb

# 查看日志
docker-compose logs timescaledb
```

---

## 💡 开发小技巧

### 1. 热重载/热更新

**后端：**
- 代码修改后自动重载
- 无需手动重启
- 日志窗口显示更新信息

**前端：**
- 组件修改热模块替换（HMR）
- 状态保留
- UI 秒级刷新

### 2. 独立窗口调试

- 后端窗口：查看 API 请求日志
- 前端窗口：查看构建日志、热更新状态

### 3. 快速切换模式

```powershell
# 需要调试后端
stop-all.bat → start-backend-only.bat

# 需要调试前端
stop-all.bat → start-frontend-only.bat

# 代码大更新后
restart-all.bat
```

---

## 📝 编码说明

### 💻 批处理文件编码

所有 `.bat` 文件使用 **GBK (936)** 编码以确保在 Windows 中文版中正确显示中文。

**如遇乱码：**
1. 确保文件保存为 ANSI/GBK 编码
2. 或使用 PowerShell 版本（`start.ps1`）

### 🎨 颜色输出说明

| 颜色 | 含义 |
|------|------|
| 绿色 | 成功、正常、推荐 |
| 黄色 | 警告、提示、信息 |
| 红色 | 错误、失败 |
| 青色 | 标题、进度 |

---

## 🔄 服务生命周期

### 启动顺序
```
1. Docker 基础设施
   ├── TimescaleDB (端口 5432)
   └── Redis (端口 6379)
          ↓
2. 后端服务 (端口 8000)
   └── 依赖数据库就绪
          ↓
3. 前端服务 (端口 5173)
   └── 依赖后端就绪
```

### 停止顺序
```
1. 停止后端服务 (端口 8000)
2. 停止前端服务 (端口 5173)
3. 停止 Docker 容器
4. 清理残留端口占用
```

---

## 📞 获取帮助

### 查看服务日志
```powershell
# Docker 容器日志
docker-compose logs -f timescaledb
docker-compose logs -f redis

# 后端/前端日志
# 查看对应的 cmd 窗口
```

### 查看帮助脚本
```powershell
# 检查服务状态
.\bat-scripts\check-status.bat
```

---

## 🎯 版本历史

### v2.0 (2025-05-16)
- ✅ 新增 `start-dev-pro.bat` - 增强版开发模式
- ✅ 新增数据初始化脚本（含8个品种+扩展品种）
- ✅ 新增状态检查工具
- ✅ 新增端口清理工具
- ✅ 新增一键重启脚本
- ✅ 新增仅后端/仅前端模式
- ✅ 智能服务状态检测
- ✅ 彩色输出、友好提示
- ✅ 自动清理端口占用

### v1.0
- ✅ 基础 Docker 启动脚本
- ✅ 基础开发模式脚本

---

**祝开发顺利！** 🎉

> 💡 **提示：** 建议将 `bat-scripts` 添加到文件资源管理器快速访问，这样可以一键启动。
