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
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False, config_key: str = "garmin"):
        self.config_manager = config_manager
        self.debug = debug
        self.config_key = config_key
        self.client = None
        self._initialized = False
        self._current_domain = None  # 跟踪当前配置的域名
        
        # 不在初始化时立即创建Garmin客户端，改为延迟初始化
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[GarminSyncClient] {message}")
    
    def _ensure_client_initialized(self) -> bool:
        """确保Garmin客户端已初始化（延迟初始化）"""
        if self._initialized:
            return self.client is not None
        
        try:
            garmin_config = self.config_manager.get_platform_config(self.config_key)
            
            if not garmin_config.get("username") or not garmin_config.get("password"):
                self.debug_print(f"{self.config_key}配置不完整，无法初始化客户端")
                self._initialized = True
                return False
            
            self.debug_print(f"开始初始化{self.config_key}客户端...")
            
            auth_domain = garmin_config.get("auth_domain", "GLOBAL")
            if auth_domain and str(auth_domain).upper() == "CN":
                self._current_domain = "garmin.cn"
            else:
                self._current_domain = "garmin.com"
            
            self.client = GarminClient(
                email=garmin_config["username"],
                password=garmin_config["password"],
                auth_domain=auth_domain,
                config_manager=self.config_manager,
                debug=self.debug
            )
            
            self.debug_print(f"{self.config_key}客户端初始化成功")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"初始化{self.config_key}客户端失败: {e}")
            self.client = None
            self._initialized = True
            return False
    
    def test_connection(self) -> bool:
        """测试Garmin连接"""
        if not self._ensure_client_initialized():
            return False
        
        try:
            # 尝试获取一个活动来测试连接
            activities = self.client.getActivities(start=0, limit=1)
            return True
        except Exception as e:
            self.debug_print(f"Garmin连接测试失败: {e}")
            return False
    
    def _ensure_correct_domain(self):
        """确保配置了正确的域名和会话"""
        try:
            import garth
            
            # 如果域名已经正确，不需要重新配置
            if hasattr(garth.client, 'domain') and garth.client.domain == self._current_domain:
                self.debug_print(f"域名已正确配置为: {self._current_domain}")
                return
            
            self.debug_print(f"重新配置域名为: {self._current_domain}")
            
            # 重新配置域名
            garth.configure(domain=self._current_domain)
            
            # 重新初始化client以恢复正确的会话
            # 这会触发会话恢复或重新登录
            self._initialized = False
            self._ensure_client_initialized()
            
        except Exception as e:
            self.debug_print(f"配置域名失败: {e}")
            logger.error(f"配置域名失败: {e}")
    
    def get_activities(self, limit: int = 10, after: Optional[datetime] = None, 
                      before: Optional[datetime] = None) -> List[Dict]:
        """获取Garmin活动列表"""
        if not self._ensure_client_initialized():
            self.debug_print(f"{self.config_key}客户端初始化失败")
            return []
        
        try:
            from datetime import timezone
            
            self.debug_print(f"获取{self.config_key}活动列表，限制: {limit}")
            
            # 确保使用正确的域名和会话
            self._ensure_correct_domain()
            
            # 确保时间参数有时区信息
            if after and after.tzinfo is None:
                after = after.replace(tzinfo=timezone.utc)
            if before and before.tzinfo is None:
                before = before.replace(tzinfo=timezone.utc)
            
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
                    else:
                        # 如果无法解析时间，保留该活动
                        filtered_activities.append(activity)
                activities = filtered_activities
            
            self.debug_print(f"获取到{len(activities)}个{self.config_key}活动")
            return activities
            
        except Exception as e:
            self.debug_print(f"获取{self.config_key}活动失败: {e}")
            logger.error(f"获取{self.config_key}活动失败: {e}")
            import traceback
            if self.debug:
                traceback.print_exc()
            return []
    
    def _parse_activity_time(self, activity: Dict) -> Optional[datetime]:
        """解析活动时间"""
        try:
            from datetime import timezone
            # Garmin活动时间字段可能是startTimeLocal或startTimeGMT
            time_str = activity.get("startTimeLocal") or activity.get("startTimeGMT")
            if time_str:
                # 处理不同的时间格式
                if time_str.endswith('Z'):
                    parsed_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                else:
                    parsed_time = datetime.fromisoformat(time_str)
                
                # 确保返回的时间都有时区信息
                if parsed_time.tzinfo is None:
                    # 如果没有时区信息，假设为UTC
                    parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                
                return parsed_time
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
        """下载活动文件（处理ZIP压缩）"""
        if not self._ensure_client_initialized():
            self.debug_print(f"{self.config_key}客户端初始化失败")
            return False
        
        try:
            import zipfile
            import tempfile
            
            self.debug_print(f"下载{self.config_key}活动文件: {activity_id}")
            
            # 确保使用正确的域名和会话
            self._ensure_correct_domain()
            
            # 下载ZIP文件
            zip_data = self.client.downloadFitActivity(activity_id)
            
            if not zip_data:
                self.debug_print("下载的文件数据为空")
                return False
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 创建临时文件保存ZIP
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                temp_zip.write(zip_data)
                temp_zip_path = temp_zip.name
            
            try:
                # 尝试解压ZIP文件
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    # 获取ZIP中的文件列表
                    file_list = zip_ref.namelist()
                    self.debug_print(f"ZIP文件包含: {file_list}")
                    
                    if not file_list:
                        self.debug_print("ZIP文件为空")
                        return False
                    
                    # 通常ZIP中只有一个FIT文件，取第一个
                    fit_file_name = file_list[0]
                    
                    # 解压FIT文件
                    with zip_ref.open(fit_file_name) as fit_file:
                        fit_data = fit_file.read()
                        
                        # 保存FIT文件
                        with open(output_path, 'wb') as f:
                            f.write(fit_data)
                        
                        self.debug_print(f"FIT文件已从ZIP中提取并保存到: {output_path}")
                        self.debug_print(f"文件大小: {len(fit_data)} bytes")
                        return True
                        
            except zipfile.BadZipFile:
                # 如果不是ZIP文件，可能直接就是FIT文件（某些情况下）
                self.debug_print("下载的不是ZIP文件，尝试直接保存为FIT")
                with open(output_path, 'wb') as f:
                    f.write(zip_data)
                self.debug_print(f"文件已直接保存到: {output_path}")
                return True
                
            finally:
                # 清理临时ZIP文件
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                
        except Exception as e:
            self.debug_print(f"下载{self.config_key}活动文件失败: {e}")
            logger.error(f"下载{self.config_key}活动文件失败: {e}")
            import traceback
            if self.debug:
                traceback.print_exc()
            return False
    
    def upload_file(self, file_path: str) -> bool:
        """上传文件到Garmin"""
        if not self._ensure_client_initialized():
            self.debug_print(f"{self.config_key}客户端初始化失败")
            return False
        
        try:
            self.debug_print(f"上传文件到{self.config_key}: {file_path}")
            
            # 确保使用正确的域名和会话
            self._ensure_correct_domain()
            
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
            self.debug_print(f"上传文件到{self.config_key}失败: {e}")
            logger.error(f"上传文件到{self.config_key}失败: {e}")
            return False 