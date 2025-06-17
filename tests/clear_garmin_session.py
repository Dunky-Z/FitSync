#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清除Garmin会话数据的工具
"""

import os
import sys

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)

from config_manager import ConfigManager

def clear_garmin_session():
    """清除Garmin会话数据"""
    print("清除Garmin会话数据工具")
    print("=" * 40)
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager()
        garmin_config = config_manager.get_platform_config("garmin")
        
        # 检查是否有会话数据
        session_data = garmin_config.get("session_data", {})
        
        if not session_data:
            print("未找到需要清除的会话数据")
            return
        
        # 显示会话信息
        saved_email = session_data.get("email", "未知")
        saved_domain = session_data.get("auth_domain", "未知")
        
        print(f"找到会话数据:")
        print(f"  - 用户: {saved_email}")
        print(f"  - 域名: {saved_domain}")
        print(f"  - 数据大小: {len(str(session_data))} 字符")
        
        # 确认清除
        confirm = input("\n是否确认清除会话数据? (y/N): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            # 清除会话数据
            del garmin_config["session_data"]
            config_manager.save_platform_config("garmin", garmin_config)
            
            print("会话数据已清除")
            print("下次登录时将需要重新认证")
        else:
            print("操作已取消")
            
    except Exception as e:
        print(f"清除会话数据失败: {e}")

if __name__ == "__main__":
    clear_garmin_session() 