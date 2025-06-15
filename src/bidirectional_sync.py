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
    
    def run_sync(self, directions: Optional[List[str]] = None, batch_size: int = 10) -> Dict[str, Any]:
        """运行双向同步"""
        print("开始双向同步...")
        
        sync_results = {
            "strava_to_garmin": {"success": 0, "failed": 0, "skipped": 0},
            "garmin_to_strava": {"success": 0, "failed": 0, "skipped": 0},
            "total_processed": 0,
            "errors": []
        }
        
        # 如果没有指定方向，使用所有启用的方向
        if not directions:
            directions = []
            for source, target in self.sync_directions:
                if self.sync_manager.is_sync_enabled(source, target):
                    directions.append(f"{source}_to_{target}")
        
        # 执行各个方向的同步
        for direction in directions:
            if "_to_" in direction:
                source, target = direction.split("_to_")
                try:
                    result = self._sync_direction(source, target, batch_size)
                    sync_results[direction].update(result)
                    sync_results["total_processed"] += result.get("processed", 0)
                except Exception as e:
                    error_msg = f"{direction}同步失败: {e}"
                    logger.error(error_msg)
                    sync_results["errors"].append(error_msg)
        
        # 清理旧缓存
        self.sync_manager.cleanup_old_cache()
        
        # 显示同步结果
        self._display_sync_results(sync_results)
        
        return sync_results
    
    def _sync_direction(self, source_platform: str, target_platform: str, batch_size: int) -> Dict[str, int]:
        """执行单个方向的同步"""
        direction = f"{source_platform}_to_{target_platform}"
        print(f"\n开始{direction}同步...")
        
        result = {"success": 0, "failed": 0, "skipped": 0, "processed": 0}
        
        try:
            # 检查API限制
            if not self._check_api_limits(source_platform):
                print(f"{source_platform} API限制已达到，跳过此方向同步")
                return result
            
            # 获取同步时间窗口
            start_time, end_time = self.sync_manager.get_sync_window(source_platform)
            
            # 获取源平台活动
            source_activities = self._get_platform_activities(source_platform, batch_size, start_time, end_time)
            
            if not source_activities:
                print(f"在{source_platform}中未找到需要同步的活动")
                return result
            
            print(f"找到{len(source_activities)}个{source_platform}活动需要处理")
            
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
                    
                    # 检查API限制
                    if not self._check_api_limits(source_platform):
                        print(f"API限制已达到，停止{direction}同步")
                        break
                        
                except Exception as e:
                    logger.error(f"处理活动失败: {e}")
                    result["failed"] += 1
                    result["processed"] += 1
            
            # 更新最后同步时间
            self.sync_manager.update_last_sync_time(source_platform)
            
        except Exception as e:
            logger.error(f"{direction}同步失败: {e}")
            raise
        
        return result
    
    def _get_platform_activities(self, platform: str, limit: int, 
                               start_time: datetime, end_time: datetime) -> List[Dict]:
        """获取平台活动列表"""
        try:
            if platform == "strava":
                # 记录API请求
                self.sync_manager.record_api_request("strava")
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
        
        for direction, stats in results.items():
            if direction.endswith("_to_garmin") or direction.endswith("_to_strava"):
                direction_name = direction.replace("_", " -> ").upper()
                print(f"\n{direction_name}:")
                print(f"  成功: {stats['success']}")
                print(f"  失败: {stats['failed']}")
                print(f"  跳过: {stats['skipped']}")
        
        print(f"\n总处理活动数: {results['total_processed']}")
        
        if results['errors']:
            print(f"\n错误信息:")
            for error in results['errors']:
                print(f"  - {error}")
        
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