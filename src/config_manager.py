# -*- coding: utf-8 -*-
import os
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            # 获取项目根目录路径
            self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.project_root = project_root
        
        self.config_file = os.path.join(self.project_root, ".app_config.json")
        self.default_config = {
            "strava": {
                "client_id": "your_client_id_here",
                "client_secret": "your_client_secret_here", 
                "refresh_token": "your_refresh_token_here",
                "access_token": "",
                "cookie": ""
            },
            "igpsport": {
                "login_token": "",
                "username": "",
                "password": ""
            },
            "garmin": {
                "username": "",
                "password": "",
                "auth_domain": "GLOBAL",
                "session_cookies": "",
                "oauth_token": "",
                "oauth_token_secret": ""
            },
            "onedrive": {
                "client_id": "your_client_id_here",
                "client_secret": "your_client_secret_here",
                "redirect_uri": "http://localhost",
                "refresh_token": "",
                "access_token": "",
                "tenant_id": "common"
            },
            "intervals_icu": {
                "user_id": "",
                "api_key": ""
            },
            "general": {
                "debug_mode": False,
                "auto_save_credentials": True
            }
        }
    
    def get_config(self) -> Dict:
        """获取应用统一配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保所有必需的字段都存在
                    for section in self.default_config:
                        if section not in config:
                            config[section] = self.default_config[section]
                        else:
                            for key in self.default_config[section]:
                                if key not in config[section]:
                                    config[section][key] = self.default_config[section][key]
                    
                    # 兼容旧配置文件
                    self._migrate_old_config(config)
                    return config
        except Exception as e:
            logger.warning(f"读取应用配置文件失败: {e}")
        
        # 如果文件不存在或读取失败，创建默认配置文件
        self.save_config(self.default_config)
        return self.default_config
    
    def save_config(self, config: Dict) -> None:
        """保存应用统一配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存应用配置文件失败: {e}")
    
    def get_platform_config(self, platform: str) -> Dict:
        """获取特定平台的配置"""
        config = self.get_config()
        return config.get(platform, {})
    
    def save_platform_config(self, platform: str, platform_config: Dict) -> None:
        """保存特定平台的配置"""
        config = self.get_config()
        config[platform].update(platform_config)
        self.save_config(config)
    
    def _migrate_old_config(self, config: Dict) -> None:
        """迁移旧配置文件格式"""
        try:
            # 迁移旧的Strava配置
            old_strava_config = os.path.join(self.project_root, ".strava_config.json")
            if os.path.exists(old_strava_config):
                with open(old_strava_config, 'r', encoding='utf-8') as f:
                    old_strava = json.load(f)
                    for key, value in old_strava.items():
                        if key in config["strava"]:
                            config["strava"][key] = value
            
            # 迁移旧的Strava Cookie
            old_strava_cookie = os.path.join(self.project_root, ".strava_cookie")
            if os.path.exists(old_strava_cookie):
                with open(old_strava_cookie, 'r', encoding='utf-8') as f:
                    cookie = f.read().strip()
                    if cookie:
                        config["strava"]["cookie"] = cookie
            
            # 迁移旧的IGPSport Cookie
            old_igpsport_cookie = os.path.join(self.project_root, ".igpsport_cookie")
            if os.path.exists(old_igpsport_cookie):
                with open(old_igpsport_cookie, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                    if token:
                        config["igpsport"]["login_token"] = token
            
            # 保存迁移后的配置
            self.save_config(config)
            
        except Exception as e:
            logger.warning(f"配置迁移失败: {e}")
    
    def is_platform_configured(self, platform: str) -> bool:
        """检查平台是否已配置"""
        config = self.get_platform_config(platform)
        
        if platform == "strava":
            return (config.get("client_id") != "your_client_id_here" and 
                   config.get("client_secret") != "your_client_secret_here" and
                   config.get("refresh_token") != "your_refresh_token_here")
        elif platform == "igpsport":
            return bool(config.get("login_token") or 
                       (config.get("username") and config.get("password")))
        elif platform == "garmin":
            return bool(config.get("username") and config.get("password"))
        elif platform == "onedrive":
            return (config.get("client_id") != "your_client_id_here" and 
                   config.get("client_secret") != "your_client_secret_here" and
                   config.get("refresh_token"))
        elif platform == "intervals_icu":
            return bool(config.get("user_id") and config.get("api_key"))
        
        return False 