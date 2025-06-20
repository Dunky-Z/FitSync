# -*- coding: utf-8 -*-
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import webbrowser

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
    
    def upload_file(self, file_path: str, remote_path: str = "/Sports-Activities") -> bool:
        """上传文件到OneDrive"""
        if not os.path.exists(file_path):
            self.debug_print(f"文件不存在: {file_path}")
            return False
        
        try:
            file_name = os.path.basename(file_path)
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
                return self._upload_small_file(file_path, remote_path, headers)
            else:
                return self._upload_large_file(file_path, remote_path, headers)
                
        except Exception as e:
            self.debug_print(f"上传文件失败: {e}")
            logger.error(f"OneDrive上传文件失败: {e}")
            return False
    
    def _upload_small_file(self, file_path: str, remote_path: str, headers: Dict) -> bool:
        """上传小文件（< 4MB）"""
        file_name = os.path.basename(file_path)
        
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
    
    def _upload_large_file(self, file_path: str, remote_path: str, headers: Dict) -> bool:
        """上传大文件（>= 4MB）"""
        file_name = os.path.basename(file_path)
        
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