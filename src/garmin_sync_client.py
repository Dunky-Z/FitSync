import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from config_manager import ConfigManager
from database_manager import ActivityMetadata
from garmin_client import GarminClient

logger = logging.getLogger(__name__)

class GarminSyncClient:
    """Garmin同步客户端，封装现有的GarminClient用于双向同步"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        self.client = None
        
        # 初始化Garmin客户端
        self._initialize_client()
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[GarminSyncClient] {message}")
    
    def _initialize_client(self) -> None:
        """初始化Garmin客户端"""
        try:
            garmin_config = self.config_manager.get_platform_config("garmin")
            
            if not garmin_config.get("username") or not garmin_config.get("password"):
                self.debug_print("Garmin配置不完整")
                return
            
            self.client = GarminClient(
                email=garmin_config["username"],
                password=garmin_config["password"],
                auth_domain=garmin_config.get("auth_domain", "GLOBAL"),
                config_manager=self.config_manager
            )
            
            self.debug_print("Garmin客户端初始化成功")
            
        except Exception as e:
            logger.error(f"初始化Garmin客户端失败: {e}")
            self.client = None
    
    def test_connection(self) -> bool:
        """测试Garmin连接"""
        if not self.client:
            return False
        
        try:
            # 尝试获取一个活动来测试连接
            activities = self.client.getActivities(start=0, limit=1)
            return True
        except Exception as e:
            self.debug_print(f"Garmin连接测试失败: {e}")
            return False
    
    def get_activities(self, limit: int = 10, after: Optional[datetime] = None, 
                      before: Optional[datetime] = None) -> List[Dict]:
        """获取Garmin活动列表"""
        if not self.client:
            self.debug_print("Garmin客户端未初始化")
            return []
        
        try:
            self.debug_print(f"获取Garmin活动列表，限制: {limit}")
            
            # 使用现有的getActivities方法
            activities = self.client.getActivities(start=0, limit=limit)
            
            # 如果指定了时间范围，进行过滤
            if after or before:
                filtered_activities = []
                for activity in activities:
                    activity_time = self._parse_activity_time(activity)
                    if activity_time:
                        if after and activity_time < after:
                            continue
                        if before and activity_time > before:
                            continue
                    filtered_activities.append(activity)
                activities = filtered_activities
            
            self.debug_print(f"获取到{len(activities)}个Garmin活动")
            return activities
            
        except Exception as e:
            self.debug_print(f"获取Garmin活动失败: {e}")
            logger.error(f"获取Garmin活动失败: {e}")
            return []
    
    def _parse_activity_time(self, activity: Dict) -> Optional[datetime]:
        """解析活动时间"""
        try:
            # Garmin活动时间字段可能是startTimeLocal或startTimeGMT
            time_str = activity.get("startTimeLocal") or activity.get("startTimeGMT")
            if time_str:
                # 处理不同的时间格式
                if time_str.endswith('Z'):
                    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(time_str)
        except Exception as e:
            self.debug_print(f"解析活动时间失败: {e}")
        return None
    
    def convert_to_activity_metadata(self, activity_data: Dict) -> ActivityMetadata:
        """将Garmin活动数据转换为标准元数据格式"""
        try:
            # 提取基本信息
            name = activity_data.get("activityName", "未命名活动")
            sport_type = self._normalize_sport_type(activity_data.get("activityType", {}).get("typeKey", "other"))
            
            # 时间信息
            start_time_str = activity_data.get("startTimeLocal") or activity_data.get("startTimeGMT", "")
            
            # 距离和时长
            distance = float(activity_data.get("distance", 0))  # 米
            duration = int(activity_data.get("duration", 0))  # 秒
            
            # 海拔增益
            elevation_gain = float(activity_data.get("elevationGain", 0))  # 米
            
            return ActivityMetadata(
                name=name,
                sport_type=sport_type,
                start_time=start_time_str,
                distance=distance,
                duration=duration,
                elevation_gain=elevation_gain
            )
            
        except Exception as e:
            logger.error(f"转换Garmin活动元数据失败: {e}")
            # 返回默认元数据
            return ActivityMetadata(
                name="转换失败的活动",
                sport_type="other",
                start_time="",
                distance=0,
                duration=0
            )
    
    def _normalize_sport_type(self, garmin_type: str) -> str:
        """标准化运动类型"""
        type_mapping = {
            "running": "running",
            "cycling": "cycling", 
            "road_biking": "cycling",
            "mountain_biking": "cycling",
            "swimming": "swimming",
            "walking": "walking",
            "hiking": "hiking",
            "strength_training": "strength_training",
            "yoga": "yoga",
            "other": "other"
        }
        
        return type_mapping.get(garmin_type.lower(), "other")
    
    def download_activity_file(self, activity_id: str, output_path: str) -> bool:
        """下载活动文件"""
        if not self.client:
            self.debug_print("Garmin客户端未初始化")
            return False
        
        try:
            self.debug_print(f"下载Garmin活动文件: {activity_id}")
            
            # 使用现有的downloadFitActivity方法
            file_data = self.client.downloadFitActivity(activity_id)
            
            if file_data:
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 写入文件
                with open(output_path, 'wb') as f:
                    f.write(file_data)
                
                self.debug_print(f"文件已保存到: {output_path}")
                return True
            else:
                self.debug_print("下载的文件数据为空")
                return False
                
        except Exception as e:
            self.debug_print(f"下载活动文件失败: {e}")
            logger.error(f"下载Garmin活动文件失败: {e}")
            return False
    
    def upload_file(self, file_path: str) -> bool:
        """上传文件到Garmin"""
        if not self.client:
            self.debug_print("Garmin客户端未初始化")
            return False
        
        try:
            self.debug_print(f"上传文件到Garmin: {file_path}")
            
            # 使用现有的upload_activity方法
            result = self.client.upload_activity(file_path)
            
            if result == "SUCCESS":
                self.debug_print("上传成功")
                return True
            elif result == "DUPLICATE_ACTIVITY":
                self.debug_print("检测到重复活动，跳过上传")
                return True  # 重复活动也算成功
            else:
                self.debug_print(f"上传失败: {result}")
                return False
                
        except Exception as e:
            self.debug_print(f"上传文件失败: {e}")
            logger.error(f"上传文件到Garmin失败: {e}")
            return False 