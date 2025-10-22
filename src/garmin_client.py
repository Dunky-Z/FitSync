import logging
import os
from enum import Enum, auto
import requests
import uuid

try:
    import garth
    GARTH_AVAILABLE = True
except ImportError:
    GARTH_AVAILABLE = False

from garmin_url_dict import GARMIN_URL_DICT

logger = logging.getLogger(__name__)


class GarminClient:
    def __init__(self, email, password, auth_domain="GLOBAL", config_manager=None, debug=False):
        if not GARTH_AVAILABLE:
            raise ImportError("需要安装garth库：pip install garth")
            
        self.auth_domain = auth_domain
        self.email = email
        self.password = password
        self.garthClient = garth
        self.config_manager = config_manager
        self.debug = debug
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "origin": GARMIN_URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT"
        }
        self._logged_in = False
        
        print(f"🔧 初始化GarminClient:")
        print(f"   - 邮箱: {email}")
        print(f"   - 认证域: {auth_domain}")
        print(f"   - 配置管理器: {'已设置' if config_manager else '未设置'}")
        print(f"   - SSO来源: {GARMIN_URL_DICT.get('SSO_URL_ORIGIN')}")
        
        # 尝试恢复已保存的会话
        self._try_resume_session()
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[GarminClient] {message}")

    def _get_session_data(self):
        """从配置文件获取会话数据"""
        if not self.config_manager:
            return None
        
        try:
            garmin_config = self.config_manager.get_platform_config("garmin")
            session_data = garmin_config.get("session_data", {})
            
            # 检查会话数据是否匹配当前用户和域名
            saved_email = session_data.get("email", "")
            saved_domain = session_data.get("auth_domain", "")
            
            if saved_email == self.email and saved_domain == self.auth_domain:
                return session_data.get("garth_session", None)
            else:
                print(f"会话数据不匹配当前用户 ({self.email}) 或域名 ({self.auth_domain})")
                return None
                
        except Exception as e:
            print(f"获取会话数据失败: {e}")
            return None

    def _save_session_data(self, session_data):
        """保存会话数据到配置文件"""
        if not self.config_manager:
            print("配置管理器未设置，无法保存会话")
            return False
        
        try:
            garmin_config = self.config_manager.get_platform_config("garmin")
            
            # 保存会话数据，包含用户和域名信息
            garmin_config["session_data"] = {
                "email": self.email,
                "auth_domain": self.auth_domain,
                "garth_session": session_data
            }
            
            self.config_manager.save_platform_config("garmin", garmin_config)
            print("Garmin会话已保存到配置文件")
            return True
            
        except Exception as e:
            print(f"保存会话数据失败: {e}")
            return False

    def _clear_session_data(self):
        """清除配置文件中的会话数据"""
        if not self.config_manager:
            return
        
        try:
            garmin_config = self.config_manager.get_platform_config("garmin")
            if "session_data" in garmin_config:
                del garmin_config["session_data"]
                self.config_manager.save_platform_config("garmin", garmin_config)
                print("已清除配置文件中的会话数据")
        except Exception as e:
            print(f"清除会话数据失败: {e}")

    def _try_resume_session(self):
        """尝试恢复已保存的会话"""
        session_data = self._get_session_data()
        if not session_data:
            print("未找到已保存的会话数据")
            return False
        
        try:
            print("尝试恢复已保存的Garmin会话...")
            
            # 配置garth域名
            if self.auth_domain and str(self.auth_domain).upper() == "CN":
                target_domain = "garmin.cn"
            else:
                target_domain = "garmin.com"
            
            self.garthClient.configure(domain=target_domain)
            
            # 创建临时会话目录
            import tempfile
            import json
            import os
            
            # 创建临时目录（garth需要目录路径）
            temp_dir = tempfile.mkdtemp(prefix="garmin_resume_")
            
            try:
                # 恢复所有会话文件
                for filename, file_data in session_data.items():
                    if filename.endswith('.json'):
                        session_file_path = os.path.join(temp_dir, filename)
                        with open(session_file_path, 'w') as temp_file:
                            json.dump(file_data, temp_file)
                
                # 尝试恢复会话
                self.garthClient.resume(temp_dir)
                
                # 验证会话是否有效
                username = self.garthClient.client.username
                print(f"会话恢复成功！用户名: {username}")
                self._logged_in = True
                return True
                
            finally:
                # 清理临时目录
                try:
                    import shutil
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception as cleanup_e:
                    print(f"清理临时目录失败: {cleanup_e}")
            
        except Exception as e:
            print(f"会话恢复失败: {e}")
            print("将使用用户名密码重新登录")
            # 清除无效的会话数据
            self._clear_session_data()
            return False

    def _save_session(self):
        """保存当前会话"""
        try:
            # 创建临时会话文件
            import tempfile
            import json
            import os
            
            # 创建临时目录（garth需要目录路径）
            temp_dir = tempfile.mkdtemp(prefix="garmin_session_")
            
            try:
                # 保存到临时目录
                self.garthClient.save(temp_dir)
                
                # 读取所有会话文件
                session_data = {}
                for file in os.listdir(temp_dir):
                    if file.endswith('.json'):
                        file_path = os.path.join(temp_dir, file)
                        with open(file_path, 'r') as f:
                            session_data[file] = json.load(f)
                
                if not session_data:
                    raise Exception("未找到会话文件")
                
                # 保存到配置文件
                success = self._save_session_data(session_data)
                if success:
                    print("会话保存成功")
                return success
                
            finally:
                # 清理临时目录
                try:
                    import shutil
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception as cleanup_e:
                    print(f"清理临时目录失败: {cleanup_e}")
                    
        except Exception as e:
            print(f"保存会话失败: {e}")
            return False

    def login(func):    
        def wrapper(self, *args, **kwargs):    
            try:
                print(f"\n检查Garmin登录状态...")
                
                if not self._logged_in:
                    print("客户端未标记为已登录，需要重新登录")
                    raise Exception("需要登录")
                    
                # 检查garth客户端状态
                try:
                    username = garth.client.username
                    print(f"Garth客户端状态正常，用户名: {username}")
                except Exception as e:
                    print(f"Garth客户端状态异常: {e}")
                    raise e
                    
            except Exception as e:
                print(f"\n开始Garmin登录流程...")
                print(f"   - 登录原因: {e}")
                
                try:
                    # 配置garth域名
                    if self.auth_domain and str(self.auth_domain).upper() == "CN":
                        target_domain = "garmin.cn"
                        print(f"配置为中国版域名: {target_domain}")
                    else:
                        target_domain = "garmin.com"
                        print(f"配置为全球版域名: {target_domain}")
                    
                    print(f"正在配置garth客户端域名...")
                    self.garthClient.configure(domain=target_domain)
                    print(f"Garth域名配置完成")
                    
                    print(f"正在使用用户名密码登录...")
                    print(f"   - 用户名: {self.email}")
                    print(f"   - 密码: {'*' * len(self.password)}")
                    
                    # 执行登录
                    self.garthClient.login(self.email, self.password)
                    
                    self._logged_in = True
                    print("Garmin登录成功！")
                    
                    # 保存会话
                    self._save_session()
                    
                    # 验证登录后的状态
                    try:
                        logged_user = garth.client.username
                        domain = garth.client.domain
                        print(f"登录后状态验证:")
                        print(f"   - 用户名: {logged_user}")
                        print(f"   - 域名: {domain}")
                        
                        # 检查OAuth token
                        if hasattr(garth.client, 'oauth2_token'):
                            token_preview = str(garth.client.oauth2_token)[:50] + "..." if len(str(garth.client.oauth2_token)) > 50 else str(garth.client.oauth2_token)
                            print(f"   - OAuth Token预览: {token_preview}")
                        else:
                            print("   - 未找到OAuth Token")
                            
                    except Exception as verify_e:
                        print(f"登录后状态验证失败: {verify_e}")
                        
                except Exception as login_e:
                    print(f"Garmin登录失败: {login_e}")
                    print(f"   - 错误类型: {type(login_e).__name__}")
                    print(f"   - 错误详情: {str(login_e)}")
                    
                    # 检查是否是特定的错误类型
                    if "Update Phone Number" in str(login_e):
                        print("检测到手机号更新要求")
                        print("建议解决方案:")
                        print("   1. 在浏览器中访问 https://connect.garmin.com 并登录")
                        print("   2. 完成任何必要的验证步骤")
                        print("   3. 确保能正常访问主页")
                        print("   4. 重新运行此程序")
                    elif "Unexpected title" in str(login_e):
                        print("检测到意外页面标题")
                        print("可能的原因:")
                        print("   - Garmin检测到自动化登录并要求额外验证")
                        print("   - 需要在浏览器中完成人工验证")
                    elif "Too Many Requests" in str(login_e) or "429" in str(login_e):
                        print("检测到登录频率限制")
                        print("建议解决方案:")
                        print("   - 等待1小时后重试")
                        print("   - 或者使用已保存的会话文件")
                        
                    self._logged_in = False
                    raise login_e
                    
            return func(self, *args, **kwargs)
        return wrapper

    def clear_session(self):
        """清除保存的会话"""
        try:
            self._clear_session_data()
            self._logged_in = False
            print("会话已清除，下次将重新登录")
        except Exception as e:
            print(f"清除会话失败: {e}")

    @login 
    def download(self, path, **kwargs):
        print(f"执行下载请求: {path}")
        return self.garthClient.download(path, **kwargs)

    @login 
    def connectapi(self, path, **kwargs):
        print(f"执行API请求: {path}")
        return self.garthClient.connectapi(path, **kwargs)

    def getActivities(self, start: int, limit: int):
        """获取活动列表"""
        params = {"start": str(start), "limit": str(limit)}
        print(f"获取活动列表: start={start}, limit={limit}")
        activities = self.connectapi(path=GARMIN_URL_DICT["garmin_connect_activities"], params=params)
        return activities

    def getAllActivities(self):
        """获取所有活动"""
        all_activities = []
        start = 0
        while True:
            activities = self.getActivities(start=start, limit=100)
            if len(activities) > 0:
                all_activities.extend(activities)
            else:
                return all_activities
            start += 100

    def downloadFitActivity(self, activity):
        """下载原始格式的活动"""
        download_fit_activity_url_prefix = GARMIN_URL_DICT["garmin_connect_fit_download"]
        download_fit_activity_url = f"{download_fit_activity_url_prefix}/{activity}"
        response = self.download(download_fit_activity_url)
        return response

    @login  
    def upload_activity(self, activity_path: str):
        """上传活动文件"""
        if not self.debug:
            print("正在上传到Garmin Connect...")
        
        self.debug_print(f"开始上传活动文件到Garmin Connect...")
        self.debug_print(f"文件路径: {activity_path}")
        
        # 检查文件
        if not os.path.exists(activity_path):
            error_msg = f"文件不存在: {activity_path}"
            print(error_msg)
            return "UPLOAD_EXCEPTION"
            
        file_size = os.path.getsize(activity_path)
        file_base_name = os.path.basename(activity_path)
        file_extension = file_base_name.split(".")[-1]
        
        self.debug_print(f"文件大小: {file_size} bytes")
        self.debug_print(f"文件名: {file_base_name}")
        self.debug_print(f"文件扩展名: {file_extension}")
        
        allowed_file_extension = (
            file_extension.upper() in ActivityUploadFormat.__members__
        )
        
        if not allowed_file_extension:
            error_msg = f"不支持的文件格式: {file_extension}"
            print(error_msg)
            print(f"支持的格式: {', '.join(ActivityUploadFormat.__members__.keys())}")
            return "UPLOAD_EXCEPTION"

        self.debug_print(f"文件格式检查通过: {file_extension.upper()}")

        try:
                self.debug_print("正在读取文件内容...")
                with open(activity_path, 'rb') as file:
                    file_data = file.read()
                    self.debug_print(f"文件读取成功，大小: {len(file_data)} bytes")
                    
                    # 为文件生成更合适的文件名（时间戳+原扩展名）
                    import time
                    timestamp = str(int(time.time() * 1000))
                    safe_filename = f"activity_{timestamp}.{file_extension.lower()}"
                    
                    # 根据文件类型设置正确的 MIME type
                    if file_extension.upper() == "FIT":
                        content_type = 'application/vnd.ant.fit'
                    elif file_extension.upper() == "GPX":
                        content_type = 'application/gpx+xml'
                    elif file_extension.upper() == "TCX":
                        content_type = 'application/vnd.garmin.tcx+xml'
                    else:
                        content_type = 'application/octet-stream'
                    
                    fields = {
                        'file': (safe_filename, file_data, content_type)
                    }
                    self.debug_print(f"文件数据准备完成 - 文件名: {safe_filename}, Content-Type: {content_type}")

                # 构建上传URL
                url_path = GARMIN_URL_DICT["garmin_connect_upload"]
                upload_url = f"https://connectapi.{self.garthClient.client.domain}{url_path}"
                self.debug_print(f"上传URL: {upload_url}")
                
                # 准备headers - 移除可能导致问题的headers
                upload_headers = {
                    'Authorization': str(self.garthClient.client.oauth2_token),
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                # 不要设置 Content-Type，让 requests 自动处理 multipart/form-data
                
                auth_preview = str(self.garthClient.client.oauth2_token)[:30] + "..." if len(str(self.garthClient.client.oauth2_token)) > 30 else str(self.garthClient.client.oauth2_token)
                self.debug_print(f"Authorization预览: {auth_preview}")
                
                if self.debug:
                    self.debug_print("请求Headers:")
                    for key, value in upload_headers.items():
                        if key == 'Authorization':
                            self.debug_print(f"   - {key}: {value[:30]}..." if len(value) > 30 else f"   - {key}: {value}")
                        else:
                            self.debug_print(f"   - {key}: {value}")
                
                self.debug_print("发送上传请求...")
                response = requests.post(upload_url, headers=upload_headers, files=fields, timeout=60)
                res_code = response.status_code
                
                # 详细响应信息只在debug模式下显示
                if self.debug:
                    self.debug_print("服务器响应:")
                    self.debug_print(f"   - 状态码: {res_code}")
                    self.debug_print(f"   - 响应头: {dict(response.headers)}")
                    self.debug_print(f"   - 响应大小: {len(response.text)} characters")
                    self.debug_print(f"   - 响应内容: {response.text}")
                
                if res_code == 200:
                    self.debug_print("HTTP 200 - 处理成功响应")
                    try:
                        result = response.json()
                        self.debug_print(f"JSON解析成功: {result}")
                        
                        upload_id = result.get("detailedImportResult", {}).get('uploadId')
                        self.debug_print(f"Upload ID: {upload_id}")
                        
                        is_duplicate_upload = upload_id is None or upload_id == ''
                        self.debug_print(f"是否重复上传: {is_duplicate_upload}")
                        
                        if not is_duplicate_upload:
                            if not self.debug:
                                print("上传成功")
                            self.debug_print("上传成功！")
                            return "SUCCESS"
                        else:
                            if not self.debug:
                                print("活动已存在（重复活动）")
                            self.debug_print("检测到重复活动")
                            return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        self.debug_print(f"JSON解析失败: {e}")
                        self.debug_print(f"原始响应: {response.text}")
                        print("上传失败：响应解析错误")
                        return "UPLOAD_EXCEPTION"
                        
                elif res_code == 202:
                    self.debug_print("HTTP 202 - 请求已接受，处理中")
                    try:
                        result = response.json()
                        self.debug_print(f"JSON解析成功: {result}")
                        
                        upload_id = result.get("detailedImportResult", {}).get('uploadId')
                        self.debug_print(f"Upload ID: {upload_id}")
                        
                        is_duplicate_upload = upload_id is None or upload_id == ''
                        self.debug_print(f"是否重复上传: {is_duplicate_upload}")
                        
                        if not is_duplicate_upload:
                            if not self.debug:
                                print("上传成功")
                            self.debug_print("上传成功！")
                            return "SUCCESS"
                        else:
                            if not self.debug:
                                print("活动已存在（重复活动）")
                            self.debug_print("检测到重复活动")
                            return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        self.debug_print(f"JSON解析失败: {e}")
                        self.debug_print(f"原始响应: {response.text}")
                        print("上传失败：响应解析错误")
                        return "UPLOAD_EXCEPTION"
                        
                elif res_code == 409:
                    self.debug_print("HTTP 409 - 冲突（通常是重复活动）")
                    try:
                        result = response.json()
                        self.debug_print(f"JSON解析成功: {result}")
                        
                        failures = result.get("detailedImportResult", {}).get("failures", [])
                        self.debug_print(f"失败信息: {failures}")
                        
                        if failures and len(failures) > 0:
                            messages = failures[0].get('messages', [])
                            if messages and len(messages) > 0:
                                message_content = messages[0].get('content', '')
                                self.debug_print(f"错误消息: {message_content}")
                                if "Duplicate Activity" in message_content:
                                    if not self.debug:
                                        print("活动已存在（重复活动）")
                                    self.debug_print("确认为重复活动")
                                    return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        self.debug_print(f"409响应解析失败: {e}")
                        self.debug_print(f"原始响应: {response.text}")
                    
                    if not self.debug:
                        print("活动已存在（重复活动）")
                    return "DUPLICATE_ACTIVITY"
                    
                else:
                    # 其他错误码的简洁提示
                    error_messages = {
                        400: "请求格式错误",
                        401: "认证失败，请重新登录",
                        403: "权限不足",
                        404: "服务不可用",
                        413: "文件过大",
                        429: "请求过于频繁，请稍后重试",
                        500: "Garmin服务器内部错误",
                        502: "Garmin服务器网关错误",
                        503: "Garmin服务不可用",
                        504: "Garmin服务器超时"
                    }
                    
                    error_msg = error_messages.get(res_code, f"上传失败，HTTP状态码: {res_code}")
                    print(f"上传失败：{error_msg}")
                    
                    self.debug_print(f"HTTP {res_code} - 上传失败")
                    self.debug_print(f"响应内容: {response.text}")
                    return "UPLOAD_EXCEPTION"
                    
        except Exception as e:
            error_msg = f"上传过程异常: {str(e)}"
            print(error_msg)
            
            self.debug_print(f"上传过程异常: {e}")
            self.debug_print(f"异常类型: {type(e).__name__}")
            self.debug_print(f"异常详情: {str(e)}")
            return "UPLOAD_EXCEPTION"


class ActivityUploadFormat(Enum):
    FIT = auto()
    GPX = auto()
    TCX = auto()


class GarminNoLoginException(Exception):
    """Raised when login fails."""
    def __init__(self, status):
        super(GarminNoLoginException, self).__init__(status)
        self.status = status 