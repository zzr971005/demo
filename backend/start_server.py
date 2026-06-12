"""启动脚本 - 在 backend 目录内运行"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # 运行启动检查
    try:
        from app.startup_checks import run_startup_checks_with_fallback
        print("🔍 执行启动前检查...")
        if not run_startup_checks_with_fallback():
            print("❌ 启动检查失败，程序退出")
            sys.exit(1)
        print("✅ 启动检查通过")
    except ImportError as e:
        print(f"⚠️  无法导入启动检查模块: {e}")
        print("继续启动服务器...")
    except Exception as e:
        print(f"⚠️  启动检查异常: {e}")
        print("继续启动服务器...")
    
    # 启动服务器
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
