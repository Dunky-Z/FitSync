#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Garth会话保存机制
"""

import os
import sys
import tempfile
import json

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)

from config_manager import ConfigManager
import garth

def debug_garth_session():
    """调试Garth会话保存机制"""
    print("调试Garth会话保存机制")
    print("=" * 50)
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    garmin_config = config_manager.get_platform_config("garmin")
    
    # 获取凭据
    username = garmin_config.get("username", "")
    password = garmin_config.get("password", "")
    auth_domain = garmin_config.get("auth_domain", "GLOBAL")
    
    if not username or not password:
        print("未找到保存的Garmin凭据")
        return
    
    print(f"使用凭据: {username}")
    print(f"认证域: {auth_domain}")
    
    try:
        # 配置garth域名
        if auth_domain and str(auth_domain).upper() == "CN":
            target_domain = "garmin.cn"
        else:
            target_domain = "garmin.com"
        
        print(f"配置域名: {target_domain}")
        garth.configure(domain=target_domain)
        
        # 登录
        print("正在登录...")
        garth.login(username, password)
        print("登录成功！")
        
        # 创建临时目录保存会话
        temp_dir = tempfile.mkdtemp(prefix="debug_garth_")
        print(f"临时目录: {temp_dir}")
        
        # 保存会话
        print("保存会话...")
        garth.save(temp_dir)
        
        # 检查保存的文件
        print("检查保存的文件:")
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, temp_dir)
                file_size = os.path.getsize(file_path)
                print(f"  - {relative_path} ({file_size} bytes)")
                
                # 如果是JSON文件，显示内容结构
                if file.endswith('.json'):
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        print(f"    结构: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
                    except:
                        print("    无法解析JSON")
        
        # 测试恢复会话
        print("\n测试会话恢复...")
        
        # 创建新的临时目录用于恢复测试
        resume_dir = tempfile.mkdtemp(prefix="debug_resume_")
        
        # 复制会话文件
        import shutil
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                src_path = os.path.join(root, file)
                relative_path = os.path.relpath(src_path, temp_dir)
                dst_path = os.path.join(resume_dir, relative_path)
                
                # 创建目录
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
        
        # 重新配置garth（清除当前状态）
        garth.configure(domain=target_domain)
        
        # 尝试恢复
        try:
            garth.resume(resume_dir)
            print("会话恢复成功！")
            print(f"恢复后用户名: {garth.client.username}")
        except Exception as resume_e:
            print(f"会话恢复失败: {resume_e}")
        
        # 清理
        try:
            shutil.rmtree(temp_dir)
            shutil.rmtree(resume_dir)
        except:
            pass
            
    except Exception as e:
        print(f"调试失败: {e}")

if __name__ == "__main__":
    debug_garth_session() 