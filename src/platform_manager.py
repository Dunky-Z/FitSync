import logging
from typing import List, Dict
from config_manager import ConfigManager
from strava_client import StravaClient
from igpsport_client import IGPSportClient
from garmin_client_wrapper import GarminClientWrapper

logger = logging.getLogger(__name__)

class PlatformManager:
    """平台管理器，统一管理所有平台的操作"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        
        # 初始化各平台客户端
        self.strava_client = StravaClient(config_manager, debug)
        self.igpsport_client = IGPSportClient(config_manager, debug)
        self.garmin_client = GarminClientWrapper(config_manager, debug)
        
        # 平台映射
        self.platform_clients = {
            "igpsport": self.igpsport_client,
            "garmin": self.garmin_client
        }
        
        self.platform_names = {
            "igpsport": "IGPSport",
            "garmin": "Garmin Connect"
        }
    
    def upload_to_platforms(self, file_path: str, platforms: List[str]) -> Dict[str, List[str]]:
        """上传文件到选定的平台"""
        upload_results = {
            "success": [],
            "failed": []
        }
        
        for platform in platforms:
            try:
                platform_name = self.platform_names.get(platform, platform)
                print(f"\n正在上传到{platform_name}...")
                
                client = self.platform_clients.get(platform)
                if client:
                    client.upload_file(file_path)
                    upload_results["success"].append(platform_name)
                else:
                    raise ValueError(f"不支持的平台: {platform}")
                    
            except Exception as e:
                platform_name = self.platform_names.get(platform, platform)
                logger.error(f"{platform}上传失败: {e}")
                upload_results["failed"].append(platform_name)
                print(f"{platform_name}上传失败: {e}")
        
        return upload_results
    
    def display_upload_results(self, results: Dict[str, List[str]]) -> None:
        """显示上传结果摘要"""
        if results["success"] or results["failed"]:
            print("\n上传结果摘要:")
            if results["success"]:
                print(f"成功上传到: {', '.join(results['success'])}")
            if results["failed"]:
                print(f"上传失败: {', '.join(results['failed'])}")
    
    def get_strava_client(self) -> StravaClient:
        """获取Strava客户端"""
        return self.strava_client 