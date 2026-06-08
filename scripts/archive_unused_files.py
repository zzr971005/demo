# -*- coding: utf-8 -*-
"""Scan project for unused files and move them to archive."""
import os
import shutil
from pathlib import Path

project_root = Path(r'd:\期货自动进化因子挖掘系统')
archive_dir = project_root / '_ARCHIVE_UNUSED_FILES'

# Files/directories to archive
unused_items = [
    # Frontend temporary scripts
    'frontend/fix_array.py',
    'frontend/fix_array_safety.py',
    'frontend/fix_map_safety.py',
    'frontend/check_imports.py',
    
    # Backend temporary verification scripts
    'backend/scripts/verify_nav.py',
    'backend/scripts/verify_nav2.py',
    
    # Backend test files in root
    'backend/test_baseline_api.py',
    'backend/test_baseline_data.py',
    'backend/test_cleanup.py',
    'backend/test_pnl_fix.py',
    
    # Temporary documentation
    'test-report.md',
    '修复报告_数据更新模块.md',
    '旧系统用途.md',
    'backend/整理方案.md',
    
    # Cache directories
    'backend/.pytest_cache',
    'backend/__pycache__',
    'frontend/node_modules',
    'frontend/dist',
    
    # Empty directories
    'logs',
    'data',
    '网友开发记录',
    
    # IDE configs
    '.trae',
    
    # Backup data
    'data_backup',
    
    # Archive zip
    'tqsdk-skills.zip',
    
    # Query file (unknown purpose)
    'query',
]

print('Creating archive directory...')
archive_dir.mkdir(exist_ok=True)

moved_count = 0
for item_path in unused_items:
    src = project_root / item_path
    if not src.exists():
        print(f'SKIP (not found): {item_path}')
        continue
    
    dst = archive_dir / item_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    if src.is_dir():
        shutil.move(str(src), str(dst))
        print(f'MOVED DIR: {item_path}')
    else:
        shutil.move(str(src), str(dst))
        print(f'MOVED FILE: {item_path}')
    moved_count += 1

print(f'\nTotal items moved to archive: {moved_count}')
print(f'Archive location: {archive_dir}')
