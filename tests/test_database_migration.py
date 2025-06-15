#!/usr/bin/env python3
"""
数据库迁移测试脚本
演示从JSON文件到SQLite数据库的迁移功能
"""

import os
import sys

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_dir)

import json
import sqlite3
from datetime import datetime

from database_manager import DatabaseManager, ActivityMetadata

def create_sample_json_data():
    """创建示例JSON数据"""
    sample_data = {
        "sync_records": {
            "abc123def456": {
                "fingerprint": "abc123def456",
                "platforms": {
                    "strava": "1234567890",
                    "garmin": "9876543210"
                },
                "metadata": {
                    "name": "晨跑训练",
                    "sport_type": "running",
                    "start_time": "2025-06-14T06:00:00Z",
                    "distance": 5000.0,
                    "duration": 1800,
                    "elevation_gain": 50.0
                },
                "files": {
                    "fit": "activity_cache/abc123def456.fit"
                },
                "sync_status": {
                    "strava_to_garmin": "synced",
                    "garmin_to_strava": "pending"
                },
                "created_at": "2025-06-14T06:30:00",
                "updated_at": "2025-06-14T06:35:00"
            },
            "def789ghi012": {
                "fingerprint": "def789ghi012",
                "platforms": {
                    "strava": "2345678901"
                },
                "metadata": {
                    "name": "骑行训练",
                    "sport_type": "cycling",
                    "start_time": "2025-06-14T08:00:00Z",
                    "distance": 20000.0,
                    "duration": 3600,
                    "elevation_gain": 200.0
                },
                "files": {
                    "tcx": "activity_cache/def789ghi012.tcx"
                },
                "sync_status": {
                    "strava_to_garmin": "failed"
                },
                "created_at": "2025-06-14T09:00:00",
                "updated_at": "2025-06-14T09:05:00"
            }
        },
        "sync_config": {
            "last_sync": {
                "strava": "2025-06-14T10:00:00",
                "garmin": "2025-06-14T09:30:00"
            },
            "sync_rules": {
                "strava_to_garmin": True,
                "garmin_to_strava": False
            }
        }
    }
    
    return sample_data

def test_migration():
    """测试数据迁移功能"""
    print("="*60)
    print("数据库迁移测试")
    print("="*60)
    
    # 1. 创建示例JSON文件
    json_file = "test_sync_database.json"
    sample_data = create_sample_json_data()
    
    print(f"1. 创建示例JSON文件: {json_file}")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"   - 包含 {len(sample_data['sync_records'])} 个活动记录")
    print(f"   - 包含同步配置和规则")
    
    # 2. 创建SQLite数据库并迁移数据
    db_file = "test_migration.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    
    print(f"\n2. 创建SQLite数据库: {db_file}")
    db_manager = DatabaseManager(db_file, debug=True)
    
    print(f"\n3. 执行数据迁移...")
    success = db_manager.migrate_from_json(json_file)
    
    if success:
        print("   ✅ 数据迁移成功！")
    else:
        print("   ❌ 数据迁移失败！")
        return
    
    # 3. 验证迁移结果
    print(f"\n4. 验证迁移结果:")
    
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查活动记录
    cursor.execute("SELECT COUNT(*) as count FROM activity_records")
    activity_count = cursor.fetchone()['count']
    print(f"   - 活动记录数: {activity_count}")
    
    # 检查平台映射
    cursor.execute("SELECT COUNT(*) as count FROM platform_mappings")
    mapping_count = cursor.fetchone()['count']
    print(f"   - 平台映射数: {mapping_count}")
    
    # 检查同步状态
    cursor.execute("SELECT COUNT(*) as count FROM sync_status")
    status_count = cursor.fetchone()['count']
    print(f"   - 同步状态数: {status_count}")
    
    # 检查文件缓存
    cursor.execute("SELECT COUNT(*) as count FROM file_cache")
    cache_count = cursor.fetchone()['count']
    print(f"   - 文件缓存数: {cache_count}")
    
    # 检查配置
    cursor.execute("SELECT COUNT(*) as count FROM sync_config")
    config_count = cursor.fetchone()['count']
    print(f"   - 配置项数: {config_count}")
    
    # 显示详细数据
    print(f"\n5. 详细数据:")
    
    print(f"\n   活动记录:")
    cursor.execute("SELECT fingerprint, name, sport_type, distance FROM activity_records")
    for row in cursor.fetchall():
        print(f"     - {row['fingerprint'][:8]}... | {row['name']} | {row['sport_type']} | {row['distance']}m")
    
    print(f"\n   平台映射:")
    cursor.execute("SELECT fingerprint, platform, activity_id FROM platform_mappings")
    for row in cursor.fetchall():
        print(f"     - {row['fingerprint'][:8]}... | {row['platform']} | {row['activity_id']}")
    
    print(f"\n   同步状态:")
    cursor.execute("SELECT fingerprint, source_platform, target_platform, status FROM sync_status")
    for row in cursor.fetchall():
        print(f"     - {row['fingerprint'][:8]}... | {row['source_platform']} -> {row['target_platform']} | {row['status']}")
    
    print(f"\n   配置项:")
    cursor.execute("SELECT key, value FROM sync_config WHERE value != ''")
    for row in cursor.fetchall():
        print(f"     - {row['key']}: {row['value']}")
    
    conn.close()
    
    # 4. 测试数据库管理器功能
    print(f"\n6. 测试数据库管理器功能:")
    
    stats = db_manager.get_sync_statistics()
    print(f"   - 总活动数: {stats['total_activities']}")
    print(f"   - 平台统计: {stats['platform_counts']}")
    print(f"   - 同步状态: {stats['sync_status']}")
    print(f"   - 最后同步: {stats['last_sync']}")
    
    # 测试查询功能
    print(f"\n7. 测试查询功能:")
    
    # 检查活动是否已同步
    is_synced = db_manager.is_activity_synced("abc123def456", "strava", "garmin")
    print(f"   - abc123def456 strava->garmin 已同步: {is_synced}")
    
    # 获取配置
    last_sync_strava = db_manager.get_last_sync_time("strava")
    print(f"   - Strava最后同步时间: {last_sync_strava}")
    
    # 检查同步规则
    rule_enabled = db_manager.is_sync_enabled("strava", "garmin")
    print(f"   - strava->garmin 同步规则启用: {rule_enabled}")
    
    # 5. 清理测试文件
    print(f"\n8. 清理测试文件:")
    try:
        os.remove(json_file)
        print(f"   - 已删除: {json_file}")
    except:
        pass
    
    try:
        os.remove(db_file)
        print(f"   - 已删除: {db_file}")
    except:
        pass
    
    print(f"\n" + "="*60)
    print("数据库迁移测试完成！")
    print("="*60)

