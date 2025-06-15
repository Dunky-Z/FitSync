import sys
import os
import time
import logging
import argparse
from typing import Optional

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

from dotenv import load_dotenv

# 导入重构后的模块
from config_manager import ConfigManager
from file_utils import FileUtils
from ui_utils import UIUtils
from platform_manager import PlatformManager

load_dotenv()
logger = logging.getLogger()
DEBUG = False  # 全局调试标志

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('logs.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def debug_print(message: str) -> None:
    """只在调试模式下打印信息"""
    if DEBUG:
        print(message)


def get_file_path(platform_manager: PlatformManager) -> Optional[str]:
    """获取文件路径，通过下载或用户提供"""
    file_location = UIUtils.ask_file_location()

    if file_location == "从Strava下载":
        # 选择活动来源
        activity_source = UIUtils.ask_activity_source()
        
        strava_client = platform_manager.get_strava_client()
        
        if activity_source == "从Strava API获取最新活动":
            activity_id, activity_name = strava_client.select_activity_from_api()
        else:
            activity_id = UIUtils.ask_activity_id()
            activity_name = None
            
        logger.info("Selected activity ID: %s, Name: %s", activity_id, activity_name)
        print("正在从Strava下载文件...")
        
        downloaded_file = strava_client.download_file(activity_id, activity_name)

        # 如果返回了下载文件路径，直接使用
        if downloaded_file:
            debug_print(f"使用下载的文件: {downloaded_file}")
            return downloaded_file
        else:
            time.sleep(3)
            latest_file = FileUtils.get_latest_download()
            if latest_file:
                debug_print(f"自动检测到下载的文件: {latest_file}")
                if UIUtils.confirm_use_latest_file(os.path.basename(latest_file)):
                    return latest_file
                else:
                    return UIUtils.ask_file_path("检查文件是否已下载并验证文件:")
            else:
                print("在Downloads文件夹中未找到活动文件")
                return UIUtils.ask_file_path("请手动选择文件:")
    else:
        return UIUtils.ask_file_path()


def main():
    global DEBUG
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='多平台运动数据同步工具')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    args = parser.parse_args()
    
    DEBUG = args.debug
    
    if DEBUG:
        print("调试模式已启用")
    
    try:
        # 初始化配置管理器和平台管理器
        config_manager = ConfigManager()
        platform_manager = PlatformManager(config_manager, DEBUG)
        
        # 获取文件路径
        file_path = get_file_path(platform_manager)
        
        if not file_path:
            logger.error("未提供文件路径")
            raise ValueError("未提供文件路径")

        print("正在验证文件...")
        FileUtils.validate_file(file_path)
        
        # 询问要上传到哪些平台
        upload_platforms = UIUtils.ask_upload_platforms()
        
        if upload_platforms:
            # 上传到选定的平台
            results = platform_manager.upload_to_platforms(file_path, upload_platforms)
            
            # 显示上传结果摘要
            platform_manager.display_upload_results(results)
        else:
            print("只进行了文件验证，未上传到任何平台")
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        print(f"程序执行失败: {e}")
        return

    print("处理完成！")


if __name__ == "__main__":
    main() 