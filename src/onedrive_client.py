# -*- coding: utf-8 -*-
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import webbrowser
import sys
import shutil

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

from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class OneDriveClient:
    """OneDrive客户端类"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        
        # OneDrive API 端点
        self.auth_url = "https://login.live.com/oauth20_authorize.srf"
        self.token_url = "https://login.live.com/oauth20_token.srf"
        self.api_base_url = "https://graph.microsoft.com/v1.0"
        
        # OAuth 范围
        self.scopes = [
            "Files.ReadWrite",
            "Files.ReadWrite.All", 
            "Files.ReadWrite.AppFolder",
            "Files.ReadWrite.Selected",
            "offline_access",
            "User.Read"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Strava-OneDrive-Sync/1.0'
        })
        
        # 支持的授权域
        self.auth_endpoints = {
            "common": "https://login.microsoftonline.com/common/oauth2/v2.0",
            "consumers": "https://login.microsoftonline.com/consumers/oauth2/v2.0",
            "organizations": "https://login.microsoftonline.com/organizations/oauth2/v2.0"
        }
        
        # 延迟导入file_converter和database_manager，避免循环导入
        self.file_converter = None
        self.db_manager = None
    
    def _get_file_converter(self):
        """延迟导入文件转换器"""
        if self.file_converter is None:
            from file_converter import FileConverter
            self.file_converter = FileConverter()
        return self.file_converter
    
    def _get_database_manager(self):
        """延迟导入数据库管理器"""
        if self.db_manager is None:
            from database_manager import DatabaseManager
            self.db_manager = DatabaseManager(debug=self.debug)
        return self.db_manager
    
    def debug_print(self, message: str) -> None:
        """调试输出"""
        if self.debug:
            print(f"[OneDrive] {message}")
            logger.debug(f"OneDrive: {message}")
    
    def get_config(self) -> Dict:
        """获取OneDrive配置"""
        return self.config_manager.get_platform_config("onedrive")
    
    def save_config(self, config: Dict) -> None:
        """保存OneDrive配置"""
        self.config_manager.save_platform_config("onedrive", config)
    
    def get_authorization_url(self) -> str:
        """获取授权URL"""
        config = self.get_config()
        
        params = {
            'client_id': config['client_id'],
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'redirect_uri': config['redirect_uri']
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        self.debug_print(f"授权URL: {auth_url}")
        return auth_url
    
    def exchange_code_for_token(self, authorization_code: str) -> bool:
        """使用授权码交换访问令牌"""
        config = self.get_config()
        
        data = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'client_secret': config['client_secret'],
            'code': authorization_code,
            'grant_type': 'authorization_code'
        }
        
        try:
            self.debug_print("正在交换授权码...")
            response = self.session.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.debug_print(f"令牌交换成功: {list(token_data.keys())}")
            
            # 保存令牌信息
            config.update({
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'expires_in': token_data.get('expires_in', 3600),
                'token_type': token_data.get('token_type', 'bearer')
            })
            
            self.save_config(config)
            return True
            
        except Exception as e:
            self.debug_print(f"令牌交换失败: {e}")
            logger.error(f"OneDrive令牌交换失败: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        config = self.get_config()
        
        if not config.get('refresh_token'):
            self.debug_print("没有刷新令牌，无法刷新")
            return False
        
        data = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'client_secret': config['client_secret'],
            'refresh_token': config['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        try:
            self.debug_print("正在刷新访问令牌...")
            response = self.session.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.debug_print("令牌刷新成功")
            
            # 更新配置
            config.update({
                'access_token': token_data['access_token'],
                'expires_in': token_data.get('expires_in', 3600),
                'token_type': token_data.get('token_type', 'bearer')
            })
            
            # 如果返回了新的刷新令牌，也要更新
            if 'refresh_token' in token_data:
                config['refresh_token'] = token_data['refresh_token']
            
            self.save_config(config)
            return True
            
        except Exception as e:
            self.debug_print(f"令牌刷新失败: {e}")
            logger.error(f"OneDrive令牌刷新失败: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        config = self.get_config()
        access_token = config.get('access_token')
        
        if not access_token:
            raise ValueError("没有访问令牌")
        
        return {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            self.debug_print("测试OneDrive连接...")
            headers = self.get_headers()
            
            response = self.session.get(
                f"{self.api_base_url}/me/drive",
                headers=headers
            )
            
            if response.status_code == 401:
                self.debug_print("访问令牌已过期，尝试刷新...")
                if self.refresh_access_token():
                    headers = self.get_headers()
                    response = self.session.get(
                        f"{self.api_base_url}/me/drive",
                        headers=headers
                    )
                else:
                    return False
            
            response.raise_for_status()
            drive_info = response.json()
            self.debug_print(f"连接成功，驱动器: {drive_info.get('name', 'Unknown')}")
            return True
            
        except Exception as e:
            self.debug_print(f"连接测试失败: {e}")
            logger.error(f"OneDrive连接测试失败: {e}")
            return False
    
    def create_folder(self, folder_name: str, parent_path: str = "/") -> Optional[str]:
        """创建文件夹"""
        try:
            headers = self.get_headers()
            
            # 构建API路径
            if parent_path == "/":
                url = f"{self.api_base_url}/me/drive/root/children"
            else:
                url = f"{self.api_base_url}/me/drive/root:{parent_path}:/children"
            
            data = {
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"
            }
            
            self.debug_print(f"创建文件夹: {parent_path}/{folder_name}")
            response = self.session.post(url, headers=headers, json=data)
            
            if response.status_code == 409:
                self.debug_print("文件夹已存在")
                return None
            
            response.raise_for_status()
            folder_info = response.json()
            
            self.debug_print(f"文件夹创建成功: {folder_info['id']}")
            return folder_info['id']
            
        except Exception as e:
            self.debug_print(f"创建文件夹失败: {e}")
            logger.error(f"OneDrive创建文件夹失败: {e}")
            return None
    
    def upload_file(self, file_path: str, activity_name: str = None, fingerprint: str = None, 
                   convert_fit_to_gpx: bool = True, remote_path: str = "/Apps/Fog of World/Import") -> bool:
        """上传文件到OneDrive
        
        Args:
            file_path: 本地文件路径
            activity_name: 活动名称（用于生成友好的文件名）
            fingerprint: 活动指纹（用于从数据库查询活动名）
            convert_fit_to_gpx: 是否将FIT文件转换为GPX上传（只上传GPX）
            remote_path: 远程目录路径
        
        Returns:
            上传是否成功
        """
        if not os.path.exists(file_path):
            self.debug_print(f"文件不存在: {file_path}")
            return False
        
        try:
            self.debug_print(f"正在上传文件到OneDrive: {remote_path}")
            
            # 检查OneDrive连接
            if not self.test_connection():
                self.debug_print("OneDrive连接失败")
                return False
            
            # 确定活动名称
            final_activity_name = self._determine_activity_name(activity_name, fingerprint, file_path)
            
            # 获取并打印活动详细信息
            self._print_activity_details(fingerprint, final_activity_name)
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 要上传的文件路径和扩展名
            final_file_path = file_path
            final_file_ext = file_ext
            final_filename = final_activity_name
            
            # 默认不清理临时文件
            should_cleanup_gpx = False
            
            # 如果是FIT文件，优先检测实际内容是否为FIT二进制
            if file_ext == '.fit' and convert_fit_to_gpx:
                # 延迟导入 FileUtils 避免循环依赖
                from file_utils import FileUtils
                # 如果文件内容不是 FIT，则按 GPX 处理
                if not FileUtils.is_fit_binary(file_path):
                    self.debug_print("文件扩展名为 .fit，但内容为 XML/GPX，按GPX文件处理 …")
                    gpx_file_path = file_path.replace('.fit', '.gpx')
                    try:
                        shutil.copyfile(file_path, gpx_file_path)
                    except Exception as copy_e:
                        logger.warning(f"复制伪FIT文件失败: {copy_e}")
                        return False
                    final_file_path = gpx_file_path
                    final_file_ext = '.gpx'
                    should_cleanup_gpx = True
                else:
                    try:
                        self.debug_print("检测到FIT文件，转换为GPX格式上传...")
                        
                        # 生成GPX文件路径
                        gpx_file_path = file_path.replace('.fit', '.gpx')
                        
                        # 转换FIT到GPX
                        file_converter = self._get_file_converter()
                        converted_gpx = file_converter.convert_file(file_path, 'gpx', gpx_file_path)
                        
                        if converted_gpx and os.path.exists(converted_gpx):
                            self.debug_print(f"FIT文件已转换为GPX: {converted_gpx}")
                            
                            # 更新上传参数为GPX文件
                            final_file_path = converted_gpx
                            final_file_ext = '.gpx'
                            
                            # 清理临时GPX文件的标记（稍后清理）
                            should_cleanup_gpx = True
                        
                        else:
                            self.debug_print("FIT到GPX转换失败，跳过上传")
                            return False
                            
                    except Exception as convert_e:
                        logger.warning(f"FIT到GPX转换过程出错: {convert_e}")
                        self.debug_print("FIT转换出错，跳过上传")
                        return False
            else:
                # 非 FIT 文件或无需转换
                pass
            
            # 生成友好的文件名
            friendly_file_name = self._generate_friendly_filename(final_filename, final_file_ext, fingerprint)
            
            # 上传文件（只上传GPX文件）
            success = self._upload_single_file(final_file_path, remote_path, friendly_file_name)
            if success:
                self.debug_print(f"文件 {friendly_file_name} 已成功上传到OneDrive")
            else:
                self.debug_print(f"文件 {friendly_file_name} 上传失败")
                return False
            
            # 清理临时GPX文件
            if should_cleanup_gpx and os.path.exists(final_file_path):
                try:
                    os.remove(final_file_path)
                    self.debug_print(f"已清理临时GPX文件: {final_file_path}")
                except Exception as cleanup_e:
                    logger.warning(f"清理临时GPX文件失败: {cleanup_e}")
            
            return True
                
        except Exception as e:
            logger.error(f"OneDrive上传失败: {e}")
            self.debug_print(f"上传文件失败: {e}")
            return False
    
    def _print_activity_details(self, fingerprint: str, activity_name: str) -> None:
        """打印活动详细信息（日期、距离、时长）"""
        if not fingerprint:
            print(f"📅 上传活动: {activity_name} (无详细信息)")
            return
        
        try:
            db_manager = self._get_database_manager()
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
            # 查询活动详细信息
            cursor.execute('''
                SELECT name, start_time, distance, duration, elapsed_time 
                FROM activity_records 
                WHERE fingerprint = ?
            ''', (fingerprint,))
            result = cursor.fetchone()
            
            if result:
                name = result['name'] or activity_name
                start_time = result['start_time']
                distance = result['distance']
                duration = result['duration'] or result['elapsed_time']
                
                # 格式化日期
                if start_time:
                    from datetime import datetime
                    try:
                        # 尝试解析ISO格式时间
                        if 'T' in start_time:
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            date_str = dt.strftime('%Y-%m-%d')
                        else:
                            date_str = start_time[:10]  # 取前10个字符作为日期
                    except:
                        date_str = start_time[:10] if start_time else "未知日期"
                else:
                    date_str = "未知日期"
                
                # 格式化距离
                if distance:
                    distance_km = round(distance / 1000, 2) if distance > 1000 else round(distance, 2)
                    distance_str = f"{distance_km} km"
                else:
                    distance_str = "未知距离"
                
                # 格式化时长
                if duration:
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    if hours > 0:
                        duration_str = f"{hours}h {minutes}m {seconds}s"
                    elif minutes > 0:
                        duration_str = f"{minutes}m {seconds}s"
                    else:
                        duration_str = f"{seconds}s"
                else:
                    duration_str = "未知时长"
                
                print(f"📅 上传活动: {name}")
                print(f"   日期: {date_str}")
                print(f"   距离: {distance_str}")
                print(f"   时长: {duration_str}")
            else:
                print(f"📅 上传活动: {activity_name} (数据库中未找到详细信息)")
                
        except Exception as e:
            print(f"📅 上传活动: {activity_name} (详细信息获取失败: {e})")
    
    def _determine_activity_name(self, activity_name: str, fingerprint: str, file_path: str) -> str:
        """确定活动名称"""
        # 如果提供了活动名称，直接使用
        if activity_name:
            return activity_name
        
        # 如果提供了fingerprint，从数据库查询活动名
        if fingerprint:
            try:
                db_manager = self._get_database_manager()
                conn = db_manager._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT name FROM activity_records WHERE fingerprint = ?', (fingerprint,))
                result = cursor.fetchone()
                
                if result and result['name']:
                    self.debug_print(f"从数据库查询到活动名: {result['name']}")
                    return result['name']
                else:
                    self.debug_print(f"未在数据库中找到fingerprint {fingerprint}对应的活动名")
            except Exception as e:
                self.debug_print(f"从数据库查询活动名失败: {e}")
        
        # 如果都没有，使用文件名作为活动名
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        self.debug_print(f"使用文件名作为活动名: {base_name}")
        return base_name
    
    def _generate_friendly_filename(self, activity_name: str, file_ext: str, fingerprint: str = None) -> str:
        """生成友好的文件名"""
        # 清理活动名中的非法字符
        import re
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', activity_name)
        safe_name = safe_name.strip()
        
        # 限制长度
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        # 如果名称为空，使用默认名称
        if not safe_name:
            safe_name = "activity"
        
        # 生成唯一后缀：优先使用 fingerprint（取前8位），否则使用当前时间戳
        from datetime import datetime
        if fingerprint:
            uniq = fingerprint[:8]
        else:
            uniq = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        safe_name = f"{safe_name}_{uniq}"

        # 添加文件扩展名
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        
        return safe_name + file_ext
    
    def _upload_single_file(self, file_path: str, remote_path: str, custom_filename: str = None) -> bool:
        """上传单个文件到OneDrive"""
        try:
            file_name = custom_filename or os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            self.debug_print(f"开始上传文件: {file_name}")
            self.debug_print(f"文件大小: {file_size} bytes")
            self.debug_print(f"目标路径: {remote_path}")
            
            # 确保目标文件夹存在
            folder_parts = remote_path.strip('/').split('/')
            if folder_parts and folder_parts[0]:
                self.create_folder(folder_parts[0])
            
            headers = self.get_headers()
            
            # 小文件直接上传（< 4MB）
            if file_size < 4 * 1024 * 1024:
                return self._upload_small_file_internal(file_path, remote_path, file_name, headers)
            else:
                return self._upload_large_file_internal(file_path, remote_path, file_name, headers)
                
        except Exception as e:
            self.debug_print(f"上传文件失败: {e}")
            logger.error(f"OneDrive上传文件失败: {e}")
            return False
    
    def _upload_small_file_internal(self, file_path: str, remote_path: str, file_name: str, headers: Dict) -> bool:
        """上传小文件（< 4MB）"""
        # 构建上传URL
        if remote_path == "/":
            url = f"{self.api_base_url}/me/drive/root:/{file_name}:/content"
        else:
            url = f"{self.api_base_url}/me/drive/root:{remote_path}/{file_name}:/content"
        
        # 更新headers，移除Content-Type让requests自动设置
        upload_headers = headers.copy()
        upload_headers.pop('Content-Type', None)
        
        with open(file_path, 'rb') as file:
            self.debug_print("执行小文件上传...")
            response = self.session.put(url, headers=upload_headers, data=file)
            
            if response.status_code == 401:
                self.debug_print("访问令牌已过期，尝试刷新...")
                if self.refresh_access_token():
                    upload_headers = self.get_headers()
                    upload_headers.pop('Content-Type', None)
                    file.seek(0)
                    response = self.session.put(url, headers=upload_headers, data=file)
                else:
                    return False
            
            response.raise_for_status()
            file_info = response.json()
            
            self.debug_print(f"文件上传成功: {file_info['id']}")
            self.debug_print(f"OneDrive路径: {file_info['webUrl']}")
            return True
    
    def _upload_large_file_internal(self, file_path: str, remote_path: str, file_name: str, headers: Dict) -> bool:
        """上传大文件（>= 4MB）"""
        # 构建上传会话URL
        if remote_path == "/":
            url = f"{self.api_base_url}/me/drive/root:/{file_name}:/createUploadSession"
        else:
            url = f"{self.api_base_url}/me/drive/root:{remote_path}/{file_name}:/createUploadSession"
        
        # 创建上传会话
        session_data = {
            "item": {
                "@microsoft.graph.conflictBehavior": "replace",
                "name": file_name
            }
        }
        
        self.debug_print("创建大文件上传会话...")
        response = self.session.post(url, headers=headers, json=session_data)
        response.raise_for_status()
        
        upload_session = response.json()
        upload_url = upload_session['uploadUrl']
        
        # 分块上传
        chunk_size = 320 * 1024  # 320KB chunks
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as file:
            bytes_uploaded = 0
            
            while bytes_uploaded < file_size:
                chunk_start = bytes_uploaded
                chunk_end = min(bytes_uploaded + chunk_size - 1, file_size - 1)
                chunk_data = file.read(chunk_end - chunk_start + 1)
                
                chunk_headers = {
                    'Content-Range': f'bytes {chunk_start}-{chunk_end}/{file_size}',
                    'Content-Length': str(len(chunk_data))
                }
                
                self.debug_print(f"上传块: {chunk_start}-{chunk_end}/{file_size}")
                
                response = self.session.put(upload_url, headers=chunk_headers, data=chunk_data)
                
                if response.status_code == 202:
                    # 继续上传
                    bytes_uploaded = chunk_end + 1
                elif response.status_code in [200, 201]:
                    # 上传完成
                    file_info = response.json()
                    self.debug_print(f"大文件上传成功: {file_info['id']}")
                    return True
                else:
                    response.raise_for_status()
            
        return True
    
    # 保留原有的upload_file方法作为向后兼容
    def upload_file_legacy(self, file_path: str, remote_path: str = "/Sports-Activities") -> bool:
        """原有的upload_file方法，保持向后兼容"""
        return self._upload_single_file(file_path, remote_path)
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """从OneDrive下载文件"""
        try:
            headers = self.get_headers()
            
            # 获取下载URL
            url = f"{self.api_base_url}/me/drive/items/{file_id}/content"
            
            self.debug_print(f"开始下载文件: {file_id}")
            response = self.session.get(url, headers=headers, stream=True)
            
            if response.status_code == 401:
                self.debug_print("访问令牌已过期，尝试刷新...")
                if self.refresh_access_token():
                    headers = self.get_headers()
                    response = self.session.get(url, headers=headers, stream=True)
                else:
                    return False
            
            response.raise_for_status()
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 下载文件
            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            
            self.debug_print(f"文件下载成功: {local_path}")
            return True
            
        except Exception as e:
            self.debug_print(f"下载文件失败: {e}")
            logger.error(f"OneDrive下载文件失败: {e}")
            return False
    
    def list_files(self, folder_path: str = "/Sports-Activities") -> list:
        """列出文件夹中的文件"""
        try:
            headers = self.get_headers()
            
            # 构建API URL
            if folder_path == "/":
                url = f"{self.api_base_url}/me/drive/root/children"
            else:
                url = f"{self.api_base_url}/me/drive/root:{folder_path}:/children"
            
            self.debug_print(f"列出文件夹内容: {folder_path}")
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 401:
                self.debug_print("访问令牌已过期，尝试刷新...")
                if self.refresh_access_token():
                    headers = self.get_headers()
                    response = self.session.get(url, headers=headers)
                else:
                    return []
            
            response.raise_for_status()
            
            data = response.json()
            files = []
            
            for item in data.get('value', []):
                if 'file' in item:  # 只返回文件，不包含文件夹
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'size': item['size'],
                        'created': item['createdDateTime'],
                        'modified': item['lastModifiedDateTime'],
                        'download_url': item.get('@microsoft.graph.downloadUrl')
                    })
            
            self.debug_print(f"找到 {len(files)} 个文件")
            return files
            
        except Exception as e:
            self.debug_print(f"列出文件失败: {e}")
            logger.error(f"OneDrive列出文件失败: {e}")
            return []
    
    def setup_oauth(self) -> bool:
        """设置OAuth认证"""
        print("\n开始OneDrive OAuth设置...")
        
        config = self.get_config()
        
        # 检查必要的配置
        if (config.get('client_id') == 'your_client_id_here' or 
            config.get('client_secret') == 'your_client_secret_here'):
            print("请先在配置文件中设置OneDrive的client_id和client_secret")
            return False
        
        # 获取授权URL
        auth_url = self.get_authorization_url()
        
        print(f"\n请在浏览器中打开以下URL进行授权:")
        print(f"{auth_url}\n")
        
        try:
            # 尝试自动打开浏览器
            webbrowser.open(auth_url)
            print("已自动打开浏览器，请完成授权...")
        except:
            print("无法自动打开浏览器，请手动复制上述URL到浏览器中")
        
        # 等待用户输入授权码
        print("\n授权完成后，浏览器会跳转到localhost页面（可能显示错误，这是正常的）")
        print("请从地址栏复制完整的回调URL，或者只复制code参数的值\n")
        
        callback_url = input("请输入完整的回调URL或者code值: ").strip()
        
        # 解析授权码
        auth_code = None
        if callback_url.startswith('http'):
            # 完整URL
            parsed = urlparse(callback_url)
            query_params = parse_qs(parsed.query)
            auth_code = query_params.get('code', [None])[0]
        else:
            # 直接是code值
            auth_code = callback_url
        
        if not auth_code:
            print("未能获取到授权码")
            return False
        
        # 交换令牌
        if self.exchange_code_for_token(auth_code):
            print("OneDrive OAuth设置成功！")
            return True
        else:
            print("OAuth设置失败")
            return False 