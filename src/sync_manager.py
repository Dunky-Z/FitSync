import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

from config_manager import ConfigManager
from database_manager import DatabaseManager, generate_activity_fingerprint, ActivityMetadata

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

@dataclass
class SyncRecord:
    """同步记录"""
    fingerprint: str
    platforms: Dict[str, str]  # platform -> activity_id
    metadata: ActivityMetadata
    files: Dict[str, str]      # format -> file_path
    sync_status: Dict[str, str]  # direction -> status
    created_at: str
    updated_at: str

class SyncManager:
    """同步管理器，负责活动同步状态跟踪和缓存管理"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        
        # 使用SQLite数据库管理器
        self.db_manager = DatabaseManager("sync_database.db", debug)
        
        # 缓存目录
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "activity_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # API限制配置
        self.api_limits = {
            "strava": {
                "daily_limit": 180,  # 保留20次余量
                "quarter_hour_limit": 90,  # 保留10次余量
                "daily_calls": 0,
                "quarter_hour_calls": 0,
                "last_reset": datetime.now()
            }
        }
        
        # 尝试从旧的JSON文件迁移数据
        self._migrate_from_json_if_exists()
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[SyncManager] {message}")
    
    def _migrate_from_json_if_exists(self) -> None:
        """如果存在旧的JSON文件，则迁移数据"""
        json_path = "sync_database.json"
        if os.path.exists(json_path):
            self.debug_print("发现旧的JSON数据库文件，开始迁移...")
            if self.db_manager.migrate_from_json(json_path):
                # 迁移成功后备份旧文件
                backup_path = f"{json_path}.backup"
                os.rename(json_path, backup_path)
                self.debug_print(f"数据迁移成功，旧文件已备份为: {backup_path}")
            else:
                self.debug_print("数据迁移失败")
    
    def generate_activity_fingerprint(self, metadata: ActivityMetadata) -> str:
        """生成活动指纹"""
        return generate_activity_fingerprint(metadata)
    
    @staticmethod
    def _generate_fingerprint_static(metadata: ActivityMetadata) -> str:
        """静态方法生成活动指纹"""
        return generate_activity_fingerprint(metadata)
    
    def is_activity_synced(self, fingerprint: str, source_platform: str, target_platform: str) -> bool:
        """检查活动是否已同步"""
        return self.db_manager.is_activity_synced(fingerprint, source_platform, target_platform)
    
    def add_sync_record(self, metadata: ActivityMetadata, platform: str, activity_id: str, 
                       file_path: Optional[str] = None) -> str:
        """添加同步记录"""
        fingerprint = self.db_manager.add_activity_record(metadata, platform, activity_id)
        
        # 如果有文件路径，添加到缓存记录
        if file_path:
            file_ext = os.path.splitext(file_path)[1][1:].lower()
            self.db_manager.add_file_cache(fingerprint, file_ext, file_path)
        
        return fingerprint
    
    def update_sync_status(self, fingerprint: str, source_platform: str, 
                          target_platform: str, status: str) -> None:
        """更新同步状态"""
        self.db_manager.update_sync_status(fingerprint, source_platform, target_platform, status)
    
    def get_sync_window(self, platform: str, max_days: int = 30) -> Tuple[datetime, datetime]:
        """获取同步时间窗口"""
        last_sync_str = self.db_manager.get_last_sync_time(platform)
        now = datetime.now()
        
        if not last_sync_str:
            # 首次同步：只同步最近30天
            start_time = now - timedelta(days=max_days)
            self.debug_print(f"{platform}首次同步，时间窗口: {start_time} - {now}")
        else:
            # 增量同步：从上次同步时间开始，1小时重叠避免遗漏
            last_sync = datetime.fromisoformat(last_sync_str)
            start_time = last_sync - timedelta(hours=1)
            self.debug_print(f"{platform}增量同步，时间窗口: {start_time} - {now}")
        
        return start_time, now
    
    def update_last_sync_time(self, platform: str, sync_time: Optional[datetime] = None) -> None:
        """更新最后同步时间"""
        self.db_manager.update_last_sync_time(platform, sync_time)
        self.debug_print(f"更新{platform}最后同步时间")
    
    def can_make_api_request(self, platform: str) -> bool:
        """检查是否可以进行API请求"""
        if platform not in self.api_limits:
            return True
        
        limits = self.api_limits[platform]
        now = datetime.now()
        
        # 重置计数器
        if (now - limits['last_reset']).total_seconds() >= 86400:  # 24小时
            limits['daily_calls'] = 0
            limits['last_reset'] = now
        
        if (now - limits['last_reset']).total_seconds() >= 900:  # 15分钟
            limits['quarter_hour_calls'] = 0
        
        return (limits['daily_calls'] < limits['daily_limit'] and
                limits['quarter_hour_calls'] < limits['quarter_hour_limit'])
    
    def record_api_request(self, platform: str) -> None:
        """记录API请求"""
        if platform in self.api_limits:
            self.api_limits[platform]['daily_calls'] += 1
            self.api_limits[platform]['quarter_hour_calls'] += 1
    
    def get_api_limit_status(self, platform: str) -> Dict[str, Any]:
        """获取API限制状态"""
        if platform not in self.api_limits:
            return {"unlimited": True}
        
        limits = self.api_limits[platform]
        return {
            "daily_remaining": limits['daily_limit'] - limits['daily_calls'],
            "quarter_hour_remaining": limits['quarter_hour_limit'] - limits['quarter_hour_calls'],
            "can_request": self.can_make_api_request(platform)
        }
    
    def get_cache_file_path(self, fingerprint: str, file_format: str) -> str:
        """获取缓存文件路径"""
        # 首先检查数据库中是否有缓存记录
        cached_path = self.db_manager.get_cached_file_path(fingerprint, file_format)
        if cached_path:
            return cached_path
        
        # 如果没有，返回默认路径
        return os.path.join(self.cache_dir, f"{fingerprint}.{file_format}")
    
    def is_sync_enabled(self, source_platform: str, target_platform: str) -> bool:
        """检查是否启用了指定方向的同步"""
        return self.db_manager.is_sync_enabled(source_platform, target_platform)
    
    def set_sync_rule(self, source_platform: str, target_platform: str, enabled: bool) -> None:
        """设置同步规则"""
        self.db_manager.set_sync_rule(source_platform, target_platform, enabled)
        self.debug_print(f"设置同步规则 {source_platform}_to_{target_platform}: {enabled}")
    
    def get_pending_syncs(self, source_platform: str, target_platform: str, limit: int = 10) -> List[Dict]:
        """获取待同步的活动"""
        # 这个方法需要在数据库管理器中实现，暂时返回空列表
        return []
    
    def cleanup_old_cache(self, days: int = 30) -> None:
        """清理旧的缓存文件"""
        cleaned_count = self.db_manager.cleanup_old_cache_records(days)
        self.debug_print(f"清理了{cleaned_count}个过期缓存文件")
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        stats = self.db_manager.get_sync_statistics()
        stats['cache_dir'] = self.cache_dir
        return stats
    
    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
    
    def __del__(self):
        """析构函数"""
        self.close() 