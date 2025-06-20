#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys
import os
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
import questionary

# 导入同步相关模块
from config_manager import ConfigManager
from bidirectional_sync import BidirectionalSync

load_dotenv()
logger = logging.getLogger()
DEBUG = False  # 全局调试标志

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('sync_logs.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def debug_print(message: str) -> None:
    """只在调试模式下打印信息"""
    if DEBUG:
        print(f"[MainSync] {message}")


def show_main_menu() -> str:
    """显示主菜单"""
    return questionary.select(
        "选择操作:",
        choices=[
            {"name": "开始双向同步", "value": "sync"},
            {"name": "配置同步规则", "value": "config"},
            {"name": "查看同步状态", "value": "status"},
            {"name": "清理缓存文件", "value": "cleanup"},
            {"name": "清除Garmin会话", "value": "clear_garmin_session"},
            {"name": "退出", "value": "exit"}
        ]
    ).ask()


def select_sync_mode() -> str:
    """选择同步模式"""
    return questionary.select(
        "选择同步模式:",
        choices=[
            {"name": "历史迁移模式 - 从最老的活动开始批量迁移所有历史数据", "value": "migration"},
            {"name": "增量同步模式 - 只同步最近的新活动", "value": "incremental"}
        ],
        instruction="(使用方向键选择，回车键确认)"
    ).ask()


def select_sync_directions() -> list:
    """选择同步方向"""
    return questionary.checkbox(
        "选择要执行的同步方向:",
        choices=[
            {"name": "Strava -> Garmin", "value": "strava_to_garmin", "checked": False},
            {"name": "Garmin -> Strava", "value": "garmin_to_strava", "checked": False},
            {"name": "Strava -> OneDrive", "value": "strava_to_onedrive", "checked": False},
            {"name": "Garmin -> OneDrive", "value": "garmin_to_onedrive", "checked": False}
        ],
        instruction="(使用空格键选择，回车键确认)"
    ).ask()


def select_migration_start_time(sync_direction: str) -> str:
    """选择历史迁移的起始时间"""
    import questionary
    from datetime import datetime, timedelta
    
    # 预设选项
    now = datetime.now()
    options = [
        {"name": "1年前", "value": (now - timedelta(days=365)).strftime("%Y-%m-%d")},
        {"name": "2年前", "value": (now - timedelta(days=730)).strftime("%Y-%m-%d")},
        {"name": "3年前", "value": (now - timedelta(days=1095)).strftime("%Y-%m-%d")},
        {"name": "5年前", "value": (now - timedelta(days=1825)).strftime("%Y-%m-%d")},
        {"name": "自定义时间", "value": "custom"}
    ]
    
    choice = questionary.select(
        f"选择{sync_direction}迁移的起始时间:",
        choices=options,
        instruction="(选择从什么时间开始迁移历史数据)"
    ).ask()
    
    if choice == "custom":
        while True:
            custom_date = questionary.text(
                "请输入自定义起始日期 (格式: YYYY-MM-DD):",
                default=(now - timedelta(days=1095)).strftime("%Y-%m-%d")
            ).ask()
            
            try:
                # 验证日期格式
                datetime.strptime(custom_date, "%Y-%m-%d")
                return custom_date
            except ValueError:
                print("日期格式无效，请使用 YYYY-MM-DD 格式")
    
    return choice


def select_batch_size(migration_mode: bool = True) -> int:
    """选择批次大小"""
    if migration_mode:
        return questionary.select(
            "选择历史迁移的批次大小:",
            choices=[
                {"name": "调试模式 - 每次10个活动", "value": 10},
                {"name": "正常模式 - 每次50个活动", "value": 50},
                {"name": "快速模式 - 每次100个活动", "value": 100}
            ],
            instruction="(建议先用调试模式验证功能)"
        ).ask()
    else:
        return questionary.select(
            "选择增量同步的批次大小:",
            choices=[
                {"name": "小批次 - 每次10个活动", "value": 10},
                {"name": "中批次 - 每次30个活动", "value": 30},
                {"name": "大批次 - 每次50个活动", "value": 50}
            ]
        ).ask()


def display_sync_status(sync_engine: BidirectionalSync) -> None:
    """显示同步状态"""
    print("\n" + "="*60)
    print("同步状态信息")
    print("="*60)
    
    try:
        status = sync_engine.get_sync_status()
        
        # 基本统计
        print(f"\n总活动记录数: {status['total_activities']}")
        
        # 各平台活动数量
        if status['platform_counts']:
            print("\n各平台活动数量:")
            for platform, count in status['platform_counts'].items():
                print(f"  {platform.upper()}: {count}")
        
        # 同步状态统计
        if status['sync_status']:
            print("\n同步状态统计:")
            for direction, stats in status['sync_status'].items():
                direction_name = direction.replace("_", " -> ").upper()
                print(f"  {direction_name}:")
                for status_type, count in stats.items():
                    print(f"    {status_type}: {count}")
        
        # 最后同步时间
        print("\n最后同步时间:")
        for platform, last_sync in status['last_sync'].items():
            if last_sync:
                print(f"  {platform.upper()}: {last_sync}")
            else:
                print(f"  {platform.upper()}: 从未同步")
        
        # API限制状态
        if 'api_limits' in status:
            print("\nAPI限制状态:")
            for platform, limits in status['api_limits'].items():
                if 'unlimited' in limits:
                    print(f"  {platform.upper()}: 无限制")
                else:
                    print(f"  {platform.upper()}:")
                    print(f"    今日剩余: {limits.get('daily_remaining', 'N/A')}")
                    print(f"    15分钟剩余: {limits.get('quarter_hour_remaining', 'N/A')}")
        
        # 缓存信息
        print(f"\n缓存目录: {status['cache_dir']}")
        print(f"缓存文件数: {status['cache_files']}")
        
    except Exception as e:
        print(f"获取状态信息失败: {e}")
    
    print("="*60)


def cleanup_cache(sync_engine: BidirectionalSync) -> None:
    """清理缓存"""
    print("\n清理缓存文件...")
    
    days = questionary.text(
        "清理多少天前的缓存文件? (默认: 30天)",
        default="30"
    ).ask()
    
    try:
        days = int(days)
        sync_engine.sync_manager.cleanup_old_cache(days)
        print("缓存清理完成！")
    except ValueError:
        print("输入的天数无效")


def clear_garmin_session(sync_engine: BidirectionalSync) -> None:
    """清除Garmin会话"""
    sync_engine.clear_garmin_session()


def check_prerequisites(sync_engine: BidirectionalSync, directions: list = None) -> bool:
    """检查同步前提条件"""
    print("检查同步前提条件...")
    
    if not directions:
        directions = []
    
    issues = []
    required_platforms = set()
    
    # 根据同步方向确定需要检查的平台
    for direction in directions:
        if "_to_" in direction:
            source, target = direction.split("_to_")
            required_platforms.add(source)
            required_platforms.add(target)
    
    # 检查Strava配置（如果需要）
    if "strava" in required_platforms:
        if not sync_engine.strava_client.is_configured():
            issues.append("Strava API未配置")
    
    # 检查Garmin配置（如果需要）
    if "garmin" in required_platforms:
        try:
            print("检查Garmin登录状态...")
            if not sync_engine.garmin_client.test_connection():
                issues.append("Garmin Connect连接失败")
        except Exception as e:
            issues.append(f"Garmin Connect配置问题: {e}")
    
    # 检查OneDrive配置（如果需要）
    if "onedrive" in required_platforms:
        try:
            print("检查OneDrive连接状态...")
            if not sync_engine.config_manager.is_platform_configured("onedrive"):
                issues.append("OneDrive未配置")
            elif not sync_engine.onedrive_client.test_connection():
                issues.append("OneDrive连接失败")
        except Exception as e:
            issues.append(f"OneDrive配置问题: {e}")
    
    if issues:
        print("\n发现以下问题:")
        for issue in issues:
            print(f"  - {issue}")
        
        print("\n请先解决这些问题再进行同步。")
        print("参考配置文档:")
        if "strava" in required_platforms:
            print("  - Strava API: STRAVA_API_SETUP.md")
        if "garmin" in required_platforms:
            print("  - Garmin Connect: GARMIN_CONNECT_SETUP.md")
        if "onedrive" in required_platforms:
            print("  - OneDrive: 已配置，如有问题请检查访问令牌")
        
        return False
    
    print("前提条件检查通过！")
    return True


def main():
    global DEBUG
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Strava-Garmin双向同步工具')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    parser.add_argument('--auto', action='store_true', help='自动模式，使用默认设置直接同步')
    parser.add_argument('--directions', nargs='+', 
                       choices=['strava_to_garmin', 'garmin_to_strava', 'strava_to_onedrive', 'garmin_to_onedrive'],
                       help='指定同步方向')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小')
    args = parser.parse_args()
    
    DEBUG = args.debug
    
    if DEBUG:
        print("调试模式已启用")
    
    try:
        # 初始化配置管理器和同步引擎
        config_manager = ConfigManager()
        sync_engine = BidirectionalSync(config_manager, DEBUG)
        
        print("欢迎使用Strava-Garmin双向同步工具！")
        
        # 自动模式
        if args.auto:
            print("\n自动同步模式")
            
            directions = args.directions or ["strava_to_garmin", "garmin_to_strava"]
            batch_size = args.batch_size
            
            if not check_prerequisites(sync_engine, directions):
                return
            
            print(f"同步方向: {', '.join(directions)}")
            print(f"批处理大小: {batch_size}")
            
            sync_engine.run_sync(directions, batch_size)
            return
        
        # 交互模式
        while True:
            try:
                action = show_main_menu()
                
                if action == "exit":
                    print("再见！")
                    break
                
                elif action == "sync":
                    print("\n准备开始双向同步...")
                    
                    # 选择同步模式
                    sync_mode = select_sync_mode()
                    
                    # 选择同步方向
                    directions = select_sync_directions()
                    
                    if not directions:
                        print("未选择任何同步方向")
                        continue
                    
                    # 检查前提条件
                    if not check_prerequisites(sync_engine, directions):
                        continue
                    
                    # 获取批处理大小
                    batch_size = select_batch_size(sync_mode == "migration")
                    
                    # 如果是历史迁移模式，检查是否需要设置起始时间
                    if sync_mode == "migration":
                        for direction in directions:
                            # 检查是否已有迁移进度
                            progress = sync_engine.sync_manager.get_migration_progress("", direction)
                            if not progress:
                                # 首次迁移，让用户选择起始时间
                                start_time = select_migration_start_time(direction)
                                sync_engine.sync_manager.set_migration_start_time(direction, start_time)
                                print(f"已设置{direction}迁移起始时间: {start_time}")
                    
                    print(f"\n将执行以下同步:")
                    mode_desc = "历史迁移" if sync_mode == "migration" else "增量同步"
                    print(f"- 同步模式: {mode_desc}")
                    print(f"- 同步方向: {', '.join(directions)}")
                    print(f"- 批次大小: {batch_size}")
                    
                    if sync_mode == "migration":
                        print("\n⚠️  历史迁移模式说明:")
                        print("- 将从设定的起始时间开始，逐步迁移历史数据")
                        print("- 每次运行只处理指定数量的活动")
                        print("- 可以多次运行，自动从上次停止的地方继续")
                        print("- 建议先用调试模式（10个活动）验证功能")
                    
                    if not questionary.confirm("确认开始同步?").ask():
                        continue
                    
                    # 执行同步
                    migration_mode = (sync_mode == "migration")
                    results = sync_engine.run_sync(directions, batch_size, migration_mode)
                
                elif action == "config":
                    sync_engine.configure_sync_rules()
                
                elif action == "status":
                    display_sync_status(sync_engine)
                
                elif action == "cleanup":
                    cleanup_cache(sync_engine)
                
                elif action == "clear_garmin_session":
                    clear_garmin_session(sync_engine)
                
            except KeyboardInterrupt:
                print("\n操作被用户中断")
                break
            except Exception as e:
                logger.error(f"操作失败: {e}")
                print(f"操作失败: {e}")
                
                if DEBUG:
                    import traceback
                    traceback.print_exc()
    
    except Exception as e:
        logger.error(f"程序初始化失败: {e}")
        print(f"程序初始化失败: {e}")
        
        if DEBUG:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main() 