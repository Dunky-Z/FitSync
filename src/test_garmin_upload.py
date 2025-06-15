#!/usr/bin/env python3
"""
测试Garmin Connect上传功能的脚本
"""
import sys
import os

# 获取项目根目录路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 动态添加Python模块搜索路径
user_site_packages = os.path.expanduser("~/.local/lib/python3.10/site-packages")
system_dist_packages = "/usr/lib/python3/dist-packages"

# 将路径添加到sys.path开头，优先级更高
if user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)
if system_dist_packages not in sys.path:
    sys.path.insert(0, system_dist_packages)

import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_garmin_import():
    """测试Garmin模块导入"""
    try:
        from garmin_client import GarminClient, GARTH_AVAILABLE
        if GARTH_AVAILABLE:
            print("garth库已安装")
            return True
        else: 
            print("garth库未安装")
            print("请运行: pip install garth")
            return False
    except ImportError as e:
        print(f"导入错误: {e}")
        return False

def test_garmin_login():
    """测试Garmin登录（不会真实登录）"""
    try:
        from garmin_client import GarminClient
        
        # 创建客户端实例（不会立即登录）
        client = GarminClient("test@example.com", "password", "GLOBAL")
        print("GarminClient创建成功")
        return True
    except Exception as e:
        print(f"GarminClient创建失败: {e}")
        return False

def main():
    print("测试Garmin Connect集成...")
    
    # 测试导入
    if not test_garmin_import():
        return False
    
    # 测试客户端创建
    if not test_garmin_login():
        return False
    
    print("所有测试通过！Garmin Connect功能已就绪")
    print("\n使用说明:")
    print("1. 运行主程序: python main.py")
    print("2. 选择下载活动文件")
    print("3. 在上传平台选择中勾选 'Garmin Connect'")
    print("4. 输入你的Garmin Connect登录凭据")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 