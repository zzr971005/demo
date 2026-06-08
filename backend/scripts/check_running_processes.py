"""检查是否有进化进程在运行"""
import psutil
import time

def check_evolution_processes():
    """检查是否有进化进程在运行"""
    print("=== 检查运行中的Python进程 ===")
    
    found = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline:
                    cmdline_str = ' '.join(cmdline)
                    if 'evolution' in cmdline_str.lower() or 'evolve' in cmdline_str.lower():
                        print(f"\nPID: {proc.info['pid']}")
                        print(f"命令: {cmdline_str}")
                        print(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.info['create_time']))}")
                        found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if not found:
        print("没有找到运行中的进化进程")
    
    return found

if __name__ == "__main__":
    check_evolution_processes()
