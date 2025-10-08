import os
import sys
import time
import json
import logging
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from config_manager import ConfigManager
from ui_utils import UIUtils
from database_manager import ActivityMetadata

logger = logging.getLogger(__name__)

class MyWhooshClient:
    """MyWhoosh客户端，使用Playwright实现网页自动化"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        self.base_url = "https://mywhoosh.com"
        self.login_url = f"{self.base_url}/login"
        self.activities_url = f"{self.base_url}/activities"
        
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[MyWhooshClient] {message}")
    
    def is_configured(self) -> bool:
        """检查MyWhoosh是否已配置"""
        config = self.config_manager.get_platform_config("mywhoosh")
        return bool(config.get("username") and config.get("password"))
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.is_configured():
                return False
            
            config = self.config_manager.get_platform_config("mywhoosh")
            username = config.get("username")
            password = config.get("password")
            
            self.debug_print("测试MyWhoosh连接...")
            
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                
                try:
                    success = self._login_with_page(page, username, password)
                    return success
                finally:
                    context.close()
                    browser.close()
                    
        except Exception as e:
            self.debug_print(f"连接测试失败: {e}")
            return False
    
    def get_credentials(self) -> Tuple[str, str]:
        """获取MyWhoosh登录凭据"""
        config = self.config_manager.get_platform_config("mywhoosh")
        
        saved_username = config.get("username", "")
        saved_password = config.get("password", "")
        
        if saved_username and saved_password:
            if UIUtils.ask_use_saved_credentials(saved_username):
                return saved_username, saved_password
        
        username, password = UIUtils.ask_credentials("MyWhoosh")
        
        if UIUtils.ask_save_credentials():
            config["username"] = username
            config["password"] = password
            self.config_manager.save_platform_config("mywhoosh", config)
            self.debug_print("MyWhoosh登录凭据已保存")
        
        return username, password
    
    def _login_with_page(self, page: Page, username: str, password: str) -> bool:
        """使用Playwright页面进行登录"""
        try:
            self.debug_print("访问MyWhoosh登录页面...")
            page.goto(self.login_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            
            self.debug_print("填写登录表单...")
            page.fill('input[type="email"], input[name="email"]', username)
            page.fill('input[type="password"], input[name="password"]', password)
            
            self.debug_print("点击登录按钮...")
            page.click('button[type="submit"]')
            
            page.wait_for_timeout(3000)
            
            if "activities" in page.url or "dashboard" in page.url:
                self.debug_print("登录成功")
                return True
            else:
                self.debug_print(f"登录后URL: {page.url}")
                return False
                
        except Exception as e:
            self.debug_print(f"登录失败: {e}")
            return False
    
    def get_activities(self, limit: int = 30, 
                      after: Optional[datetime] = None,
                      before: Optional[datetime] = None) -> List[Dict]:
        """获取MyWhoosh活动列表"""
        try:
            config = self.config_manager.get_platform_config("mywhoosh")
            username = config.get("username")
            password = config.get("password")
            
            if not username or not password:
                username, password = self.get_credentials()
            
            self.debug_print("启动浏览器获取活动列表...")
            
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                
                try:
                    if not self._login_with_page(page, username, password):
                        self.debug_print("登录失败，无法获取活动")
                        return []
                    
                    page.goto(self.activities_url, timeout=30000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                    
                    activities = []
                    
                    activities_data = page.evaluate("""() => {
                        const activities = [];
                        const activityElements = document.querySelectorAll('.activity-item, [data-activity-id]');
                        
                        activityElements.forEach(element => {
                            const id = element.getAttribute('data-activity-id') || element.id;
                            const titleElement = element.querySelector('.activity-title, h3, h4');
                            const dateElement = element.querySelector('.activity-date, time');
                            const distanceElement = element.querySelector('.activity-distance, [data-distance]');
                            const durationElement = element.querySelector('.activity-duration, [data-duration]');
                            
                            if (id) {
                                activities.push({
                                    id: id,
                                    title: titleElement ? titleElement.textContent.trim() : 'MyWhoosh Activity',
                                    date: dateElement ? dateElement.textContent.trim() || dateElement.getAttribute('datetime') : '',
                                    distance: distanceElement ? distanceElement.textContent.trim() : '0',
                                    duration: durationElement ? durationElement.textContent.trim() : '0'
                                });
                            }
                        });
                        
                        return activities;
                    }""")
                    
                    if not activities_data:
                        self.debug_print("页面上未找到活动元素，尝试使用API...")
                        activities_data = self._get_activities_via_api(context)
                    
                    for activity_data in activities_data[:limit]:
                        try:
                            activity_time = self._parse_activity_date(activity_data.get('date', ''))
                            
                            if after and activity_time and activity_time < after:
                                continue
                            if before and activity_time and activity_time > before:
                                continue
                            
                            activities.append(activity_data)
                            
                        except Exception as e:
                            self.debug_print(f"解析活动数据失败: {e}")
                            continue
                    
                    self.debug_print(f"获取到{len(activities)}个MyWhoosh活动")
                    return activities
                    
                finally:
                    context.close()
                    browser.close()
                    
        except Exception as e:
            self.debug_print(f"获取MyWhoosh活动失败: {e}")
            logger.error(f"获取MyWhoosh活动失败: {e}")
            return []
    
    def _get_activities_via_api(self, context: BrowserContext) -> List[Dict]:
        """通过拦截API请求获取活动数据"""
        activities = []
        
        try:
            page = context.new_page()
            
            def handle_response(response):
                if "api" in response.url and "activities" in response.url.lower():
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            activities.extend(data)
                        elif isinstance(data, dict) and "activities" in data:
                            activities.extend(data["activities"])
                    except:
                        pass
            
            page.on("response", handle_response)
            
            page.goto(self.activities_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            page.close()
            
        except Exception as e:
            self.debug_print(f"API拦截失败: {e}")
        
        return activities
    
    def _parse_activity_date(self, date_str: str) -> Optional[datetime]:
        """解析活动日期"""
        if not date_str:
            return None
        
        try:
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str.split('.')[0].split('Z')[0], fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except:
                    continue
            
            return None
        except Exception as e:
            self.debug_print(f"日期解析失败: {e}")
            return None
    
    def convert_to_activity_metadata(self, activity_data: Dict) -> ActivityMetadata:
        """将MyWhoosh活动数据转换为ActivityMetadata"""
        try:
            name = activity_data.get("title", "MyWhoosh Activity")
            sport_type = "cycling"
            
            start_time_str = activity_data.get("date", "")
            if start_time_str:
                activity_time = self._parse_activity_date(start_time_str)
                start_time = activity_time.isoformat() if activity_time else ""
            else:
                start_time = ""
            
            distance_str = str(activity_data.get("distance", "0"))
            distance = float(''.join(filter(str.isdigit, distance_str.replace('.', '', 1))))
            
            duration_str = str(activity_data.get("duration", "0"))
            duration = self._parse_duration(duration_str)
            
            elevation_gain = float(activity_data.get("elevation_gain", 0))
            
            return ActivityMetadata(
                name=name,
                sport_type=sport_type,
                start_time=start_time,
                distance=distance,
                duration=duration,
                elevation_gain=elevation_gain
            )
            
        except Exception as e:
            logger.error(f"转换MyWhoosh活动元数据失败: {e}")
            return ActivityMetadata(
                name="转换失败的活动",
                sport_type="cycling",
                start_time="",
                distance=0,
                duration=0
            )
    
    def _parse_duration(self, duration_str: str) -> int:
        """解析持续时间字符串，返回秒数"""
        try:
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:
                    minutes, seconds = map(int, parts)
                    return minutes * 60 + seconds
            
            return int(''.join(filter(str.isdigit, duration_str)))
        except:
            return 0
    
    def download_activity_file(self, activity_id: str, output_path: str) -> bool:
        """下载MyWhoosh活动文件"""
        try:
            config = self.config_manager.get_platform_config("mywhoosh")
            username = config.get("username")
            password = config.get("password")
            
            if not username or not password:
                username, password = self.get_credentials()
            
            self.debug_print(f"下载MyWhoosh活动文件: {activity_id}")
            
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                
                try:
                    if not self._login_with_page(page, username, password):
                        self.debug_print("登录失败，无法下载活动")
                        return False
                    
                    activity_url = f"{self.base_url}/activities/{activity_id}"
                    page.goto(activity_url, timeout=30000)
                    page.wait_for_load_state("networkidle")
                    
                    with page.expect_download(timeout=30000) as download_info:
                        page.click('button:has-text("Download"), a:has-text("Download"), [data-action="download"]')
                    
                    download = download_info.value
                    
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    download.save_as(output_path)
                    
                    file_size = os.path.getsize(output_path)
                    self.debug_print(f"文件已保存到: {output_path}")
                    self.debug_print(f"文件大小: {file_size} bytes")
                    
                    if file_size < 100:
                        self.debug_print("下载的文件过小，可能无效")
                        return False
                    
                    return True
                    
                finally:
                    context.close()
                    browser.close()
                    
        except Exception as e:
            self.debug_print(f"下载MyWhoosh活动文件异常: {e}")
            logger.error(f"下载MyWhoosh活动文件失败: {e}")
            return False
    
    def upload_file(self, file_path: str, activity_name: str = None) -> bool:
        """上传活动文件到MyWhoosh"""
        try:
            config = self.config_manager.get_platform_config("mywhoosh")
            username = config.get("username")
            password = config.get("password")
            
            if not username or not password:
                username, password = self.get_credentials()
            
            self.debug_print(f"上传文件到MyWhoosh: {file_path}")
            
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                
                try:
                    if not self._login_with_page(page, username, password):
                        self.debug_print("登录失败，无法上传活动")
                        return False
                    
                    page.goto(f"{self.base_url}/upload", timeout=30000)
                    page.wait_for_load_state("networkidle")
                    
                    page.set_input_files('input[type="file"]', file_path)
                    
                    page.wait_for_timeout(2000)
                    
                    if activity_name:
                        try:
                            page.fill('input[name="name"], input[name="title"]', activity_name)
                        except:
                            self.debug_print("未找到活动名称输入框，使用默认名称")
                    
                    page.click('button[type="submit"], button:has-text("Upload")')
                    
                    page.wait_for_timeout(3000)
                    
                    if "activities" in page.url or "success" in page.url.lower():
                        self.debug_print("上传成功")
                        return True
                    else:
                        self.debug_print(f"上传后URL: {page.url}")
                        return False
                    
                finally:
                    context.close()
                    browser.close()
                    
        except Exception as e:
            self.debug_print(f"上传文件到MyWhoosh失败: {e}")
            logger.error(f"上传文件到MyWhoosh失败: {e}")
            return False
    
    def get_activities_for_migration(self, batch_size: int = 10,
                                    after: Optional[datetime] = None,
                                    before: Optional[datetime] = None) -> List[Dict]:
        """获取用于历史迁移的活动列表"""
        print(f"获取MyWhoosh历史迁移活动，批次大小: {batch_size}")
        if after:
            print(f"开始时间: {after}")
        if before:
            print(f"结束时间: {before}")
        
        activities = self.get_activities(limit=batch_size, after=after, before=before)
        
        if not activities:
            print("未找到符合条件的活动")
            return []
        
        activities.sort(key=lambda x: self._parse_activity_date(x.get('date', '')) or datetime.min.replace(tzinfo=timezone.utc))
        
        print(f"最终返回{len(activities)}个活动用于迁移")
        
        if activities:
            first_activity = activities[0]
            last_activity = activities[-1]
            first_time = self._parse_activity_date(first_activity.get('date', ''))
            last_time = self._parse_activity_date(last_activity.get('date', ''))
            if first_time and last_time:
                print(f"活动时间范围: {first_time} 到 {last_time}")
        
        return activities

