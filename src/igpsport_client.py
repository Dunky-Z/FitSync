import os
import json
import uuid
import logging
import requests
import oss2
from typing import Dict, Tuple, Optional, List
from datetime import datetime

from config_manager import ConfigManager
from ui_utils import UIUtils
from database_manager import ActivityMetadata

logger = logging.getLogger(__name__)

class IGPSportClient:
    """IGPSport客户端"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[IGPSportClient] {message}")
    
    def is_configured(self) -> bool:
        """检查IGPSport是否已配置"""
        config = self.config_manager.get_platform_config("igpsport")
        return bool(config.get("login_token") or 
                   (config.get("username") and config.get("password")))
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 尝试使用已保存的token
            saved_token = self._get_saved_token()
            if saved_token:
                return self.test_token(saved_token)
            
            # 如果没有token，尝试获取凭据
            if self.is_configured():
                config = self.config_manager.get_platform_config("igpsport")
                username = config.get("username")
                password = config.get("password")
                if username and password:
                    token = self.login(username, password)
                    return bool(token)
            
            return False
        except Exception as e:
            self.debug_print(f"连接测试失败: {e}")
            return False
    
    def get_activities(self, limit: int = 30, 
                      after: Optional[datetime] = None,
                      before: Optional[datetime] = None) -> List[Dict]:
        """获取IGPSport活动列表（注意：IGPSport主要用于上传，不提供活动获取）"""
        self.debug_print("IGPSport主要用于上传活动，不支持获取活动列表")
        return []
    
    def convert_to_activity_metadata(self, activity_data: Dict) -> ActivityMetadata:
        """将IGPSport活动数据转换为ActivityMetadata（IGPSport主要用于上传）"""
        return ActivityMetadata(
            name=activity_data.get("name", "IGPSport活动"),
            sport_type=activity_data.get("sport_type", "unknown"),
            start_time=activity_data.get("start_time", ""),
            distance=float(activity_data.get("distance", 0)),
            duration=int(activity_data.get("duration", 0)),
            elevation_gain=float(activity_data.get("elevation_gain", 0))
        )
    
    def download_activity_file(self, activity_id: str, output_path: str) -> bool:
        """下载活动文件（IGPSport主要用于上传，不支持下载）"""
        self.debug_print("IGPSport主要用于上传活动，不支持下载活动文件")
        return False
    
    def get_credentials(self) -> Tuple[str, str]:
        """获取IGPSport登录凭据"""
        config = self.config_manager.get_platform_config("igpsport")
        
        # 检查是否已保存凭据
        saved_username = config.get("username", "")
        saved_password = config.get("password", "")
        
        if saved_username and saved_password:
            if UIUtils.ask_use_saved_credentials(saved_username):
                return saved_username, saved_password
        
        # 获取新的凭据
        username, password = UIUtils.ask_credentials("IGPSport")
        
        # 询问是否保存凭据
        if UIUtils.ask_save_credentials():
            config["username"] = username
            config["password"] = password
            self.config_manager.save_platform_config("igpsport", config)
            self.debug_print("IGPSport登录凭据已保存")
        
        return username, password
    
    def login(self, username: str, password: str) -> str:
        """登录IGPSport并获取token"""
        self.debug_print("正在登录IGPSport...")
        
        session = requests.Session()
        
        # 添加必要的header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://my.igpsport.com/',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # 登录请求
        login_data = {
            'username': username,
            'password': password
        }
        
        try:
            response = session.post('https://my.igpsport.com/Auth/Login', 
                                  data=login_data, 
                                  headers=headers, 
                                  allow_redirects=False)
            
            self.debug_print(f"登录响应状态码: {response.status_code}")
            
            if response.status_code in [200, 302]:
                # 提取登录token
                for cookie in session.cookies:
                    if cookie.name == 'loginToken':
                        self.debug_print("IGPSport登录成功")
                        # 保存token供下次使用
                        self._save_token(cookie.value)
                        return cookie.value
                
                # 如果没有找到cookie，尝试从响应中解析
                try:
                    if response.text:
                        result = response.json()
                        if 'token' in result:
                            self.debug_print("IGPSport登录成功")
                            self._save_token(result['token'])
                            return result['token']
                        elif 'data' in result and 'token' in result['data']:
                            self.debug_print("IGPSport登录成功")
                            self._save_token(result['data']['token'])
                            return result['data']['token']
                except Exception as e:
                    self.debug_print(f"解析响应失败: {e}")
            
            self.debug_print(f"登录失败，响应内容: {response.text[:200] if response.text else 'No content'}")
            
        except Exception as e:
            self.debug_print(f"登录请求异常: {e}")
        
        # 如果还是失败，提供一个选项让用户手动输入token
        manual_token = UIUtils.ask_manual_token("IGPSport loginToken")
        if manual_token:
            self.debug_print("使用手动输入的Token")
            self._save_token(manual_token.strip())
            return manual_token.strip()
        
        raise ValueError("IGPSport登录失败，请检查用户名和密码")
    
    def _save_token(self, token: str) -> None:
        """保存token到配置"""
        config = self.config_manager.get_platform_config("igpsport")
        config["login_token"] = token
        self.config_manager.save_platform_config("igpsport", config)
        self.debug_print("IGPSport Token已保存")
    
    def _get_saved_token(self) -> str:
        """获取已保存的token"""
        config = self.config_manager.get_platform_config("igpsport")
        return config.get("login_token", "")
    
    def test_token(self, token: str) -> bool:
        """测试IGPSport token是否有效"""
        try:
            url = "https://prod.zh.igpsport.com/service/mobile/api/AliyunService/GetOssTokenForApp"
            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_oss_token(self, login_token: str) -> dict:
        """获取阿里云OSS临时凭证"""
        self.debug_print("获取OSS上传凭证...")
        
        url = "https://prod.zh.igpsport.com/service/mobile/api/AliyunService/GetOssTokenForApp"
        headers = {
            'Authorization': f'Bearer {login_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.debug_print(f"请求URL: {url}")
        self.debug_print(f"Authorization: Bearer {login_token[:20]}...")
        
        response = requests.get(url, headers=headers)
        
        self.debug_print(f"响应状态码: {response.status_code}")
        self.debug_print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.debug_print(f"完整响应数据: {data}")
                
                if 'data' in data:
                    oss_data = data['data']
                    self.debug_print("OSS凭证获取成功")
                    self.debug_print(f"AccessKeyId: {oss_data.get('accessKeyId', 'Not found')}")
                    self.debug_print(f"SecurityToken前50字符: {oss_data.get('securityToken', 'Not found')[:50]}...")
                    return oss_data
                else:
                    self.debug_print("响应中没有找到data字段")
                    self.debug_print(f"完整响应: {data}")
            except Exception as e:
                self.debug_print(f"JSON解析失败: {e}")
                self.debug_print(f"响应文本: {response.text}")
        else:
            self.debug_print("获取OSS凭证失败")
            self.debug_print(f"响应文本: {response.text}")
        
        raise ValueError("获取OSS凭证失败")
    
    def upload_to_oss(self, file_path: str, oss_credentials: dict) -> str:
        """上传文件到阿里云OSS"""
        self.debug_print("正在上传文件到OSS...")
        
        # 生成唯一的OSS文件名
        oss_name = f"1456042-{str(uuid.uuid4())}"
        
        self.debug_print(f"本地文件: {file_path}")
        self.debug_print(f"OSS文件名: {oss_name}")
        self.debug_print(f"文件大小: {os.path.getsize(file_path)} bytes")
        
        try:
            # 使用OSS凭证创建认证对象
            auth = oss2.StsAuth(
                oss_credentials['accessKeyId'],
                oss_credentials['accessKeySecret'], 
                oss_credentials['securityToken']
            )
            
            # 创建OSS bucket对象
            bucket = oss2.Bucket(
                auth, 
                oss_credentials['endpoint'], 
                oss_credentials['bucketName']
            )
            
            self.debug_print(f"OSS Endpoint: {oss_credentials['endpoint']}")
            self.debug_print(f"OSS Bucket: {oss_credentials['bucketName']}")
            self.debug_print(f"使用AccessKey: {oss_credentials['accessKeyId']}")
            
            # 上传文件
            self.debug_print("开始真正的OSS上传...")
            result = bucket.put_object_from_file(oss_name, file_path)
            
            self.debug_print(f"OSS上传结果状态: {result.status}")
            self.debug_print(f"请求ID: {result.request_id}")
            self.debug_print(f"ETag: {result.etag}")
            
            if result.status == 200:
                self.debug_print("文件上传成功")
                
                # 验证文件是否真的上传成功
                if bucket.object_exists(oss_name):
                    self.debug_print("文件在OSS中确认存在")
                    
                    # 获取文件信息
                    meta = bucket.head_object(oss_name)
                    self.debug_print(f"OSS中文件大小: {meta.content_length} bytes")
                    self.debug_print(f"上传时间: {meta.last_modified}")
                else:
                    self.debug_print("警告：文件在OSS中不存在")
            else:
                self.debug_print(f"OSS上传失败，状态码: {result.status}")
                raise Exception(f"OSS上传失败，状态码: {result.status}")
            
            return oss_name
            
        except Exception as e:
            logger.error(f"OSS上传失败: {e}")
            self.debug_print(f"OSS上传异常: {e}")
            self.debug_print("错误详情:")
            self.debug_print(f"  - AccessKeyId: {oss_credentials.get('accessKeyId', 'Missing')}")
            self.debug_print(f"  - Endpoint: {oss_credentials.get('endpoint', 'Missing')}")
            self.debug_print(f"  - BucketName: {oss_credentials.get('bucketName', 'Missing')}")
            raise
    
    def notify_server(self, login_token: str, file_name: str, oss_name: str) -> None:
        """通知IGPSport服务器文件已上传"""
        self.debug_print("通知IGPSport服务器...")
        
        url = "https://prod.zh.igpsport.com/service/web-gateway/web-analyze/activity/uploadByOss"
        
        data = {
            'fileName': file_name,
            'ossName': oss_name
        }
        
        headers = {
            'Authorization': f'Bearer {login_token}',
            'Content-Type': 'application/json',
            'Referer': 'https://app.zh.igpsport.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        self.debug_print(f"通知URL: {url}")
        self.debug_print(f"发送数据: {data}")
        self.debug_print(f"使用Token: {login_token[:20]}...")
        
        response = requests.post(url, json=data, headers=headers)
        
        self.debug_print(f"通知响应状态码: {response.status_code}")
        self.debug_print(f"响应头: {dict(response.headers)}")
        self.debug_print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                self.debug_print(f"解析后的响应: {result}")
                self.debug_print("IGPSport上传通知成功")
            except:
                self.debug_print("IGPSport上传通知成功（无JSON响应）")
        else:
            self.debug_print(f"IGPSport通知失败 (状态码: {response.status_code})")
            self.debug_print(f"可能的错误原因：")
            self.debug_print(f"   - Token已过期")
            self.debug_print(f"   - OSS文件名无效")
            self.debug_print(f"   - 服务器内部错误")
            raise Exception(f"IGPSport通知失败: {response.status_code}")
    
    def upload_file(self, file_path: str, activity_name: str = None) -> bool:
        """完整的IGPSport上传流程"""
        try:
            # 1. 首先尝试使用保存的token
            saved_token = self._get_saved_token()
            login_token = None
            
            if saved_token:
                self.debug_print("使用已保存的IGPSport Token进行认证...")
                if self.test_token(saved_token):
                    self.debug_print("IGPSport Token有效，跳过登录")
                    login_token = saved_token
                else:
                    self.debug_print("保存的IGPSport Token已过期，需要重新登录...")
            
            # 2. 如果没有有效的token，进行登录
            if not login_token:
                username, password = self.get_credentials()
                login_token = self.login(username, password)
            
            # 3. 获取OSS凭证
            oss_credentials = self.get_oss_token(login_token)
            
            # 4. 上传文件到OSS
            # 使用原活动名称，如果没有提供则使用文件名
            if activity_name:
                # 清理活动名称，移除不合法字符，并添加文件扩展名
                import re
                clean_name = re.sub(r'[<>:"/\\|?*]', '_', activity_name)
                file_ext = os.path.splitext(file_path)[1]  # 获取原文件扩展名
                file_name = f"{clean_name}{file_ext}"
                self.debug_print(f"使用原活动名称: {activity_name} -> {file_name}")
            else:
                file_name = os.path.basename(file_path)
                self.debug_print(f"使用文件名: {file_name}")
            
            oss_name = self.upload_to_oss(file_path, oss_credentials)
            
            # 5. 通知IGPSport
            self.notify_server(login_token, file_name, oss_name)
            
            self.debug_print(f"文件 {file_name} 已成功上传到IGPSport！")
            return True
            
        except Exception as e:
            logger.error(f"IGPSport上传失败: {e}")
            self.debug_print(f"上传失败: {e}")
            return False 