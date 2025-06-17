#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Garmin会话保存功能
"""

import os
import sys

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)


from config_manager import ConfigManager
from garmin_client import GarminClient

def test_garmin_session():
    """测试Garmin会话功能"""
    print("测试Garmin会话保存功能")
    print("=" * 50)
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    garmin_config = config_manager.get_platform_config("garmin")
    
    # 检查是否有保存的凭据
    username = garmin_config.get("username", "")
    password = garmin_config.get("password", "")
    auth_domain = garmin_config.get("auth_domain", "GLOBAL")
    
    if not username or not password:
        print("未找到保存的Garmin凭据")
        print("请先运行主程序并保存登录信息")
        return
    
    print(f"使用保存的凭据: {username}")
    print(f"认证域: {auth_domain}")
    
    try:
        # 创建Garmin客户端（会自动尝试恢复会话）
        print("\n创建Garmin客户端...")
        client = GarminClient(username, password, auth_domain, config_manager)
        
        # 测试连接
        print("\n测试连接...")
        activities = client.getActivities(start=0, limit=1)
        
        if activities:
            print(f"连接成功！获取到{len(activities)}个活动")
            if activities:
                activity = activities[0]
                print(f"最新活动: {activity.get('activityName', '未命名')}")
                print(f"活动时间: {activity.get('startTimeLocal', 'N/A')}")
        else:
            print("连接成功，但未获取到活动")
        
        # 检查会话数据
        session_data = client._get_session_data()
        if session_data:
            print(f"\n会话数据已保存到配置文件")
            print(f"会话数据大小: {len(str(session_data))} 字符")
        else:
            print("\n警告: 会话数据未找到")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        print("可能的原因:")
        print("1. 网络连接问题")
        print("2. 登录凭据已过期")
        print("3. Garmin服务器问题")
        
        # 提供清除会话的选项
        import questionary
        clear_session = questionary.confirm(
            "是否清除会话数据重新开始?",
            default=False
        ).ask()
        
        if clear_session:
            try:
                client = GarminClient(username, password, auth_domain, config_manager)
                client.clear_session()
                print("会话已清除")
            except:
                print("清除会话失败")

if __name__ == "__main__":
    test_garmin_session() 