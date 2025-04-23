#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库文档更新助手脚本
用途：检查数据库模型文件的变更，提醒开发者更新数据库文档
使用：在git commit前执行此脚本，或设置为git hook
"""

import os
import sys
import datetime
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
# 模型目录
MODELS_DIR = PROJECT_ROOT / "app" / "models"
# 数据库文档路径
DB_DOC_PATH = PROJECT_ROOT / "docs" / "database" / "database_structure.md"

# 获取git中最近修改过的模型文件
def get_modified_model_files():
    try:
        # 获取git中已修改但未提交的文件
        cmd = "git diff --name-only --cached"
        modified_files = subprocess.check_output(cmd, shell=True).decode('utf-8').split("\n")
        
        # 过滤出模型文件
        model_files = [f for f in modified_files if f.startswith("app/models/") and f.endswith(".py")]
        return model_files
    except Exception as e:
        print(f"获取修改文件失败: {e}")
        return []

# 检查数据库文档更新时间
def check_doc_update_needed():
    modified_models = get_modified_model_files()
    
    if not modified_models:
        print("没有检测到数据库模型文件的修改。")
        return False
    
    if not DB_DOC_PATH.exists():
        print(f"警告: 数据库文档不存在，请创建文档 {DB_DOC_PATH}")
        return True
    
    doc_update_time = datetime.datetime.fromtimestamp(DB_DOC_PATH.stat().st_mtime)
    current_time = datetime.datetime.now()
    
    # 检查文档是否在24小时内更新过
    if (current_time - doc_update_time).days > 0:
        print("警告: 数据库文档可能需要更新！")
        print("修改的模型文件:")
        for model_file in modified_models:
            print(f"  - {model_file}")
        print(f"\n请更新数据库文档: {DB_DOC_PATH}")
        return True
    
    return False

# 更新文档的更新记录部分
def update_doc_changelog():
    if not DB_DOC_PATH.exists():
        print(f"错误: 无法更新文档，文件不存在: {DB_DOC_PATH}")
        return
    
    # 读取文档内容
    with open(DB_DOC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找更新记录部分
    update_section = "## 更新记录"
    if update_section not in content:
        print(f"错误: 文档中找不到'{update_section}'部分")
        return
    
    # 获取当前日期
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    username = os.environ.get('USER', '未知用户')
    
    # 添加新的更新记录
    changelog_entry = f"| {today} | v1.x | 更新数据库结构文档 | {username} |\n"
    
    # 分割内容
    parts = content.split(update_section)
    header = parts[0] + update_section + "\n\n"
    
    # 查找表格头
    table_header = "| 日期 | 版本 | 更新内容 | 更新人 |\n|------|------|----------|--------|"
    if table_header in parts[1]:
        rest = parts[1].split(table_header)
        table_content = table_header + "\n" + changelog_entry + rest[1]
    else:
        table_content = table_header + "\n" + changelog_entry + parts[1]
    
    # 更新文档
    with open(DB_DOC_PATH, 'w', encoding='utf-8') as f:
        f.write(header + table_content)
    
    print(f"已更新文档 {DB_DOC_PATH} 的更新记录")

def main():
    # 检查是否需要更新文档
    update_needed = check_doc_update_needed()
    
    if update_needed:
        response = input("是否自动更新文档的更新记录？(y/n): ")
        if response.lower() == 'y':
            update_doc_changelog()
        else:
            print("请手动更新数据库文档")

if __name__ == "__main__":
    main() 