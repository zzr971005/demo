#!/usr/bin/env python3
"""统一脚本入口"""

import sys
import os
import subprocess

def show_usage():
    print("用法:")
    print("  python scripts/run.py cleanup <script_name>")
    print("  python scripts/run.py migration <script_name>")
    print("  python scripts/run.py testing <script_name>")
    print("  python scripts/run.py debugging <script_name>")
    print("  python scripts/run.py maintenance <script_name>")
    print("")
    print("可用脚本:")
    print("  cleanup: clean_all_data.py, clean_data_simple.py, clear_and_restart.py")
    print("  migration: migrate_add_candidate_fields.py, migrate_sqlite_to_postgres.py")
    print("  testing: test_signal_consistency.py, test_evolution_flow.py")
    print("  debugging: debug_gp.py, debug_single_factor.py")
    print("  maintenance: check_data.py, init_db.py, fix_candidates.py")

def list_scripts(category):
    """列出指定类别的脚本"""
    script_dir = f"{category}"
    if not os.path.exists(script_dir):
        print(f"类别 {category} 不存在")
        return
    
    scripts = [f for f in os.listdir(script_dir) if f.endswith('.py')]
    if scripts:
        print(f"{category} 类别下的脚本:")
        for script in sorted(scripts):
            print(f"  - {script}")
    else:
        print(f"{category} 类别下没有脚本")

def run_script(category, script_name):
    """运行指定脚本"""
    script_path = f"{category}/{script_name}"
    
    if not script_name.endswith('.py'):
        script_path += '.py'
    
    if not os.path.exists(script_path):
        print(f"脚本不存在: {script_path}")
        list_scripts(category)
        return
    
    print(f"运行脚本: {script_path}")
    try:
        # 使用subprocess运行脚本，这样可以传递参数
        result = subprocess.run([sys.executable, script_path] + sys.argv[3:], 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        return result.returncode
    except Exception as e:
        print(f"运行脚本失败: {e}")
        return 1

def main():
    if len(sys.argv) < 2:
        show_usage()
        return 1
    
    command = sys.argv[1]
    
    if command == "help" or command == "--help" or command == "-h":
        show_usage()
        return 0
    
    if command == "list":
        if len(sys.argv) < 3:
            print("可用类别: cleanup, migration, testing, debugging, maintenance")
            for category in ["cleanup", "migration", "testing", "debugging", "maintenance"]:
                list_scripts(category)
        else:
            list_scripts(sys.argv[2])
        return 0
    
    if len(sys.argv) < 3:
        print(f"请指定脚本名称")
        list_scripts(command)
        return 1
    
    category = sys.argv[1]
    script_name = sys.argv[2]
    
    # 验证类别
    valid_categories = ["cleanup", "migration", "testing", "debugging", "maintenance"]
    if category not in valid_categories:
        print(f"无效类别: {category}")
        print(f"有效类别: {', '.join(valid_categories)}")
        return 1
    
    return run_script(category, script_name)

if __name__ == "__main__":
    sys.exit(main())
