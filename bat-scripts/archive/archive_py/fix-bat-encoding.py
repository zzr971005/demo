# -*- coding: utf-8 -*-
"""
修复批处理文件编码 - 将所有 .bat 文件转换为 GBK 编码
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def read_file_content(filepath):
    """尝试用不同编码读取文件内容"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            print(f"  使用 {enc} 成功读取")
            return content, enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None, None

def write_file_gbk(filepath, content):
    """将内容写入 GBK 编码的文件"""
    with open(filepath, 'w', encoding='gbk') as f:
        f.write(content)
    print(f"  已保存为 GBK 编码")

def process_bat_files():
    """处理所有 .bat 文件"""
    bat_files = [f for f in os.listdir(SCRIPT_DIR) if f.endswith('.bat')]

    print(f"找到 {len(bat_files)} 个批处理文件")
    print()

    for filename in bat_files:
        filepath = os.path.join(SCRIPT_DIR, filename)
        print(f"处理: {filename}")

        content, source_encoding = read_file_content(filepath)
        if content is None:
            print(f"  [错误] 无法读取文件")
            print()
            continue

        write_file_gbk(filepath, content)
        print()

def test_read():
    """验证 GBK 文件是否能正确读取"""
    print("=" * 60)
    print("验证 GBK 编码文件")
    print("=" * 60)

    for filename in ['启动中心.bat', 'start-dev.bat', 'check-service.bat']:
        filepath = os.path.join(SCRIPT_DIR, filename)
        if not os.path.exists(filepath):
            continue

        print(f"\n{filename}:")
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
            lines = content.split('\n')[:3]
            for line in lines:
                print(f"  {line[:80]}")
            print("  [OK] GBK 读取正常")
        except Exception as e:
            print(f"  [错误] {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("批处理文件编码修复工具")
    print("=" * 60)
    print()

    process_bat_files()

    print()
    print("=" * 60)
    test_read()
    print()
    print("修复完成！")