def compare_performance():
    """比较JSON和SQLite的性能"""
    print("\n" + "="*60)
    print("性能对比测试")
    print("="*60)
    
    import time
    
    # 创建大量测试数据
    print("1. 创建测试数据...")
    large_data = {"sync_records": {}, "sync_config": {"last_sync": {}, "sync_rules": {}}}
    
    for i in range(1000):
        fingerprint = f"test_{i:04d}_fingerprint"
        large_data["sync_records"][fingerprint] = {
            "fingerprint": fingerprint,
            "platforms": {"strava": f"strava_{i}", "garmin": f"garmin_{i}"},
            "metadata": {
                "name": f"测试活动 {i}",
                "sport_type": "running" if i % 2 == 0 else "cycling",
                "start_time": f"2025-06-{(i % 30) + 1:02d}T06:00:00Z",
                "distance": 5000.0 + i * 10,
                "duration": 1800 + i * 5,
                "elevation_gain": 50.0 + i
            },
            "sync_status": {"strava_to_garmin": "synced"},
            "created_at": "2025-06-14T06:30:00",
            "updated_at": "2025-06-14T06:35:00"
        }
    
    # JSON性能测试
    json_file = "large_test.json"
    print(f"\n2. JSON性能测试 (1000条记录):")
    
    start_time = time.time()
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(large_data, f)
    json_write_time = time.time() - start_time
    print(f"   - JSON写入时间: {json_write_time:.3f}秒")
    
    start_time = time.time()
    with open(json_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    json_read_time = time.time() - start_time
    print(f"   - JSON读取时间: {json_read_time:.3f}秒")
    
    # SQLite性能测试
    db_file = "large_test.db"
    print(f"\n3. SQLite性能测试 (1000条记录):")
    
    start_time = time.time()
    db_manager = DatabaseManager(db_file, debug=False)
    db_manager.migrate_from_json(json_file)
    sqlite_write_time = time.time() - start_time
    print(f"   - SQLite写入时间: {sqlite_write_time:.3f}秒")
    
    start_time = time.time()
    stats = db_manager.get_sync_statistics()
    sqlite_read_time = time.time() - start_time
    print(f"   - SQLite读取时间: {sqlite_read_time:.3f}秒")
    
    # 文件大小对比
    json_size = os.path.getsize(json_file) / 1024  # KB
    sqlite_size = os.path.getsize(db_file) / 1024  # KB
    
    print(f"\n4. 存储空间对比:")
    print(f"   - JSON文件大小: {json_size:.1f} KB")
    print(f"   - SQLite文件大小: {sqlite_size:.1f} KB")
    print(f"   - 空间效率: SQLite比JSON {'节省' if sqlite_size < json_size else '增加'} {abs(sqlite_size - json_size):.1f} KB")
    
    # 查询性能测试
    print(f"\n5. 查询性能测试:")
    
    # JSON查询
    start_time = time.time()
    count = 0
    for record in loaded_data["sync_records"].values():
        if record["metadata"]["sport_type"] == "running":
            count += 1
    json_query_time = time.time() - start_time
    print(f"   - JSON查询跑步活动: {json_query_time:.3f}秒 (找到{count}个)")
    
    # SQLite查询
    start_time = time.time()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activity_records WHERE sport_type = 'running'")
    count = cursor.fetchone()[0]
    conn.close()
    sqlite_query_time = time.time() - start_time
    print(f"   - SQLite查询跑步活动: {sqlite_query_time:.3f}秒 (找到{count}个)")
    
    # 清理
    try:
        os.remove(json_file)
        os.remove(db_file)
    except:
        pass
    
    print(f"\n6. 性能总结:")
    print(f"   - 写入性能: SQLite比JSON {'快' if sqlite_write_time < json_write_time else '慢'} {abs(sqlite_write_time - json_write_time):.3f}秒")
    print(f"   - 读取性能: SQLite比JSON {'快' if sqlite_read_time < json_read_time else '慢'} {abs(sqlite_read_time - json_read_time):.3f}秒")
    print(f"   - 查询性能: SQLite比JSON快 {json_query_time - sqlite_query_time:.3f}秒")

if __name__ == "__main__":
    test_migration()
    compare_performance() 