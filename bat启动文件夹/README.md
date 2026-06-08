# 期货自动进化因子挖掘系统 - 启动中心

## 快速开始

**推荐使用方式：双击运行 `启动中心_增强版.bat`**

这是最简单、最完整的启动方式，包含所有功能选项。

## 文件说明

### 核心启动文件（必需）
- `启动中心_增强版.bat` - **主启动中心**（推荐使用）
  - 基础开发模式
  - 增强版开发模式（GPU检测）
  - 基础设施启动
  - 后端/前端单独启动
  - 数据初始化
  - 端口清理
  - GPU加速设置

### 功能脚本（被启动中心调用）
- `start-dev.bat` - 基础开发模式（PostgreSQL + Redis + Backend + Frontend）
- `start-dev-pro.bat` - 增强版开发模式（分离模式：API + Evolution + Frontend）
- `start-backend-only.bat` - 仅启动后端
- `start-frontend-only.bat` - 仅启动前端
- `start-evolution-only.bat` - 仅启动进化引擎
- `init-data.bat` - 数据初始化
- `check-service.bat` - 服务状态检查
- `check-db-status.bat` - 数据库状态检查
- `restart-all.bat` - 重启所有服务
- `stop-all.bat` - 停止所有服务
- `clean-ports.bat` - 清理端口占用

### 文档
- `docs/README-zh.md` - 中文使用说明
- `docs/README.md` - 英文使用说明
- `docs/增强版启动中心使用说明.md` - 增强版详细说明
- `docs/批处理文件编码规范.md` - 批处理文件规范
- `docs/数据库安全启动说明.md` - 数据库启动说明
- `docs/文件清单.md` - 文件清单

### 存档
- `archive/archive_bat/` - 旧版或废弃的批处理文件
- `archive/` - 其他存档文件

## 端口配置

- **后端 API**: 8000
- **前端**: 5173
- **PostgreSQL**: 5432
- **Redis**: 6379

## 使用建议

1. **首次使用**：
   - 运行 `启动中心_增强版.bat`
   - 选择 [3] 仅启动基础设施
   - 选择 [6] 数据初始化
   - 选择 [1] 或 [2] 启动开发模式

2. **日常开发**：
   - 直接运行 `启动中心_增强版.bat`
   - 选择 [1] 基础开发模式 或 [2] 增强版开发模式

3. **GPU加速**：
   - 在增强版开发模式中，使用选项 [15] 安装 PyTorch Nightly
   - 适用于 RTX 5070 Ti 等新架构显卡

## 访问地址

启动成功后访问：
- 前端界面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 故障排除

如果遇到端口占用问题：
1. 运行 `启动中心_增强版.bat`
2. 选择 [14] 清理端口占用
3. 重新启动服务

如果服务无法启动：
1. 选择 [7] 检查服务状态
2. 选择 [8] 检查数据库状态
3. 查看错误信息并参考文档
