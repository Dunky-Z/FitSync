#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'src')

from sync_manager import SyncManager
from config_manager import ConfigManager
from datetime import datetime

def main():
    print("=== 同步时间窗口调试 ===")
    
    config = ConfigManager()
    sync_manager = SyncManager(config, debug=True)
    
    # 检查当前的同步时间窗口
    print("\n1. 检查同步时间窗口...")
    start_time, end_time = sync_manager.get_sync_window('strava')
    print(f'Strava同步时间窗口: {start_time} 到 {end_time}')
    
    # 检查最后同步时间
    print("\n2. 检查最后同步时间...")
    last_sync = sync_manager.db_manager.get_last_sync_time('strava')
    print(f'Strava最后同步时间: {last_sync}')
    
    # 检查时间差
    if last_sync:
        last_sync_dt = datetime.fromisoformat(last_sync)
        now = datetime.now()
        time_diff = now - last_sync_dt
        print(f'距离上次同步: {time_diff}')
    else:
        print('这是首次同步')
    
    # 显示一些示例活动时间
    print("\n3. 检查最近的Strava活动时间...")
    from strava_client import StravaClient
    strava_client = StravaClient(config, debug=False)  # 关闭调试避免干扰
    
    if strava_client.is_configured():
        activities = strava_client.get_activities(limit=5)
        print(f"获取到{len(activities)}个活动")
        
        for i, activity in enumerate(activities):
            activity_time = datetime.fromisoformat(activity['start_date'].replace('Z', '+00:00'))
            print(f'\n活动{i+1}: {activity["name"][:50]}...')
            print(f'  时间: {activity_time}')
            
            # 检查是否在时间窗口内
            if start_time <= activity_time <= end_time:
                print(f'  ✅ 在同步窗口内')
            else:
                print(f'  ❌ 不在同步窗口内')
                if activity_time < start_time:
                    print(f'     (活动时间早于窗口开始时间)')
                if activity_time > end_time:
                    print(f'     (活动时间晚于窗口结束时间)')
    else:
        print("Strava未配置")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    main() 