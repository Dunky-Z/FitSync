import os
import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone
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
    
    def get_sync_window(self, platform: str, max_days: int = 30, migration_mode: bool = True, 
                       sync_direction: str = None) -> Tuple[datetime, datetime]:
        """获取同步时间窗口
        
        Args:
            platform: 平台名称
            max_days: 最大天数（仅在非迁移模式下使用）
            migration_mode: 是否为历史迁移模式
            sync_direction: 同步方向，格式为"source_to_target"
        """
        if migration_mode:
            return self._get_migration_window(platform, sync_direction)
        else:
            return self._get_incremental_window(platform, max_days)
    
    def _get_migration_window(self, platform: str, sync_direction: str = None) -> Tuple[datetime, datetime]:
        """获取历史迁移模式的时间窗口"""
        # 如果有同步方向，使用方向特定的进度；否则使用平台进度（向后兼容）
        if sync_direction:
            progress_key = f'migration_progress_{sync_direction}'
        else:
            progress_key = f'migration_progress_{platform}'
        
        # 获取迁移进度
        migration_progress = self.db_manager.get_sync_config(progress_key)
        
        # 检查是否有用户设置的起始时间
        if sync_direction:
            start_time_key = f'migration_start_time_{sync_direction}'
            custom_start_time = self.db_manager.get_sync_config(start_time_key)
            
            if not migration_progress and custom_start_time:
                # 首次迁移且有自定义起始时间
                start_time = datetime.fromisoformat(custom_start_time)
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                self.debug_print(f"{sync_direction}首次历史迁移，使用自定义起始时间: {start_time}")
            elif migration_progress:
                # 继续迁移：从上次迁移进度开始
                start_time = datetime.fromisoformat(migration_progress)
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                self.debug_print(f"{sync_direction}继续历史迁移，从{start_time}开始")
            else:
                # 首次迁移且无自定义起始时间：使用默认时间
                start_time = datetime(2008, 1, 1, tzinfo=timezone.utc)
                self.debug_print(f"{sync_direction}首次历史迁移，使用默认起始时间: {start_time}")
        else:
            # 向后兼容：原有逻辑
            if not migration_progress:
                start_time = datetime(2008, 1, 1, tzinfo=timezone.utc)
                self.debug_print(f"{platform}首次历史迁移，从{start_time}开始")
            else:
                start_time = datetime.fromisoformat(migration_progress)
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                self.debug_print(f"{platform}继续历史迁移，从{start_time}开始")
        
        # 结束时间：现在
        end_time = datetime.now(timezone.utc)
        
        direction_or_platform = sync_direction or platform
        self.debug_print(f"{direction_or_platform}历史迁移时间窗口: {start_time} - {end_time}")
        return start_time, end_time
    
    def _get_incremental_window(self, platform: str, max_days: int) -> Tuple[datetime, datetime]:
        """获取增量同步模式的时间窗口（原有逻辑）"""
        last_sync_str = self.db_manager.get_last_sync_time(platform)
        now = datetime.now()
        
        if not last_sync_str:
            # 首次同步：只同步最近30天
            start_time = now - timedelta(days=max_days)
            self.debug_print(f"{platform}首次同步，时间窗口: {start_time} - {now}")
        else:
            # 增量同步：从上次同步时间开始，1小时重叠避免遗漏
            last_sync = datetime.fromisoformat(last_sync_str)
            
            # 检查上次同步时间是否太久远（超过max_days天）
            time_since_last_sync = now - last_sync
            if time_since_last_sync.days > max_days:
                # 如果上次同步时间太久远，重置为首次同步模式
                start_time = now - timedelta(days=max_days)
                self.debug_print(f"{platform}上次同步时间过久({time_since_last_sync.days}天前)，重置为首次同步模式")
                self.debug_print(f"{platform}重置同步，时间窗口: {start_time} - {now}")
            else:
                # 正常增量同步，但确保至少覆盖最近7天
                min_start_time = now - timedelta(days=7)
                calculated_start_time = last_sync - timedelta(hours=1)
                start_time = min(calculated_start_time, min_start_time)
                self.debug_print(f"{platform}增量同步，时间窗口: {start_time} - {now}")
        
        # 确保返回的时间都是带时区信息的
        if start_time.tzinfo is None:
            # 如果是naive datetime，假设为UTC时间
            start_time = start_time.replace(tzinfo=timezone.utc)
        
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        return start_time, now
    
    def set_migration_start_time(self, sync_direction: str, start_time: str) -> None:
        """设置历史迁移的起始时间"""
        self.db_manager.set_sync_config(f'migration_start_time_{sync_direction}', start_time)
        self.debug_print(f"设置{sync_direction}迁移起始时间: {start_time}")
    
    def update_migration_progress(self, platform_or_direction: str, latest_activity_time: datetime, 
                                 sync_direction: str = None) -> None:
        """更新历史迁移进度"""
        # 如果提供了sync_direction，使用方向特定的进度；否则使用平台进度（向后兼容）
        if sync_direction:
            progress_key = f'migration_progress_{sync_direction}'
        else:
            progress_key = f'migration_progress_{platform_or_direction}'
        
        self.db_manager.set_sync_config(progress_key, latest_activity_time.isoformat())
        
        direction_or_platform = sync_direction or platform_or_direction
        self.debug_print(f"更新{direction_or_platform}迁移进度到: {latest_activity_time}")
    
    def get_migration_progress(self, platform_or_direction: str, sync_direction: str = None) -> Optional[datetime]:
        """获取历史迁移进度"""
        # 如果提供了sync_direction，使用方向特定的进度；否则使用平台进度（向后兼容）
        if sync_direction:
            progress_key = f'migration_progress_{sync_direction}'
        else:
            progress_key = f'migration_progress_{platform_or_direction}'
        
        progress_str = self.db_manager.get_sync_config(progress_key)
        if progress_str:
            progress = datetime.fromisoformat(progress_str)
            # 确保有时区信息
            if progress.tzinfo is None:
                progress = progress.replace(tzinfo=timezone.utc)
            return progress
        return None
    
    def is_migration_complete(self, platform_or_direction: str, sync_direction: str = None) -> bool:
        """检查历史迁移是否完成"""
        progress = self.get_migration_progress(platform_or_direction, sync_direction)
        if not progress:
            return False
        
        # 如果迁移进度已经接近当前时间（比如1天内），认为迁移完成
        now = datetime.now(timezone.utc)
        # 确保progress有时区信息
        if progress.tzinfo is None:
            progress = progress.replace(tzinfo=timezone.utc)
        return (now - progress).days <= 1
    
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