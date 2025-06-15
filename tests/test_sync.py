#!/usr/bin/env python3
"""
双向同步功能测试脚本
用于测试 Strava-Garmin 双向同步的各个组件
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)

import argparse

from config_manager import ConfigManager
from database_manager import DatabaseManager, ActivityMetadata
from sync_manager import SyncManager
from activity_matcher import ActivityMatcher, MatchResult
from strava_client import StravaClient
from garmin_sync_client import GarminSyncClient
from bidirectional_sync import BidirectionalSync

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_activity_metadata():
    """测试活动元数据创建"""
    print("测试活动元数据创建...")
    
    metadata = ActivityMetadata(
        name="测试跑步",
        sport_type="running",
        start_time="2024-01-01T06:00:00Z",
        distance=5000.0,
        duration=1800,
        elevation_gain=100.0
    )
    
    print(f"创建的元数据: {metadata}")
    return metadata

def test_sync_manager():
    """测试同步管理器"""
    print("\n测试同步管理器...")
    
    config_manager = ConfigManager()
    sync_manager = SyncManager(config_manager, debug=True)
    
    # 测试活动指纹生成
    metadata = test_activity_metadata()
    fingerprint = sync_manager.generate_activity_fingerprint(metadata)
    print(f"生成的指纹: {fingerprint}")
    
    # 测试添加同步记录
    record_fingerprint = sync_manager.add_sync_record(metadata, "strava", "12345")
    print(f"添加的记录指纹: {record_fingerprint}")
    
    # 测试同步状态更新
    sync_manager.update_sync_status(fingerprint, "strava", "garmin", "synced")
    print("同步状态已更新")
    
    # 测试统计信息
    stats = sync_manager.get_sync_statistics()
    print(f"统计信息: {stats}")
    
    return sync_manager

def test_activity_matcher():
    """测试活动匹配器"""
    print("\n测试活动匹配器...")
    
    matcher = ActivityMatcher(debug=True)
    
    # 创建两个相似的活动
    activity1 = ActivityMetadata(
        name="晨跑",
        sport_type="running",
        start_time="2024-01-01T06:00:00Z",
        distance=5000.0,
        duration=1800
    )
    
    activity2 = ActivityMetadata(
        name="Morning Run",
        sport_type="run",
        start_time="2024-01-01T06:02:00Z",  # 2分钟差异
        distance=5020.0,  # 20米差异
        duration=1810     # 10秒差异
    )
    
    # 测试匹配
    match_result = matcher.match_activities(activity1, activity2)
    print(f"匹配结果: {match_result}")
    
    return matcher

def test_strava_client():
    """测试Strava客户端"""
    print("\n测试Strava客户端...")
    
    config_manager = ConfigManager()
    strava_client = StravaClient(config_manager, debug=True)
    
    # 检查配置
    is_configured = strava_client.is_configured()
    print(f"Strava配置状态: {is_configured}")
    
    if is_configured:
        try:
            # 测试获取活动（限制1个避免API消耗）
            activities = strava_client.get_activities(limit=1)
            print(f"获取到{len(activities)}个活动")
            
            if activities:
                # 测试元数据转换
                metadata = strava_client.convert_to_activity_metadata(activities[0])
                print(f"转换的元数据: {metadata}")
        except Exception as e:
            print(f"Strava测试失败: {e}")
    else:
        print("Strava未配置，跳过API测试")
    
    return strava_client

def test_garmin_client():
    """测试Garmin客户端"""
    print("\n测试Garmin客户端...")
    
    config_manager = ConfigManager()
    garmin_client = GarminSyncClient(config_manager, debug=True)
    
    # 测试连接
    try:
        connection_ok = garmin_client.test_connection()
        print(f"Garmin连接状态: {connection_ok}")
        
        if connection_ok:
            # 测试获取活动（限制1个）
            activities = garmin_client.get_activities(limit=1)
            print(f"获取到{len(activities)}个Garmin活动")
            
            if activities:
                # 测试元数据转换
                metadata = garmin_client.convert_to_activity_metadata(activities[0])
                print(f"转换的Garmin元数据: {metadata}")
    except Exception as e:
        print(f"Garmin测试失败: {e}")
    
    return garmin_client

def test_bidirectional_sync():
    """测试双向同步核心功能"""
    print("\n测试双向同步核心功能...")
    
    config_manager = ConfigManager()
    sync_engine = BidirectionalSync(config_manager, debug=True)
    
    # 测试同步状态获取
    status = sync_engine.get_sync_status()
    print("同步状态获取成功")
    
    # 测试API限制检查
    strava_limit = sync_engine._check_api_limits("strava")
    print(f"Strava API限制检查: {strava_limit}")
    
    garmin_limit = sync_engine._check_api_limits("garmin")
    print(f"Garmin API限制检查: {garmin_limit}")
    
    return sync_engine

def test_sync_window():
    """测试同步时间窗口"""
    print("\n测试同步时间窗口...")
    
    config_manager = ConfigManager()
    sync_manager = SyncManager(config_manager, debug=True)
    
    # 测试首次同步窗口
    start_time, end_time = sync_manager.get_sync_window("strava")
    print(f"Strava同步窗口: {start_time} - {end_time}")
    
    # 更新同步时间
    sync_manager.update_last_sync_time("strava")
    
    # 测试增量同步窗口
    start_time2, end_time2 = sync_manager.get_sync_window("strava")
    print(f"更新后的同步窗口: {start_time2} - {end_time2}")

def test_cache_management():
    """测试缓存管理"""
    print("\n测试缓存管理...")
    
    config_manager = ConfigManager()
    sync_manager = SyncManager(config_manager, debug=True)
    
    # 测试缓存路径生成
    cache_path = sync_manager.get_cache_file_path("test_fingerprint", "fit")
    print(f"缓存文件路径: {cache_path}")
    
    # 测试缓存清理
    sync_manager.cleanup_old_cache(days=1)
    print("缓存清理完成")

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("开始双向同步功能测试")
    print("="*60)
    
    try:
        # 基础组件测试
        test_activity_metadata()
        test_sync_manager()
        test_activity_matcher()
        test_sync_window()
        test_cache_management()
        
        # 客户端测试
        test_strava_client()
        test_garmin_client()
        
        # 核心功能测试
        test_bidirectional_sync()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='双向同步功能测试')
    parser.add_argument('--test', choices=[
        'all', 'metadata', 'sync_manager', 'matcher', 
        'strava', 'garmin', 'bidirectional'
    ], default='all', help='选择要运行的测试')
    
    args = parser.parse_args()
    
    if args.test == 'all':
        run_all_tests()
    elif args.test == 'metadata':
        test_activity_metadata()
    elif args.test == 'sync_manager':
        test_sync_manager()
    elif args.test == 'matcher':
        test_activity_matcher()
    elif args.test == 'strava':
        test_strava_client()
    elif args.test == 'garmin':
        test_garmin_client()
    elif args.test == 'bidirectional':
        test_bidirectional_sync()

if __name__ == "__main__":
    main() 