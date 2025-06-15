#!/usr/bin/env python3
"""
测试运行脚本
便捷地运行项目中的所有测试
"""

import os
import sys
import subprocess
import argparse

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=False, text=True)
        print(f"✅ {description} - 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失败 (退出码: {e.returncode})")
        return False

def main():
    parser = argparse.ArgumentParser(description='运行项目测试')
    parser.add_argument('--test', choices=[
        'all', 'sync', 'migration', 'main', 'quick'
    ], default='all', help='选择要运行的测试')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='显示详细输出')
    
    args = parser.parse_args()
    
    # 确保在项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    print("🚀 Strava-Garmin双向同步项目测试套件")
    print(f"📁 项目目录: {project_root}")
    print(f"🎯 测试类型: {args.test}")
    
    success_count = 0
    total_count = 0
    
    if args.test in ['all', 'quick', 'sync']:
        total_count += 1
        if run_command("python tests/test_sync.py", "双向同步功能测试"):
            success_count += 1
    
    if args.test in ['all', 'migration']:
        total_count += 1
        if run_command("python tests/test_database_migration.py", "数据库迁移测试"):
            success_count += 1
    
    if args.test in ['all', 'main']:
        total_count += 1
        if run_command("python tests/test_main.py", "主要功能测试"):
            success_count += 1
    
    # 显示测试结果摘要
    print(f"\n{'='*60}")
    print("📊 测试结果摘要")
    print('='*60)
    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查上面的错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 