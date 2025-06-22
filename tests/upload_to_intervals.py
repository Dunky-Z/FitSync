#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_manager import ConfigManager
from intervals_icu_client import IntervalsIcuClient

def upload_file_to_intervals(file_path: str, name: str = None, description: str = None):
    """上传文件到Intervals.icu"""
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    # 检查文件格式
    supported_formats = ['.fit', '.tcx', '.gpx']
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext not in supported_formats:
        print(f"错误: 不支持的文件格式 {file_ext}")
        print(f"支持的格式: {', '.join(supported_formats)}")
        return False
    
    print(f"准备上传文件: {file_path}")
    print(f"文件大小: {os.path.getsize(file_path)} bytes")
    print(f"文件格式: {file_ext}")
    
    try:
        # 初始化配置管理器和客户端
        config_manager = ConfigManager()
        intervals_client = IntervalsIcuClient(config_manager, debug=True)
        
        # 准备上传参数
        if not name:
            name = os.path.splitext(os.path.basename(file_path))[0]
        
        if not description:
            description = f"通过同步工具上传 - {os.path.basename(file_path)}"
        
        print(f"\n活动名称: {name}")
        print(f"活动描述: {description}")
        
        # 执行上传
        print("\n开始上传...")
        result = intervals_client.upload_activity(
            file_path=file_path,
            name=name,
            description=description,
            external_id=f"upload_{os.path.basename(file_path)}"
        )
        
        # 显示结果
        print("\n" + "="*50)
        print("上传结果:")
        print("="*50)
        
        if result['success']:
            print("状态: 成功")
            print(f"活动ID: {result.get('activity_id', 'Unknown')}")
            print(f"活动名称: {result.get('name', 'Unknown')}")
            if 'url' in result:
                print(f"查看链接: {result['url']}")
            print("\n上传完成!")
            return True
        else:
            print("状态: 失败")
            print(f"错误信息: {result.get('error', 'Unknown error')}")
            if 'status_code' in result:
                print(f"HTTP状态码: {result['status_code']}")
            return False
            
    except Exception as e:
        print(f"\n上传过程中发生异常: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='上传运动文件到Intervals.icu')
    parser.add_argument('file_path', help='要上传的文件路径')
    parser.add_argument('--name', '-n', help='活动名称')
    parser.add_argument('--description', '-d', help='活动描述')
    parser.add_argument('--test-connection', action='store_true', help='仅测试连接')
    
    args = parser.parse_args()
    
    print("Intervals.icu文件上传工具")
    print("="*50)
    
    # 如果只是测试连接
    if args.test_connection:
        config_manager = ConfigManager()
        intervals_client = IntervalsIcuClient(config_manager, debug=True)
        
        print("测试Intervals.icu连接...")
        if intervals_client.test_connection():
            print("连接测试成功!")
            return
        else:
            print("连接测试失败!")
            return
    
    # 上传文件
    success = upload_file_to_intervals(
        file_path=args.file_path,
        name=args.name,
        description=args.description
    )
    
    if success:
        print("\n文件上传成功!")
        sys.exit(0)
    else:
        print("\n文件上传失败!")
        sys.exit(1)

if __name__ == "__main__":
    main() 