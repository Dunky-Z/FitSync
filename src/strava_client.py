import os
import time
import logging
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config_manager import ConfigManager
from file_utils import FileUtils
from ui_utils import UIUtils

logger = logging.getLogger(__name__)

class StravaClient:
    """Strava客户端"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(message)
    
    def is_configured(self) -> bool:
        """检查Strava是否已配置"""
        return self.config_manager.is_platform_configured("strava")
    
    def refresh_token(self) -> str:
        """刷新Strava访问令牌"""
        config = self.config_manager.get_platform_config("strava")
        self.debug_print("刷新Strava访问令牌...")
        
        url = "https://www.strava.com/oauth/token"
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": config["refresh_token"],
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(url, data=data)
            self.debug_print(f"Token刷新响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data["access_token"]
                
                # 更新配置中的access_token
                config["access_token"] = new_access_token
                if "refresh_token" in token_data:
                    config["refresh_token"] = token_data["refresh_token"]
                    
                # 保存更新后的配置
                self.config_manager.save_platform_config("strava", config)
                
                self.debug_print("Strava访问令牌刷新成功")
                return new_access_token
            else:
                self.debug_print(f"Token刷新失败: {response.text}")
                raise ValueError("无法刷新Strava访问令牌，请检查配置")
                
        except Exception as e:
            logger.error(f"刷新Strava令牌失败: {e}")
            raise
    
    def get_activities(self, limit: int = 10) -> List[Dict]:
        """获取用户的Strava活动列表"""
        access_token = self.refresh_token()
        self.debug_print(f"获取最新的{limit}个Strava活动...")
        
        url = "https://www.strava.com/api/v3/athlete/activities"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        params = {
            "per_page": limit,
            "page": 1
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            self.debug_print(f"活动列表响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                activities = response.json()
                self.debug_print(f"成功获取{len(activities)}个活动")
                return activities
            else:
                self.debug_print(f"获取活动列表失败: {response.text}")
                raise ValueError("无法获取活动列表")
                
        except Exception as e:
            logger.error(f"获取Strava活动失败: {e}")
            raise
    
    def select_activity_from_api(self) -> Tuple[str, Optional[str]]:
        """从API获取活动并让用户选择，返回(activity_id, activity_name)"""
        # 检查Strava配置
        if not self.is_configured():
            print("\n检测到默认的Strava API配置")
            print("请按照以下步骤获取Strava API凭据:")
            print("1. 访问 https://www.strava.com/settings/api")
            print("2. 创建应用程序获取 Client ID 和 Client Secret")
            print("3. 使用OAuth流程获取 Refresh Token")
            print("4. 更新 .app_config.json 文件中的strava配置")
            
            use_manual = UIUtils.ask_manual_token("Strava活动ID")
            
            if use_manual:
                return UIUtils.ask_activity_id(), None
            else:
                raise ValueError("请先配置Strava API凭据")
        
        try:
            # 获取活动列表
            activities = self.get_activities()
            
            if not activities:
                print("未找到任何活动")
                return UIUtils.ask_activity_id(), None
            
            # 让用户选择活动
            return UIUtils.select_activity_from_list(activities)
                
        except Exception as e:
            logger.error(f"从API获取活动失败: {e}")
            print(f"从API获取活动失败: {e}")
            print("将使用手动输入方式...")
            return UIUtils.ask_activity_id(), None
    
    def download_file(self, activity_id: str, activity_name: Optional[str] = None) -> Optional[str]:
        """下载活动文件"""
        # 统一使用export_original下载fit文件，不区分运动类型
        url = f"https://www.strava.com/activities/{activity_id}/export_original"
        
        self.debug_print(f"\n开始下载活动 {activity_id} 的原始文件...")
        self.debug_print(f"活动名称: {activity_name}")
        self.debug_print(f"下载URL: {url}")
        
        # 检查是否已存在相同活动ID的文件
        existing_file = FileUtils.check_existing_activity_file(activity_id, activity_name)
        if existing_file:
            print(f"发现已存在的活动文件: {os.path.basename(existing_file)}")
            if UIUtils.confirm_use_existing_file(os.path.basename(existing_file)):
                print("跳过下载，使用已存在的文件")
                return existing_file
            else:
                print("继续下载新文件...")
        
        # 直接使用Cookie认证下载
        return self._download_with_cookie(url, activity_id, activity_name)
    
    def _download_with_cookie(self, url: str, activity_id: str, activity_name: Optional[str] = None) -> Optional[str]:
        """使用Cookie进行认证下载"""
        config = self.config_manager.get_platform_config("strava")
        
        # 首先尝试使用保存的Cookie
        saved_cookie = config.get("cookie", "")
        
        if saved_cookie:
            self.debug_print("使用已保存的Cookie进行下载...")
            success, file_path = self._try_download_with_cookie(url, activity_id, saved_cookie, activity_name)
            if success:
                return file_path
            else:
                self.debug_print("保存的Cookie可能已过期，需要更新Cookie")
        
        # 如果没有保存的Cookie或Cookie已过期，提示用户输入新的Cookie
        print("\n要获取Strava Cookie，请按以下步骤操作：")
        print("1. 在浏览器中打开 https://www.strava.com 并登录")
        print("2. 按F12打开开发者工具")
        print("3. 转到 Network(网络) 标签")
        print("4. 刷新页面")
        print("5. 找到任意一个请求，在Request Headers中找到Cookie")
        print("6. 复制完整的Cookie值")
        
        cookie_value = UIUtils.ask_manual_token("Strava Cookie")
        
        if not cookie_value:
            print("未提供Cookie，无法下载文件")
            raise ValueError("Cookie为空，无法继续")
        
        # 尝试使用新Cookie下载
        success, file_path = self._try_download_with_cookie(url, activity_id, cookie_value, activity_name)
        
        if success:
            # 保存Cookie供下次使用
            config["cookie"] = cookie_value
            self.config_manager.save_platform_config("strava", config)
            return file_path
        else:
            print("Cookie无效或活动不可访问")
            raise ValueError("下载失败")
    
    def _try_download_with_cookie(self, url: str, activity_id: str, cookie: str, 
                                  activity_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """尝试使用Cookie下载文件"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Cookie': cookie.strip(),
                'Referer': f'https://www.strava.com/activities/{activity_id}'
            }
            
            self.debug_print(f"发送下载请求...")
            response = requests.get(url, headers=headers, timeout=30)
            
            self.debug_print(f"响应状态码: {response.status_code}")
            self.debug_print(f"Content-Type: {response.headers.get('content-type', 'Unknown')}")
            self.debug_print(f"Content-Length: {response.headers.get('content-length', 'Unknown')}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                # 生成文件名
                if activity_name:
                    # 使用活动名生成文件名
                    clean_name = FileUtils.sanitize_filename(activity_name)
                    base_filename = f"{clean_name}_{activity_id}"
                else:
                    # 如果没有活动名，使用默认格式
                    base_filename = f"activity_{activity_id}"
                
                # 判断文件类型并保存
                download_path = self._save_downloaded_file(response, base_filename, content_type)
                
                if download_path:
                    return True, download_path
                else:
                    return False, None
                    
            else:
                self.debug_print(f"下载失败 (状态码: {response.status_code})")
                return False, None
                
        except Exception as e:
            self.debug_print(f"下载出错: {e}")
            return False, None
    
    def _save_downloaded_file(self, response: requests.Response, base_filename: str, content_type: str) -> Optional[str]:
        """保存下载的文件"""
        try:
            if 'application/octet-stream' in content_type or 'application/fit' in content_type:
                # FIT文件（二进制）
                filename = f"{base_filename}.fit"
                download_path = os.path.join(os.path.expanduser("~/Downloads"), filename)
                
                with open(download_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"FIT文件已成功下载: {filename}")
                self.debug_print(f"文件大小: {len(response.content)} bytes")
                return download_path
                
            elif 'xml' in content_type or '<?xml' in response.text:
                # XML格式文件（TCX/GPX）
                content = response.text
                if 'TrainingCenterDatabase' in content:
                    filename = f"{base_filename}.tcx"
                elif 'gpx' in content.lower():
                    filename = f"{base_filename}.gpx"
                else:
                    filename = f"{base_filename}.xml"
                    
                download_path = os.path.join(os.path.expanduser("~/Downloads"), filename)
                
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"XML文件已成功下载: {filename}")
                self.debug_print(f"文件大小: {len(content)} characters")
                return download_path
            else:
                self.debug_print(f"未知的文件格式，Content-Type: {content_type}")
                if hasattr(response, 'text'):
                    preview = response.text[:200] if response.text else str(response.content[:200]) 
                    self.debug_print(f"响应内容开头: {preview}")
                return None
                
        except Exception as e:
            self.debug_print(f"文件保存失败: {e}")
            return None 