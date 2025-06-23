import os
import json
import uuid
import logging
import requests
import oss2
import time
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timezone

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
        return bool(config.get("access_token") or 
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
        """获取IGPSport活动列表"""
        try:
            # 获取Bearer Token
            auth_token = self._get_saved_token()
            
            if not auth_token or not self.test_token(auth_token):
                # 如果没有有效token，尝试登录获取
                username, password = self.get_credentials()
                auth_token = self.login(username, password)
            
            activities = []
            page = 1
            collected_count = 0
            
            # 分页获取活动，直到达到limit或没有更多数据
            while collected_count < limit:
                self.debug_print(f"获取第{page}页活动...")
                
                # 使用新的API接口
                url = f"https://prod.zh.igpsport.com/service/web-gateway/web-analyze/activity/queryMyActivity"
                params = {
                    'pageNo': page,
                    'pageSize': 20,
                    'reqType': 0,
                    'sort': 1
                }
                
                headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'Authorization': f'Bearer {auth_token}',
                    'Origin': 'https://app.zh.igpsport.com',
                    'Referer': 'https://app.zh.igpsport.com/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                    'timezone': 'Asia/Shanghai',
                    'qiwu-app-version': '1.0.0'
                }
                
                self.debug_print(f"请求URL: {url}")
                self.debug_print(f"参数: {params}")
                
                response = requests.get(url, params=params, headers=headers, timeout=30)
                self.debug_print(f"响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('code') != 0:
                        self.debug_print(f"API返回错误: {data.get('message', 'Unknown error')}")
                        break
                    
                    page_activities = data.get('data', {}).get('rows', [])
                    
                    if not page_activities:
                        self.debug_print("没有更多活动，停止获取")
                        break
                    
                    # 过滤时间范围
                    for activity in page_activities:
                        if collected_count >= limit:
                            break
                            
                        # 解析活动时间 - 使用startTime字段
                        start_time_str = activity.get('startTime', '')
                        if start_time_str:
                            try:
                                # IGPSport API返回的时间格式是 "YYYY.MM.DD"
                                if '.' in start_time_str and len(start_time_str) == 10:
                                    # 转换 "YYYY.MM.DD" 格式为datetime
                                    activity_time = datetime.strptime(start_time_str, "%Y.%m.%d")
                                    activity_time = activity_time.replace(tzinfo=timezone.utc)
                                else:
                                    # 尝试解析ISO格式时间
                                    activity_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                                
                                # 检查时间范围
                                if after and activity_time < after:
                                    continue
                                if before and activity_time > before:
                                    continue
                                    
                            except ValueError:
                                self.debug_print(f"无法解析活动时间: {start_time_str}")
                                continue
                        
                        activities.append(activity)
                        collected_count += 1
                    
                    self.debug_print(f"第{page}页获取到{len(page_activities)}个活动，已收集{collected_count}个")
                    page += 1
                    
                    # 添加延迟避免请求过快
                    time.sleep(0.5)
                else:
                    self.debug_print(f"获取活动列表失败: {response.text}")
                    break
            
            self.debug_print(f"总共获取到{len(activities)}个IGPSport活动")
            return activities
                
        except Exception as e:
            self.debug_print(f"获取IGPSport活动失败: {e}")
            return []
    
    def convert_to_activity_metadata(self, activity_data: Dict) -> ActivityMetadata:
        """将IGPSport活动数据转换为ActivityMetadata"""
        try:
            # 根据实际API响应修正字段名
            name = activity_data.get("title", "IGPSport活动")
            sport_type = self._normalize_sport_type(activity_data.get("exerciseType", 0))
            
            # 时间处理 - 使用startTime字段
            start_time_str = activity_data.get("startTime", "")
            if start_time_str:
                try:
                    # IGPSport API返回的时间格式是 "YYYY.MM.DD"
                    if '.' in start_time_str and len(start_time_str) == 10:
                        # 转换 "YYYY.MM.DD" 格式为ISO格式
                        activity_time = datetime.strptime(start_time_str, "%Y.%m.%d")
                        start_time = activity_time.isoformat() + 'Z'
                    else:
                        # 如果是其他格式，直接使用
                        start_time = start_time_str
                except Exception:
                    self.debug_print(f"无法解析时间格式: {start_time_str}")
                    start_time = ""
            else:
                start_time = ""
            
            # 距离和时长 - 根据实际API字段名修正
            distance = float(activity_data.get("rideDistance", 0))      # 米
            duration = int(activity_data.get("totalMovingTime", 0))     # 秒
            
            # 海拔增益 - 从实际数据看没有这个字段，设为0
            elevation_gain = float(activity_data.get("totalAscent", 0))  # 米
            
            return ActivityMetadata(
                name=name,
                sport_type=sport_type,
                start_time=start_time,
                distance=distance,
                duration=duration,
                elevation_gain=elevation_gain
            )
            
        except Exception as e:
            logger.error(f"转换IGPSport活动元数据失败: {e}")
            self.debug_print(f"活动数据: {activity_data}")
            return ActivityMetadata(
                name="转换失败的活动",
                sport_type="other",
                start_time="",
                distance=0,
                duration=0
            )
    
    def _normalize_sport_type(self, igpsport_type: int) -> str:
        """标准化IGPSport运动类型"""
        type_mapping = {
            0: "cycling",      # 骑行（从JSON数据看，SportType为0）
            1: "running",      # 跑步
            2: "walking",      # 步行
            3: "hiking",       # 徒步
            4: "swimming",     # 游泳
            5: "other",        # 其他
            6: "indoor_cycling", # 室内骑行
            7: "strength_training", # 力量训练
        }
        
        return type_mapping.get(igpsport_type, "other")
    
    def download_activity_file(self, activity_id: str, output_path: str) -> bool:
        """下载IGPSport活动文件"""
        try:
            # 获取Bearer Token
            auth_token = self._get_saved_token()
            
            if not auth_token or not self.test_token(auth_token):
                # 如果没有有效token，尝试登录获取
                username, password = self.get_credentials()
                auth_token = self.login(username, password)
            
            if not auth_token:
                self.debug_print("无法获取有效的认证Token")
                return False
            
            self.debug_print(f"下载IGPSport活动文件: {activity_id}")
            
            # 第一步：获取活动详情，包括下载链接
            detail_url = f"https://prod.zh.igpsport.com/service/web-gateway/web-analyze/activity/queryActivityDetail/{activity_id}"
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Authorization': f'Bearer {auth_token}',
                'Origin': 'https://app.zh.igpsport.com',
                'Referer': 'https://app.zh.igpsport.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'timezone': 'Asia/Shanghai',
                'qiwu-app-version': '1.0.0'
            }
            
            self.debug_print(f"获取活动详情URL: {detail_url}")
            
            response = requests.get(detail_url, headers=headers, timeout=30)
            self.debug_print(f"详情响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                self.debug_print(f"获取活动详情失败: {response.text}")
                return False
            
            detail_data = response.json()
            if detail_data.get('code') != 0:
                self.debug_print(f"API返回错误: {detail_data.get('message', 'Unknown error')}")
                return False
            
            # 获取FIT文件下载链接
            activity_detail = detail_data.get('data', {})
            fit_url = activity_detail.get('fitUrl')
            
            if not fit_url:
                self.debug_print("活动详情中没有找到FIT文件下载链接")
                return False
            
            self.debug_print(f"找到FIT文件下载链接: {fit_url}")
            
            # 第二步：下载FIT文件
            download_response = requests.get(fit_url, timeout=60)
            self.debug_print(f"下载响应状态码: {download_response.status_code}")
            
            if download_response.status_code != 200:
                self.debug_print(f"下载文件失败: {download_response.text}")
                return False
            
            # 检查响应内容类型
            content_type = download_response.headers.get('Content-Type', '').lower()
            self.debug_print(f"Content-Type: {content_type}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存文件
            with open(output_path, 'wb') as f:
                f.write(download_response.content)
            
            file_size = len(download_response.content)
            self.debug_print(f"文件已保存到: {output_path}")
            self.debug_print(f"文件大小: {file_size} bytes")
            
            # 验证文件是否有效（FIT文件至少应该有一定大小）
            if file_size < 100:
                self.debug_print("下载的文件过小，可能无效")
                return False
            
            # 验证文件头是否为FIT格式
            with open(output_path, 'rb') as f:
                header = f.read(14)  # 读取FIT文件头（通常是14字节）
                
                # FIT文件头验证：
                # 1. 文件至少有14字节
                # 2. 第8-11字节应该是".FIT"字符串
                if len(header) >= 14:
                    # 检查第8-11字节是否为".FIT"
                    fit_signature = header[8:12]
                    if fit_signature == b'.FIT':
                        self.debug_print("FIT文件头验证通过")
                        return True
                    else:
                        self.debug_print(f"FIT签名验证失败: {fit_signature}")
                        # 如果签名不匹配，但文件大小合理，可能是有效的FIT文件
                        # 某些设备可能不严格遵循标准
                        if file_size > 1000:  # 如果文件大于1KB，可能是有效的
                            self.debug_print("文件大小合理，可能是有效的FIT文件，跳过严格验证")
                            return True
                        return False
                else:
                    self.debug_print(f"文件头长度不足: {len(header)} bytes")
                    # 检查是否是HTML内容
                    f.seek(0)
                    first_bytes = f.read(100)
                    if b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
                        self.debug_print("下载的是HTML页面，不是FIT文件")
                        return False
                    return False
                    
        except Exception as e:
            self.debug_print(f"下载IGPSport活动文件异常: {e}")
            logger.error(f"下载IGPSport活动文件失败: {e}")
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
        """登录IGPSport并获取Bearer Token"""
        self.debug_print("正在登录IGPSport...")
        
        try:
            # 获取access token
            login_url = "https://prod.zh.igpsport.com/service/auth/account/login"
            login_data = {
                'username': username,
                'password': password,
                'appId': 'igpsport-web'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://app.zh.igpsport.com',
                'Referer': 'https://app.zh.igpsport.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
            }
            
            self.debug_print("获取access token...")
            response = requests.post(login_url, json=login_data, headers=headers, timeout=30)
            self.debug_print(f"登录响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('code') != 0:
                    error_msg = response_data.get('message', '登录失败')
                    self.debug_print(f"登录失败: {error_msg}")
                    raise ValueError(f"IGPSport登录失败: {error_msg}")
                
                access_token = response_data['data']['access_token']
                self.debug_print("IGPSport登录成功，获取到access token")
                
                # 保存token供下次使用
                self._save_token(access_token)
                return access_token
            else:
                self.debug_print(f"登录请求失败，状态码: {response.status_code}")
                self.debug_print(f"响应内容: {response.text[:200]}")
                raise ValueError("IGPSport登录请求失败")
                
        except Exception as e:
            self.debug_print(f"登录过程异常: {e}")
            
            # 如果自动登录失败，提供手动输入token的选项
            manual_token = UIUtils.ask_manual_token("IGPSport Bearer Token")
            if manual_token:
                self.debug_print("使用手动输入的Token")
                self._save_token(manual_token.strip())
                return manual_token.strip()
            
            raise ValueError(f"IGPSport登录失败: {e}")
    
    def _save_token(self, token: str) -> None:
        """保存Bearer Token到配置"""
        config = self.config_manager.get_platform_config("igpsport")
        config["access_token"] = token
        self.config_manager.save_platform_config("igpsport", config)
        self.debug_print("IGPSport Token已保存")
    
    def _get_saved_token(self) -> str:
        """获取已保存的Bearer Token"""
        config = self.config_manager.get_platform_config("igpsport")
        return config.get("access_token", "")
    
    def test_token(self, token: str) -> bool:
        """测试IGPSport Bearer Token是否有效"""
        try:
            if not token or token.strip() == "":
                return False
                
            # 尝试获取活动列表的第一页来测试token是否有效
            url = "https://prod.zh.igpsport.com/service/web-gateway/web-analyze/activity/queryMyActivity"
            params = {
                'pageNo': 1,
                'pageSize': 1,
                'reqType': 0,
                'sort': 1
            }
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Authorization': f'Bearer {token}',
                'Origin': 'https://app.zh.igpsport.com',
                'Referer': 'https://app.zh.igpsport.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'timezone': 'Asia/Shanghai',
                'qiwu-app-version': '1.0.0'
            }
            
            self.debug_print("测试Token有效性...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            self.debug_print(f"Token测试响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # 如果能成功解析JSON且code为0，说明token有效
                    is_valid = data.get('code') == 0
                    self.debug_print(f"Token有效性: {is_valid}")
                    return is_valid
                except:
                    self.debug_print("Token测试: JSON解析失败")
                    return False
            elif response.status_code in [401, 403]:
                self.debug_print("Token测试: 认证失败")
                return False
            else:
                self.debug_print(f"Token测试: 响应状态码异常 {response.status_code}")
                return False
        except Exception as e:
            self.debug_print(f"Token测试异常: {e}")
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
            auth_token = None
            
            if saved_token:
                self.debug_print("使用已保存的IGPSport Token进行认证...")
                if self.test_token(saved_token):
                    self.debug_print("IGPSport Token有效，跳过登录")
                    auth_token = saved_token
                else:
                    self.debug_print("保存的IGPSport Token已过期，需要重新登录...")
            
            # 2. 如果没有有效的token，进行登录
            if not auth_token:
                username, password = self.get_credentials()
                auth_token = self.login(username, password)
            
            # 3. 获取OSS凭证
            oss_credentials = self.get_oss_token(auth_token)
            
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
            self.notify_server(auth_token, file_name, oss_name)
            
            self.debug_print(f"文件 {file_name} 已成功上传到IGPSport！")
            return True
            
        except Exception as e:
            logger.error(f"IGPSport上传失败: {e}")
            self.debug_print(f"上传失败: {e}")
            return False 