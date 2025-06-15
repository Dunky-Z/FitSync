import sqlite3
import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ActivityMetadata:
    """活动元数据"""
    name: str
    sport_type: str
    start_time: str  # ISO格式
    distance: float  # 米
    duration: int    # 秒
    elevation_gain: Optional[float] = None

def generate_activity_fingerprint(metadata: ActivityMetadata) -> str:
    """生成活动指纹的静态方法"""
    fingerprint_data = {
        'start_time': metadata.start_time[:16],  # 精确到分钟
        'sport_type': metadata.sport_type.lower(),
        'distance': round(metadata.distance / 50) * 50,  # 50米容差
        'duration': round(metadata.duration / 30) * 30   # 30秒容差
    }
    
    fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
    return hashlib.md5(fingerprint_str.encode()).hexdigest()

class DatabaseManager:
    """SQLite数据库管理器，用于存储同步数据"""
    
    def __init__(self, db_path: str = "sync_database.db", debug: bool = False):
        self.db_path = db_path
        self.debug = debug
        self.connection = None
        
        # 初始化数据库
        self._initialize_database()
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[DatabaseManager] {message}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # 使结果可以按列名访问
        return self.connection
    
    def _initialize_database(self) -> None:
        """初始化数据库表结构"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建活动记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_records (
                    fingerprint TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sport_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    distance REAL NOT NULL,
                    duration INTEGER NOT NULL,
                    elevation_gain REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 创建平台映射表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS platform_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    activity_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (fingerprint) REFERENCES activity_records (fingerprint),
                    UNIQUE(fingerprint, platform)
                )
            ''')
            
            # 创建同步状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    source_platform TEXT NOT NULL,
                    target_platform TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (fingerprint) REFERENCES activity_records (fingerprint),
                    UNIQUE(fingerprint, source_platform, target_platform)
                )
            ''')
            
            # 创建文件缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    file_format TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (fingerprint) REFERENCES activity_records (fingerprint),
                    UNIQUE(fingerprint, file_format)
                )
            ''')
            
            # 创建同步配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 创建API限制表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_limits (
                    platform TEXT PRIMARY KEY,
                    daily_calls INTEGER DEFAULT 0,
                    quarter_hour_calls INTEGER DEFAULT 0,
                    daily_limit INTEGER NOT NULL,
                    quarter_hour_limit INTEGER NOT NULL,
                    last_reset TEXT NOT NULL
                )
            ''')
            
            # 初始化默认配置
            self._initialize_default_config()
            
            conn.commit()
            self.debug_print("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _initialize_default_config(self) -> None:
        """初始化默认配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        default_configs = [
            ('last_sync_strava', ''),
            ('last_sync_garmin', ''),
            ('sync_rule_strava_to_garmin', 'true'),
            ('sync_rule_garmin_to_strava', 'true')
        ]
        
        for key, value in default_configs:
            cursor.execute('''
                INSERT OR IGNORE INTO sync_config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
    
    def add_activity_record(self, metadata: ActivityMetadata, platform: str, activity_id: str) -> str:
        """添加活动记录"""
        fingerprint = generate_activity_fingerprint(metadata)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # 插入或更新活动记录
            cursor.execute('''
                INSERT OR REPLACE INTO activity_records 
                (fingerprint, name, sport_type, start_time, distance, duration, elevation_gain, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM activity_records WHERE fingerprint = ?), ?), ?)
            ''', (fingerprint, metadata.name, metadata.sport_type, metadata.start_time,
                  metadata.distance, metadata.duration, metadata.elevation_gain,
                  fingerprint, now, now))
            
            # 插入平台映射
            cursor.execute('''
                INSERT OR REPLACE INTO platform_mappings (fingerprint, platform, activity_id, created_at)
                VALUES (?, ?, ?, ?)
            ''', (fingerprint, platform, activity_id, now))
            
            conn.commit()
            self.debug_print(f"添加活动记录: {fingerprint}")
            return fingerprint
            
        except Exception as e:
            conn.rollback()
            logger.error(f"添加活动记录失败: {e}")
            raise
    
    def update_sync_status(self, fingerprint: str, source_platform: str, 
                          target_platform: str, status: str) -> None:
        """更新同步状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status 
                (fingerprint, source_platform, target_platform, status, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (fingerprint, source_platform, target_platform, status, now))
            
            conn.commit()
            self.debug_print(f"更新同步状态: {fingerprint} {source_platform}->{target_platform} = {status}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新同步状态失败: {e}")
            raise
    
    def is_activity_synced(self, fingerprint: str, source_platform: str, target_platform: str) -> bool:
        """检查活动是否已同步"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查是否有两个平台的映射且同步状态为synced
        cursor.execute('''
            SELECT COUNT(*) as platform_count
            FROM platform_mappings 
            WHERE fingerprint = ? AND platform IN (?, ?)
        ''', (fingerprint, source_platform, target_platform))
        
        platform_count = cursor.fetchone()['platform_count']
        
        if platform_count < 2:
            return False
        
        # 检查同步状态
        cursor.execute('''
            SELECT status FROM sync_status 
            WHERE fingerprint = ? AND source_platform = ? AND target_platform = ?
        ''', (fingerprint, source_platform, target_platform))
        
        result = cursor.fetchone()
        return result and result['status'] == 'synced'
    
    def get_sync_config(self, key: str) -> Optional[str]:
        """获取同步配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM sync_config WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result['value'] if result else None
    
    def set_sync_config(self, key: str, value: str) -> None:
        """设置同步配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sync_config (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, now))
        
        conn.commit()
        self.debug_print(f"设置配置: {key} = {value}")
    
    def get_last_sync_time(self, platform: str) -> Optional[str]:
        """获取最后同步时间"""
        return self.get_sync_config(f'last_sync_{platform}')
    
    def update_last_sync_time(self, platform: str, sync_time: Optional[datetime] = None) -> None:
        """更新最后同步时间"""
        if sync_time is None:
            sync_time = datetime.now()
        
        self.set_sync_config(f'last_sync_{platform}', sync_time.isoformat())
        self.debug_print(f"更新{platform}最后同步时间: {sync_time}")
    
    def is_sync_enabled(self, source_platform: str, target_platform: str) -> bool:
        """检查是否启用了指定方向的同步"""
        rule_key = f'sync_rule_{source_platform}_to_{target_platform}'
        value = self.get_sync_config(rule_key)
        return value == 'true'
    
    def set_sync_rule(self, source_platform: str, target_platform: str, enabled: bool) -> None:
        """设置同步规则"""
        rule_key = f'sync_rule_{source_platform}_to_{target_platform}'
        self.set_sync_config(rule_key, 'true' if enabled else 'false')
    
    def add_file_cache(self, fingerprint: str, file_format: str, file_path: str) -> None:
        """添加文件缓存记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_cache (fingerprint, file_format, file_path, file_size, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (fingerprint, file_format, file_path, file_size, now))
        
        conn.commit()
        self.debug_print(f"添加文件缓存: {fingerprint}.{file_format}")
    
    def get_cached_file_path(self, fingerprint: str, file_format: str) -> Optional[str]:
        """获取缓存文件路径"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_path FROM file_cache 
            WHERE fingerprint = ? AND file_format = ?
        ''', (fingerprint, file_format))
        
        result = cursor.fetchone()
        if result and os.path.exists(result['file_path']):
            return result['file_path']
        return None
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 总活动数
        cursor.execute('SELECT COUNT(*) as total FROM activity_records')
        total_activities = cursor.fetchone()['total']
        
        # 各平台活动数量
        cursor.execute('''
            SELECT platform, COUNT(*) as count 
            FROM platform_mappings 
            GROUP BY platform
        ''')
        platform_counts = {row['platform']: row['count'] for row in cursor.fetchall()}
        
        # 同步状态统计
        cursor.execute('''
            SELECT source_platform, target_platform, status, COUNT(*) as count
            FROM sync_status 
            GROUP BY source_platform, target_platform, status
        ''')
        
        sync_status = {}
        for row in cursor.fetchall():
            direction = f"{row['source_platform']}_to_{row['target_platform']}"
            if direction not in sync_status:
                sync_status[direction] = {}
            sync_status[direction][row['status']] = row['count']
        
        # 最后同步时间
        last_sync = {
            'strava': self.get_last_sync_time('strava'),
            'garmin': self.get_last_sync_time('garmin')
        }
        
        # 缓存文件统计
        cursor.execute('SELECT COUNT(*) as count FROM file_cache')
        cache_files = cursor.fetchone()['count']
        
        return {
            'total_activities': total_activities,
            'platform_counts': platform_counts,
            'sync_status': sync_status,
            'last_sync': last_sync,
            'cache_files': cache_files,
            'database_path': self.db_path
        }
    
    def cleanup_old_cache_records(self, days: int = 30) -> int:
        """清理旧的缓存记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_time.isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取要删除的文件路径
        cursor.execute('''
            SELECT file_path FROM file_cache 
            WHERE created_at < ?
        ''', (cutoff_str,))
        
        old_files = [row['file_path'] for row in cursor.fetchall()]
        
        # 删除数据库记录
        cursor.execute('DELETE FROM file_cache WHERE created_at < ?', (cutoff_str,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        # 删除实际文件
        for file_path in old_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {file_path}, {e}")
        
        self.debug_print(f"清理了{deleted_count}个过期缓存记录")
        return deleted_count
    
    def migrate_from_json(self, json_file_path: str) -> bool:
        """从JSON文件迁移数据"""
        if not os.path.exists(json_file_path):
            self.debug_print(f"JSON文件不存在: {json_file_path}")
            return False
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 迁移同步记录
            for fingerprint, record in data.get('sync_records', {}).items():
                metadata_dict = record.get('metadata', {})
                metadata = ActivityMetadata(
                    name=metadata_dict.get('name', ''),
                    sport_type=metadata_dict.get('sport_type', ''),
                    start_time=metadata_dict.get('start_time', ''),
                    distance=metadata_dict.get('distance', 0),
                    duration=metadata_dict.get('duration', 0),
                    elevation_gain=metadata_dict.get('elevation_gain')
                )
                
                # 添加活动记录
                now = record.get('created_at', datetime.now().isoformat())
                cursor.execute('''
                    INSERT OR REPLACE INTO activity_records 
                    (fingerprint, name, sport_type, start_time, distance, duration, elevation_gain, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fingerprint, metadata.name, metadata.sport_type, metadata.start_time,
                      metadata.distance, metadata.duration, metadata.elevation_gain, now, now))
                
                # 添加平台映射
                for platform, activity_id in record.get('platforms', {}).items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO platform_mappings (fingerprint, platform, activity_id, created_at)
                        VALUES (?, ?, ?, ?)
                    ''', (fingerprint, platform, activity_id, now))
                
                # 添加同步状态
                for direction, status in record.get('sync_status', {}).items():
                    if '_to_' in direction:
                        source, target = direction.split('_to_')
                        cursor.execute('''
                            INSERT OR REPLACE INTO sync_status 
                            (fingerprint, source_platform, target_platform, status, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (fingerprint, source, target, status, now))
                
                # 添加文件缓存
                for file_format, file_path in record.get('files', {}).items():
                    if os.path.exists(file_path):
                        cursor.execute('''
                            INSERT OR REPLACE INTO file_cache (fingerprint, file_format, file_path, file_size, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (fingerprint, file_format, file_path, os.path.getsize(file_path), now))
            
            # 迁移配置
            sync_config = data.get('sync_config', {})
            
            # 最后同步时间
            for platform, last_sync in sync_config.get('last_sync', {}).items():
                if last_sync:
                    self.set_sync_config(f'last_sync_{platform}', last_sync)
            
            # 同步规则
            for direction, enabled in sync_config.get('sync_rules', {}).items():
                self.set_sync_config(f'sync_rule_{direction}', 'true' if enabled else 'false')
            
            conn.commit()
            self.debug_print(f"成功从JSON文件迁移数据: {json_file_path}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"JSON数据迁移失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close() 