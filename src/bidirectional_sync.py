import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

from config_manager import ConfigManager
from sync_manager import SyncManager, ActivityMetadata
from activity_matcher import ActivityMatcher
from strava_client import StravaClient
from garmin_sync_client import GarminSyncClient

logger = logging.getLogger(__name__)

class BidirectionalSync:
    """双向同步核心类"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        
        # 初始化各个组件
        self.sync_manager = SyncManager(config_manager, debug)
        self.activity_matcher = ActivityMatcher(debug)
        self.strava_client = StravaClient(config_manager, debug)
        self.garmin_client = GarminSyncClient(config_manager, debug)
        
        # 支持的同步方向
        self.sync_directions = [
            ("strava", "garmin"),
            ("garmin", "strava")
        ]
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[BidirectionalSync] {message}")
    
    def run_sync(self, directions: Optional[List[str]] = None, batch_size: int = 10, migration_mode: bool = True) -> Dict[str, Any]:
        """运行双向同步
        
        Args:
            directions: 同步方向列表，如 ['strava_to_garmin', 'garmin_to_strava']
            batch_size: 每批处理的活动数量
            migration_mode: 是否为历史迁移模式
        """
        if directions is None:
            directions = ["strava_to_garmin", "garmin_to_strava"]
        
        sync_results = {}
        
        for direction in directions:
            if "_to_" not in direction:
                logger.warning(f"无效的同步方向: {direction}")
                continue
            
            source_platform, target_platform = direction.split("_to_")
            
            try:
                result = self._sync_direction(source_platform, target_platform, batch_size, migration_mode)
                sync_results[direction] = result
                
            except Exception as e:
                logger.error(f"{direction}同步失败: {e}")
                sync_results[direction] = {"success": 0, "failed": 0, "skipped": 0, "processed": 0, "error": str(e)}
        
        # 显示同步结果
        self._display_sync_results(sync_results)
        
        return sync_results
    
    def _sync_direction(self, source_platform: str, target_platform: str, batch_size: int, migration_mode: bool = True) -> Dict[str, int]:
        """执行单个方向的同步"""
        direction = f"{source_platform}_to_{target_platform}"
        mode_desc = "历史迁移" if migration_mode else "增量同步"
        print(f"\n开始{direction}{mode_desc}...")
        
        result = {"success": 0, "failed": 0, "skipped": 0, "processed": 0}
        
        try:
            # 检查API限制
            if not self._check_api_limits(source_platform):
                print(f"{source_platform} API限制已达到，跳过此方向同步")
                return result
            
            # 获取同步时间窗口
            start_time, end_time = self.sync_manager.get_sync_window(source_platform, migration_mode=migration_mode)
            
            # 检查历史迁移是否已完成
            if migration_mode and self.sync_manager.is_migration_complete(source_platform):
                print(f"{source_platform}历史迁移已完成")
                return result
            
            # 获取源平台活动
            source_activities = self._get_platform_activities(
                source_platform, batch_size, start_time, end_time, migration_mode
            )
            
            if not source_activities:
                if migration_mode:
                    print(f"在{source_platform}中未找到更多需要迁移的活动，迁移可能已完成")
                else:
                    print(f"在{source_platform}中未找到需要同步的活动")
                return result
            
            print(f"找到{len(source_activities)}个{source_platform}活动需要处理")
            
            # 记录最新处理的活动时间（用于更新迁移进度）
            latest_activity_time = None
            
            # 处理每个活动
            for activity_data in source_activities:
                try:
                    processed = self._process_single_activity(
                        activity_data, source_platform, target_platform
                    )
                    
                    if processed == "success":
                        result["success"] += 1
                    elif processed == "skipped":
                        result["skipped"] += 1
                    else:
                        result["failed"] += 1
                    
                    result["processed"] += 1
                    
                    # 记录活动时间
                    activity_time_str = activity_data.get('start_date', '')
                    if activity_time_str:
                        activity_time = datetime.fromisoformat(activity_time_str.replace('Z', '+00:00'))
                        if not latest_activity_time or activity_time > latest_activity_time:
                            latest_activity_time = activity_time
                    
                    # 检查API限制
                    if not self._check_api_limits(source_platform):
                        print(f"API限制已达到，停止{direction}同步")
                        break
                        
                except Exception as e:
                    logger.error(f"处理活动失败: {e}")
                    result["failed"] += 1
                    result["processed"] += 1
            
            # 更新同步进度
            if migration_mode and latest_activity_time:
                self.sync_manager.update_migration_progress(source_platform, latest_activity_time)
                print(f"更新{source_platform}迁移进度到: {latest_activity_time}")
            else:
                # 非迁移模式，更新最后同步时间
                self.sync_manager.update_last_sync_time(source_platform)
            
        except Exception as e:
            logger.error(f"{direction}同步失败: {e}")
            raise
        
        return result
    
    def _get_platform_activities(self, platform: str, limit: int, 
                               start_time: datetime, end_time: datetime, 
                               migration_mode: bool = True) -> List[Dict]:
        """获取平台活动列表"""
        try:
            if platform == "strava":
                # 记录API请求
                self.sync_manager.record_api_request("strava")
                
                if migration_mode:
                    # 历史迁移模式：使用专门的迁移方法
                    return self.strava_client.get_activities_for_migration(
                        batch_size=limit, after=start_time, before=end_time
                    )
                else:
                    # 增量同步模式：使用原有方法
                    return self.strava_client.get_activities_in_batches(
                        total_limit=limit, after=start_time, before=end_time
                    )
            elif platform == "garmin":
                return self.garmin_client.get_activities(
                    limit=limit, after=start_time, before=end_time
                )
            else:
                raise ValueError(f"不支持的平台: {platform}")
                
        except Exception as e:
            logger.error(f"获取{platform}活动失败: {e}")
            return []
    
    def _process_single_activity(self, activity_data: Dict, source_platform: str, 
                               target_platform: str) -> str:
        """处理单个活动的同步"""
        try:
            # 转换为标准元数据格式
            if source_platform == "strava":
                metadata = self.strava_client.convert_to_activity_metadata(activity_data)
                activity_id = str(activity_data.get("id", ""))
            elif source_platform == "garmin":
                metadata = self.garmin_client.convert_to_activity_metadata(activity_data)
                activity_id = str(activity_data.get("activityId", ""))
            else:
                raise ValueError(f"不支持的源平台: {source_platform}")
            
            # 生成活动指纹
            fingerprint = self.sync_manager.generate_activity_fingerprint(metadata)
            
            # 检查是否已经同步过
            if self.sync_manager.is_activity_synced(fingerprint, source_platform, target_platform):
                self.debug_print(f"活动{activity_id}已同步，跳过")
                return "skipped"
            
            # 添加到同步记录
            self.sync_manager.add_sync_record(metadata, source_platform, activity_id)
            
            # 下载活动文件
            cache_file_path = self._download_activity_file(
                source_platform, activity_id, fingerprint, metadata.name
            )
            
            if not cache_file_path:
                self.sync_manager.update_sync_status(
                    fingerprint, source_platform, target_platform, "failed"
                )
                return "failed"
            
            # 上传到目标平台
            upload_success = self._upload_to_target_platform(
                target_platform, cache_file_path
            )
            
            if upload_success:
                self.sync_manager.update_sync_status(
                    fingerprint, source_platform, target_platform, "synced"
                )
                print(f"活动 '{metadata.name}' 同步成功: {source_platform} -> {target_platform}")
                return "success"
            else:
                self.sync_manager.update_sync_status(
                    fingerprint, source_platform, target_platform, "failed"
                )
                return "failed"
                
        except Exception as e:
            logger.error(f"处理活动同步失败: {e}")
            return "failed"
    
    def _download_activity_file(self, platform: str, activity_id: str, 
                              fingerprint: str, activity_name: str) -> Optional[str]:
        """下载活动文件到缓存"""
        try:
            # 检查缓存中是否已存在
            for ext in ['fit', 'tcx', 'gpx']:
                cache_path = self.sync_manager.get_cache_file_path(fingerprint, ext)
                if os.path.exists(cache_path):
                    self.debug_print(f"使用缓存文件: {cache_path}")
                    return cache_path
            
            # 下载文件
            cache_path = self.sync_manager.get_cache_file_path(fingerprint, 'fit')
            
            if platform == "strava":
                success = self.strava_client.download_activity_file(activity_id, cache_path)
            elif platform == "garmin":
                success = self.garmin_client.download_activity_file(activity_id, cache_path)
            else:
                return None
            
            if success and os.path.exists(cache_path):
                self.debug_print(f"文件已下载到缓存: {cache_path}")
                return cache_path
            
            return None
            
        except Exception as e:
            logger.error(f"下载活动文件失败: {e}")
            return None
    
    def _upload_to_target_platform(self, platform: str, file_path: str) -> bool:
        """上传文件到目标平台"""
        try:
            if platform == "strava":
                # Strava上传需要特殊处理，可能需要通过网页端
                self.debug_print("Strava上传功能待实现")
                return False
            elif platform == "garmin":
                return self.garmin_client.upload_file(file_path)
            else:
                return False
                
        except Exception as e:
            logger.error(f"上传到{platform}失败: {e}")
            return False
    
    def _check_api_limits(self, platform: str) -> bool:
        """检查API限制"""
        can_request = self.sync_manager.can_make_api_request(platform)
        
        if not can_request:
            status = self.sync_manager.get_api_limit_status(platform)
            self.debug_print(f"{platform} API限制状态: {status}")
        
        return can_request
    
    def _display_sync_results(self, results: Dict[str, Any]) -> None:
        """显示同步结果"""
        print("\n" + "="*50)
        print("双向同步结果摘要")
        print("="*50)
        
        total_success = 0
        total_failed = 0
        total_skipped = 0
        total_processed = 0
        
        for direction, result in results.items():
            if isinstance(result, dict) and "success" in result:
                direction_name = direction.replace("_", " -> ").upper()
                print(f"\n{direction_name}:")
                print(f"  成功: {result.get('success', 0)}")
                print(f"  失败: {result.get('failed', 0)}")
                print(f"  跳过: {result.get('skipped', 0)}")
                
                if "error" in result:
                    print(f"  错误: {result['error']}")
                
                total_success += result.get('success', 0)
                total_failed += result.get('failed', 0)
                total_skipped += result.get('skipped', 0)
                total_processed += result.get('processed', 0)
        
        print(f"\n总处理活动数: {total_processed}")
        print(f"总成功数: {total_success}")
        print(f"总失败数: {total_failed}")
        print(f"总跳过数: {total_skipped}")
        
        if total_processed > 0:
            success_rate = (total_success / total_processed) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print("="*50)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态信息"""
        stats = self.sync_manager.get_sync_statistics()
        
        # 添加API限制状态
        api_status = {}
        for platform in ["strava", "garmin"]:
            api_status[platform] = self.sync_manager.get_api_limit_status(platform)
        
        stats["api_limits"] = api_status
        
        return stats
    
    def configure_sync_rules(self) -> None:
        """配置同步规则"""
        print("\n配置同步规则:")
        
        for source, target in self.sync_directions:
            current_status = self.sync_manager.is_sync_enabled(source, target)
            direction_name = f"{source} -> {target}"
            
            print(f"\n{direction_name} (当前: {'启用' if current_status else '禁用'})")
            
            from ui_utils import UIUtils
            import questionary
            
            enable = questionary.confirm(
                f"是否启用 {direction_name} 同步?",
                default=current_status
            ).ask()
            
            self.sync_manager.set_sync_rule(source, target, enable)
        
        print("\n同步规则配置完成！") 