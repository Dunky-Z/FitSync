#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_manager import ConfigManager
from intervals_icu_client import IntervalsIcuClient

def test_intervals_icu_upload():
    """测试Intervals.icu上传功能"""
    print("=== Intervals.icu上传功能测试 ===\n")
    
    # 初始化配置管理器和客户端
    config_manager = ConfigManager()
    intervals_client = IntervalsIcuClient(config_manager, debug=True)
    
    # 测试连接
    print("1. 测试连接...")
    if not intervals_client.test_connection():
        print("连接测试失败，请检查凭据")
        return False
    
    print("\n2. 查找测试文件...")
    
    # 查找可用的测试文件
    test_files = []
    assets_dir = "assets"
    
    if os.path.exists(assets_dir):
        for file in os.listdir(assets_dir):
            if file.lower().endswith(('.fit', '.tcx', '.gpx')):
                test_files.append(os.path.join(assets_dir, file))
    
    if not test_files:
        print("未找到测试文件，请在assets目录下放置.fit、.tcx或.gpx文件")
        return False
    
    print(f"找到{len(test_files)}个测试文件:")
    for i, file in enumerate(test_files):
        print(f"  {i+1}. {file}")
    
    # 让用户选择要上传的文件
    while True:
        try:
            choice = input(f"\n请选择要上传的文件 (1-{len(test_files)}, 0=取消): ").strip()
            if choice == '0':
                print("测试取消")
                return False
            
            file_index = int(choice) - 1
            if 0 <= file_index < len(test_files):
                selected_file = test_files[file_index]
                break
            else:
                print("选择无效，请重新输入")
        except ValueError:
            print("请输入有效的数字")
    
    print(f"\n3. 上传文件: {selected_file}")
    
    # 准备上传参数
    file_name = os.path.basename(selected_file)
    activity_name = f"测试上传 - {file_name}"
    description = f"这是一个测试上传，文件来源: {file_name}"
    
    try:
        # 执行上传
        result = intervals_client.upload_activity(
            file_path=selected_file,
            name=activity_name,
            description=description,
            external_id=f"test_{file_name}"
        )
        
        print(f"\n4. 上传结果:")
        if result['success']:
            print("  状态: 成功")
            print(f"  活动ID: {result.get('activity_id', 'Unknown')}")
            print(f"  活动名称: {result.get('name', 'Unknown')}")
            if 'url' in result:
                print(f"  查看链接: {result['url']}")
            return True
        else:
            print("  状态: 失败")
            print(f"  错误: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n上传过程中发生异常: {e}")
        return False

def test_get_activities():
    """测试获取活动列表"""
    print("\n=== 获取活动列表测试 ===\n")
    
    config_manager = ConfigManager()
    intervals_client = IntervalsIcuClient(config_manager, debug=True)
    
    try:
        print("获取最近的5个活动...")
        activities = intervals_client.get_activities(limit=5)
        
        if activities:
            print(f"成功获取{len(activities)}个活动:")
            for i, activity in enumerate(activities, 1):
                print(f"  {i}. {activity.get('name', 'Unknown')} - {activity.get('start_date_local', 'Unknown time')}")
        else:
            print("未获取到任何活动")
            
    except Exception as e:
        print(f"获取活动列表失败: {e}")

def main():
    """主函数"""
    print("Intervals.icu客户端测试工具")
    print("="*50)
    
    while True:
        print("\n请选择测试项目:")
        print("1. 测试文件上传")
        print("2. 测试获取活动列表")
        print("3. 测试连接")
        print("0. 退出")
        
        choice = input("\n请输入选择: ").strip()
        
        if choice == '0':
            print("测试结束")
            break
        elif choice == '1':
            test_intervals_icu_upload()
        elif choice == '2':
            test_get_activities()
        elif choice == '3':
            config_manager = ConfigManager()
            intervals_client = IntervalsIcuClient(config_manager, debug=True)
            intervals_client.test_connection()
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    main() 