import os
import sys
from datetime import datetime, timezone, timedelta

# 获取项目根目录路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 动态添加Python模块搜索路径
user_site_packages = os.path.expanduser("~/.local/lib/python3.10/site-packages")
system_dist_packages = "/usr/lib/python3/dist-packages"

# 将路径添加到sys.path开头，优先级更高
if user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)
if system_dist_packages not in sys.path:
    sys.path.insert(0, system_dist_packages)
    
import time
import logging
import requests
import json
from typing import List, Dict, Optional, Tuple

from config_manager import ConfigManager
from file_utils import FileUtils
from ui_utils import UIUtils
from database_manager import ActivityMetadata

logger = logging.getLogger(__name__)

class StravaClient:
    """扩展的Strava客户端，支持双向同步功能"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        self.base_url = "https://www.strava.com/api/v3"
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[StravaClient] {message}")
    
    def is_configured(self) -> bool:
        """检查Strava是否已配置"""
        config = self.config_manager.get_platform_config("strava")
        return bool(config.get("client_id") and config.get("client_secret") and config.get("refresh_token"))
    
    def _refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        config = self.config_manager.get_platform_config("strava")
        
        refresh_data = {
            'client_id': config.get("client_id"),
            'client_secret': config.get("client_secret"),
            'refresh_token': config.get("refresh_token"),
            'grant_type': 'refresh_token'
        }
        
        try:
            print("刷新Strava访问令牌...")
            response = requests.post('https://www.strava.com/oauth/token', data=refresh_data)
            print(f"Token刷新响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                
                # 更新配置中的访问令牌
                config["access_token"] = token_data['access_token']
                config["refresh_token"] = token_data['refresh_token']
                self.config_manager.save_platform_config("strava", config)
                
                print("Strava访问令牌刷新成功")
                return True
            else:
                print(f"Token刷新失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"刷新Strava访问令牌失败: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        config = self.config_manager.get_platform_config("strava")
        access_token = config.get("access_token")
        
        if not access_token:
            if not self._refresh_access_token():
                raise Exception("无法获取有效的访问令牌")
            access_token = config.get("access_token")
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_activities(self, limit: int = 30, page: int = 1, 
                     after: Optional[datetime] = None, 
                     before: Optional[datetime] = None) -> List[Dict]:
        """获取活动列表，支持重试机制"""
        max_retries = 3
        retry_delay = 5  # 初始重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                headers = self._get_headers()
                params = {
                    'per_page': min(limit, 200),  # Strava限制每页最多200
                    'page': page
                }
                
                # 添加时间参数到API请求中
                if after:
                    params['after'] = int(after.timestamp())
                if before:
                    params['before'] = int(before.timestamp())
                
                if attempt > 0:
                    print(f"第{attempt + 1}次尝试获取活动列表...")
                else:
                    print(f"获取Strava活动列表，限制: {limit}")
                    
                response = requests.get(f"{self.base_url}/athlete/activities", 
                                      headers=headers, params=params, timeout=30)
                print(f"活动列表响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    activities = response.json()
                    print(f"成功获取{len(activities)}个活动")
                    return activities
                    
                elif response.status_code == 401:
                    # Token可能过期，尝试刷新
                    if self._refresh_access_token():
                        headers = self._get_headers()
                        response = requests.get(f"{self.base_url}/athlete/activities", 
                                              headers=headers, params=params, timeout=30)
                        if response.status_code == 200:
                            activities = response.json()
                            print(f"重试后成功获取{len(activities)}个活动")
                            return activities
                    
                    raise Exception(f"认证失败: {response.text}")
                    
                elif response.status_code == 429:
                    # 速率限制
                    retry_after = int(response.headers.get('Retry-After', retry_delay * (attempt + 1)))
                    print(f"⚠️  达到API速率限制，将在{retry_after}秒后重试...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        raise Exception("API速率限制，请稍后再试")
                        
                elif response.status_code in [500, 502, 503, 504, 597]:
                    # 服务器错误或临时不可用
                    error_msg = "Strava服务暂时不可用" if response.status_code == 597 else f"服务器错误 {response.status_code}"
                    
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"⚠️  {error_msg}，将在{wait_time}秒后重试（剩余{max_retries - attempt - 1}次）...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"{error_msg}，已重试{max_retries}次")
                else:
                    raise Exception(f"获取活动失败: {response.status_code} - {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⚠️  请求超时，将在{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("获取Strava活动超时")
                    return []
                    
            except Exception as e:
                if attempt < max_retries - 1 and "temporarily unavailable" in str(e).lower():
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⚠️  Strava服务暂时不可用，将在{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                    
                logger.error(f"获取Strava活动失败: {e}")
                return []
        
        return []
    
    def get_activities_in_batches(self, total_limit: int = 50, 
                                after: Optional[datetime] = None,
                                before: Optional[datetime] = None) -> List[Dict]:
        """分批获取活动"""
        all_activities = []
        page = 1
        per_page = min(200, total_limit)  # 使用更大的页面大小，减少请求次数
        
        while len(all_activities) < total_limit:
            remaining = total_limit - len(all_activities)
            current_limit = min(per_page, remaining)
            
            print(f"获取第{page}页活动，每页{current_limit}个")
            # 直接在API请求中使用时间参数，避免客户端过滤
            activities = self.get_activities(limit=current_limit, page=page, after=after, before=before)
            
            if not activities:
                print("没有更多活动，停止获取")
                break
            
            # 由于API已经按时间过滤，这里不需要再次过滤
            all_activities.extend(activities)
            
            # 如果这一页的活动数量少于请求数量，说明没有更多了
            if len(activities) < current_limit:
                print("已获取所有可用活动")
                break
                
            # 如果已经获取足够的活动，停止
            if len(all_activities) >= total_limit:
                print(f"已获取足够的活动数量: {len(all_activities)}")
                break
                
            page += 1
        
        print(f"总共获取{len(all_activities)}个活动")
        return all_activities[:total_limit]
    
    def convert_to_activity_metadata(self, strava_activity: Dict) -> ActivityMetadata:
        """将Strava活动数据转换为ActivityMetadata"""
        return ActivityMetadata(
            name=strava_activity.get("name", "未命名活动"),
            sport_type=strava_activity.get("sport_type", "unknown"),
            start_time=strava_activity.get("start_date", ""),
            distance=float(strava_activity.get("distance", 0)),
            duration=int(strava_activity.get("elapsed_time", 0)),
            elevation_gain=float(strava_activity.get("total_elevation_gain", 0))
        )
    
    def get_activity_details(self, activity_id: str) -> Dict:
        """获取活动详细信息，支持重试机制"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                access_token = self._get_headers()['Authorization'].split(' ')[1]
                self.debug_print(f"获取活动{activity_id}的详细信息")
                
                url = f"{self.base_url}/activities/{activity_id}"
                headers = {"Authorization": f"Bearer {access_token}"}
                
                response = requests.get(url, headers=headers, timeout=30)
                self.debug_print(f"活动详情响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    # 尝试刷新token
                    if self._refresh_access_token():
                        continue
                    else:
                        raise ValueError(f"无法获取活动{activity_id}的详情：认证失败")
                elif response.status_code in [500, 502, 503, 504, 597]:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        self.debug_print(f"服务器错误，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f"无法获取活动{activity_id}的详情：服务器错误")
                else:
                    self.debug_print(f"获取活动详情失败: {response.text[:200]}")
                    raise ValueError(f"无法获取活动{activity_id}的详情")
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    self.debug_print(f"请求超时，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"获取Strava活动详情超时: {activity_id}")
                    raise
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                    
                logger.error(f"获取Strava活动详情失败: {e}")
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
    
    def _is_manual_activity(self, activity_data: Dict) -> bool:
        """检查活动是否为手动创建（没有原始文件）"""
        try:
            # 检查活动是否有设备信息
            device_name = activity_data.get('device_name')
            upload_id = activity_data.get('upload_id')
            external_id = activity_data.get('external_id')
            
            # 手动创建的活动通常没有这些字段或者为空
            has_device = device_name and device_name.strip()
            has_upload_id = upload_id is not None
            has_external_id = external_id and external_id.strip()
            
            # 检查是否有GPS数据
            has_start_latlng = activity_data.get('start_latlng') is not None
            has_map = activity_data.get('map', {}).get('polyline') is not None
            
            # 手动活动的判断逻辑：
            # 1. 没有设备名称
            # 2. 没有上传ID
            # 3. 没有外部ID
            # 4. 可能没有GPS数据
            
            is_manual = (not has_device and not has_upload_id and not has_external_id)
            
            if is_manual:
                self.debug_print(f"检测到手动创建活动: {activity_data.get('name', 'Unknown')}")
                self.debug_print(f"  - Device: {device_name}")
                self.debug_print(f"  - Upload ID: {upload_id}")
                self.debug_print(f"  - External ID: {external_id}")
                self.debug_print(f"  - Has GPS: {has_start_latlng or has_map}")
            
            return is_manual
            
        except Exception as e:
            self.debug_print(f"检查手动活动失败: {e}")
            return False
    
    def _has_original_file(self, activity_data: Dict) -> bool:
        """检查活动是否有原始文件可下载"""
        # 如果是手动创建的活动，通常没有原始文件
        if self._is_manual_activity(activity_data):
            return False
        
        # 检查活动类型和数据源
        activity_type = activity_data.get('type', '').lower()
        device_name = activity_data.get('device_name', '').lower()
        
        # 某些活动类型更可能有原始文件
        likely_has_file_types = [
            'ride', 'run', 'swim', 'hike', 'walk', 'cycling', 
            'running', 'swimming', 'hiking', 'walking'
        ]
        
        # 某些设备名称表明有原始文件
        device_indicators = [
            'garmin', 'polar', 'suunto', 'wahoo', 'coros', 'fitbit',
            'zwift', 'trainer', 'power', 'gps', 'watch'
        ]
        
        has_likely_type = any(t in activity_type for t in likely_has_file_types)
        has_device_indicator = any(d in device_name for d in device_indicators)
        
        # 如果有设备信息或者是常见的运动类型，可能有原始文件
        return has_device_indicator or (has_likely_type and activity_data.get('upload_id') is not None)

    def download_activity_file(self, activity_id: str, save_path: str) -> bool:
        """下载活动文件到指定路径
        
        注意：Strava的export_original端点是网页端点，需要使用Cookie认证，不支持API token
        """
        try:
            self.debug_print(f"下载Strava活动文件: {activity_id}")
            
            # 首先获取活动详情，检查是否有原始文件
            activity_details = self.get_activity_details(activity_id)
            if activity_details:
                if not self._has_original_file(activity_details):
                    self.debug_print(f"活动 {activity_id} 是手动创建的活动，没有原始文件可下载")
                    print(f"跳过手动创建的活动: {activity_details.get('name', activity_id)}")
                    return False
            
            activity_name = activity_details.get('name') if activity_details else None
            download_url = f"https://www.strava.com/activities/{activity_id}/export_original"
            
            # export_original是网页端点，必须使用Cookie认证
            cookie = self.config_manager.get_platform_config("strava").get("cookie", "")
            if not cookie:
                print("\n⚠️  Strava Cookie未配置或已过期")
                print("下载原始文件需要Cookie认证（export_original端点不支持API token）")
                print("\n请按以下步骤更新Cookie：")
                print("1. 在浏览器中登录 https://www.strava.com")
                print("2. 按F12打开开发者工具")
                print("3. 在Network标签中访问任意活动页面")
                print("4. 复制请求头中的Cookie值")
                print("5. 更新.app_config.json文件中的 strava.cookie 字段\n")
                return False
            
            self.debug_print("使用Cookie认证下载原始文件...")
            success, downloaded_file = self._try_download_with_cookie(
                download_url,
                activity_id,
                cookie,
                activity_name
            )
            
            # 如果Cookie失效，提示用户更新
            if success and not downloaded_file:
                # success=True 但 downloaded_file=None 表示需要重新认证
                print("\n⚠️  Cookie已过期，请更新Cookie")
                print("请按以下步骤更新Cookie：")
                print("1. 在浏览器中登录 https://www.strava.com")
                print("2. 按F12打开开发者工具")
                print("3. 在Network标签中访问任意活动页面")
                print("4. 复制请求头中的Cookie值")
                print("5. 更新.app_config.json文件中的 strava.cookie 字段\n")
                return False
            
            if success and downloaded_file and os.path.exists(downloaded_file):
                # 移动到指定路径
                if downloaded_file != save_path:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    os.rename(downloaded_file, save_path)
                
                self.debug_print(f"文件已保存到: {save_path}")
                return True
            else:
                self.debug_print(f"下载活动文件失败: {activity_id}")
                return False
                
        except Exception as e:
            logger.error(f"下载Strava活动文件失败: {e}")
            self.debug_print(f"下载失败: {e}")
            return False
    
    def _download_with_cookie(self, url: str, activity_id: str, activity_name: Optional[str] = None) -> Optional[str]:
        """使用Cookie下载活动文件"""
        try:
            config = self.config_manager.get_platform_config("strava")
            cookie = config.get("cookie", "")
            
            if not cookie:
                print("未找到Strava Cookie，请重新配置")
                return None
            
            self.debug_print(f"活动名称: {activity_name}")
            self.debug_print(f"下载URL: {url}")
            self.debug_print("使用已保存的Cookie进行下载...")
            
            return self._try_download_with_cookie(url, activity_id, cookie, activity_name)
            
        except Exception as e:
            logger.error(f"Cookie下载失败: {e}")
            return None
    
    def _try_download_with_cookie(self, url: str, activity_id: str, cookie: str, 
                                  activity_name: Optional[str] = None, max_retries: int = 10) -> Tuple[bool, Optional[str]]:
        """尝试使用Cookie下载文件，支持重试机制处理202状态码
        
        Args:
            url: 下载URL
            activity_id: 活动ID
            cookie: 认证Cookie
            activity_name: 活动名称（可选）
            max_retries: 最大重试次数，默认10次
            
        Returns:
            (需要重新认证?, 下载的文件路径或None)
        """
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # 优化等待策略：前3次使用指数退避(2,4,8秒)，之后固定10秒
                    if attempt <= 3:
                        wait_time = 2 ** attempt  # 2, 4, 8秒
                    else:
                        wait_time = 10  # 之后固定10秒
                    
                    self.debug_print(f"第{attempt + 1}次重试，等待{wait_time}秒...")
                    time.sleep(wait_time)
                
                self.debug_print(f"发送下载请求（第{attempt + 1}次尝试）...")
                response = requests.get(url, headers=headers, timeout=30)
                
                self.debug_print(f"响应状态码: {response.status_code}")
                self.debug_print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                self.debug_print(f"Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    # 检查是否返回了HTML页面（表示没有原始文件或需要登录）
                    if 'text/html' in content_type:
                        self.debug_print("返回HTML页面，检查原因...")
                        
                        # 检查响应内容
                        response_text_lower = response.text.lower() if response.text else ""
                        response_preview = response.text[:200] if response.text else ""
                        self.debug_print(f"响应内容开头: {response_preview}")
                        
                        # 首先检查是否是登录页面（Cookie失效）
                        login_indicators = [
                            'log in', 'sign in', 'login', 'signin',
                            'log_in', 'sign_in', 'create a new account',
                            'join for free', 'remember me', 'forgot password'
                        ]
                        if any(indicator in response_text_lower for indicator in login_indicators):
                            self.debug_print("检测到登录页面，Cookie已失效")
                            print("Cookie已过期，请重新配置Cookie")
                            return True, None  # 返回True表示需要重新认证
                        
                        # 检查是否是手动创建的活动页面
                        manual_indicators = [
                            'manual activity', 'manually created', '手动创建',
                            'no file available', 'file not available'
                        ]
                        if any(indicator in response_text_lower for indicator in manual_indicators):
                            self.debug_print("确认为手动创建的活动，没有原始文件")
                            print(f"活动 '{activity_name or activity_id}' 是手动创建的，跳过下载")
                            return False, None  # 返回False表示没有文件可下载
                        
                        # 其他HTML情况，可能是Cookie问题或其他错误
                        self.debug_print("返回未知HTML页面，可能是Cookie问题")
                        print("下载失败：收到HTML页面而非文件，可能是Cookie问题")
                        return True, None
                    
                    # 检查是否为有效的文件格式
                    valid_content_types = [
                        'application/octet-stream',
                        'application/vnd.ant.fit',
                        'application/gpx+xml',
                        'application/tcx+xml',
                        'text/xml',
                        'application/xml'
                    ]
                    
                    is_valid_file = any(ct in content_type for ct in valid_content_types)
                    
                    if is_valid_file or len(response.content) > 1000:  # 假设有效文件至少1KB
                        # 保存文件
                        return self._save_downloaded_file(response, activity_name or f"activity_{activity_id}", content_type)
                    else:
                        self.debug_print(f"未知的文件格式，Content-Type: {content_type}")
                        return False, None
                        
                elif response.status_code == 404:
                    self.debug_print("活动不存在或没有原始文件")
                    print(f"活动 {activity_id} 不存在或没有原始文件")
                    return False, None
                    
                elif response.status_code == 202:
                    self.debug_print(f"文件正在准备中（状态码202），第{attempt + 1}次尝试")
                    if attempt < max_retries - 1:
                        # 计算下次等待时间
                        next_wait_time = 2 ** (attempt + 1) if attempt < 3 else 10
                        remaining_attempts = max_retries - attempt - 1
                        print(f"活动 {activity_id} 的文件正在准备中，将在{next_wait_time}秒后重试（剩余{remaining_attempts}次尝试）...")
                        continue  # 继续下一次循环，进行重试
                    else:
                        self.debug_print("已达到最大重试次数，文件仍在准备中")
                        print(f"活动 {activity_id} 的文件准备时间过长（已尝试{max_retries}次），请稍后手动重试")
                        return True, None
                    
                elif response.status_code in [401, 403]:
                    self.debug_print("认证失败，Cookie可能已过期")
                    print("Cookie已过期，请重新输入")
                    return True, None
                    
                else:
                    self.debug_print(f"下载失败，状态码: {response.status_code}")
                    return True, None
                    
            except Exception as e:
                self.debug_print(f"下载请求异常: {e}")
                if attempt < max_retries - 1:
                    continue
                return True, None
        
        # 如果所有重试都失败了
        self.debug_print("所有重试尝试都失败")
        return True, None
    
    def _save_downloaded_file(self, response: requests.Response, base_filename: str, content_type: str) -> Tuple[bool, Optional[str]]:
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
                return True, download_path
                
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
                return True, download_path
            else:
                self.debug_print(f"未知的文件格式，Content-Type: {content_type}")
                if hasattr(response, 'text'):
                    preview = response.text[:200] if response.text else str(response.content[:200]) 
                    self.debug_print(f"响应内容开头: {preview}")
                return False, None
                
        except Exception as e:
            self.debug_print(f"文件保存失败: {e}")
            return False, None
    
    def get_activities_for_migration(self, batch_size: int = 10, 
                                    after: Optional[datetime] = None,
                                    before: Optional[datetime] = None) -> List[Dict]:
        """获取用于历史迁移的活动列表
        
        Args:
            batch_size: 每批处理的活动数量
            after: 开始时间（从这个时间之后开始获取）
            before: 结束时间（获取到这个时间为止）
        
        Returns:
            按时间顺序排列的活动列表（最老的在前）
        """
        print(f"获取历史迁移活动，批次大小: {batch_size}")
        if after:
            print(f"开始时间: {after}")
        if before:
            print(f"结束时间: {before}")
        
        # 直接使用优化后的get_activities_in_batches方法
        activities = self.get_activities_in_batches(
            total_limit=batch_size,
            after=after,
            before=before
        )
        
        if not activities:
            print("未找到符合条件的活动")
            return []
        
        # 按时间排序（最老的在前）
        activities.sort(key=lambda x: x['start_date'])
        
        print(f"最终返回{len(activities)}个活动用于迁移")
        
        if activities:
            first_activity_time = activities[0]['start_date']
            last_activity_time = activities[-1]['start_date']
            print(f"活动时间范围: {first_activity_time} 到 {last_activity_time}")
        
        return activities 