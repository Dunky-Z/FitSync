import logging
import os
from enum import Enum, auto
import requests

try:
    import garth
    GARTH_AVAILABLE = True
except ImportError:
    GARTH_AVAILABLE = False

from garmin_url_dict import GARMIN_URL_DICT

logger = logging.getLogger(__name__)


class GarminClient:
    def __init__(self, email, password, auth_domain="GLOBAL"):
        if not GARTH_AVAILABLE:
            raise ImportError("需要安装garth库：pip install garth")
            
        self.auth_domain = auth_domain
        self.email = email
        self.password = password
        self.garthClient = garth
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "origin": GARMIN_URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT"
        }
        self._logged_in = False
        
        print(f"🔧 初始化GarminClient:")
        print(f"   - 邮箱: {email}")
        print(f"   - 认证域: {auth_domain}")
        print(f"   - SSO来源: {GARMIN_URL_DICT.get('SSO_URL_ORIGIN')}")

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
                        
                    self._logged_in = False
                    raise login_e
                    
            return func(self, *args, **kwargs)
        return wrapper

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
        print(f"\n开始上传活动文件到Garmin Connect...")
        print(f"   - 文件路径: {activity_path}")
        
        # 检查文件
        if not os.path.exists(activity_path):
            print(f"文件不存在: {activity_path}")
            return "UPLOAD_EXCEPTION"
            
        file_size = os.path.getsize(activity_path)
        print(f"   - 文件大小: {file_size} bytes")
        
        file_base_name = os.path.basename(activity_path)
        file_extension = file_base_name.split(".")[-1]
        print(f"   - 文件名: {file_base_name}")
        print(f"   - 文件扩展名: {file_extension}")
        
        allowed_file_extension = (
            file_extension.upper() in ActivityUploadFormat.__members__
        )
        
        if not allowed_file_extension:
            print(f"不支持的文件格式: {file_extension}")
            print(f"   支持的格式: {', '.join(ActivityUploadFormat.__members__.keys())}")
            return "UPLOAD_EXCEPTION"

        print(f"文件格式检查通过: {file_extension.upper()}")

        try:
            print(f"正在读取文件内容...")
            with open(activity_path, 'rb') as file:
                file_data = file.read()
                print(f"文件读取成功，大小: {len(file_data)} bytes")
                
                fields = {
                    'file': (file_base_name, file_data, 'application/octet-stream')
                }
                print(f"文件数据准备完成")

                # 构建上传URL
                url_path = GARMIN_URL_DICT["garmin_connect_upload"]
                upload_url = f"https://connectapi.{self.garthClient.client.domain}{url_path}"
                print(f"上传URL: {upload_url}")
                
                # 准备headers
                self.headers['Authorization'] = str(self.garthClient.client.oauth2_token)
                auth_preview = str(self.garthClient.client.oauth2_token)[:30] + "..." if len(str(self.garthClient.client.oauth2_token)) > 30 else str(self.garthClient.client.oauth2_token)
                print(f"Authorization预览: {auth_preview}")
                
                print(f"请求Headers:")
                for key, value in self.headers.items():
                    if key == 'Authorization':
                        print(f"   - {key}: {value[:30]}..." if len(value) > 30 else f"   - {key}: {value}")
                    else:
                        print(f"   - {key}: {value}")
                
                print(f"发送上传请求...")
                response = requests.post(upload_url, headers=self.headers, files=fields, timeout=60)
                res_code = response.status_code
                
                print(f"服务器响应:")
                print(f"   - 状态码: {res_code}")
                print(f"   - 响应头: {dict(response.headers)}")
                print(f"   - 响应大小: {len(response.text)} characters")
                print(f"   - 响应内容: {response.text}")
                
                if res_code == 200:
                    print("HTTP 200 - 处理成功响应")
                    try:
                        result = response.json()
                        print(f"JSON解析成功: {result}")
                        
                        upload_id = result.get("detailedImportResult", {}).get('uploadId')
                        print(f"Upload ID: {upload_id}")
                        
                        is_duplicate_upload = upload_id is None or upload_id == ''
                        print(f"是否重复上传: {is_duplicate_upload}")
                        
                        if not is_duplicate_upload:
                            print("上传成功！")
                            return "SUCCESS"
                        else:
                            print("检测到重复活动")
                            return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        print(f"JSON解析失败: {e}")
                        print(f"   原始响应: {response.text}")
                        return "UPLOAD_EXCEPTION"
                        
                elif res_code == 202:
                    print("HTTP 202 - 请求已接受，处理中")
                    try:
                        result = response.json()
                        print(f"JSON解析成功: {result}")
                        
                        upload_id = result.get("detailedImportResult", {}).get('uploadId')
                        print(f"Upload ID: {upload_id}")
                        
                        is_duplicate_upload = upload_id is None or upload_id == ''
                        print(f"是否重复上传: {is_duplicate_upload}")
                        
                        if not is_duplicate_upload:
                            print("上传成功！")
                            return "SUCCESS"
                        else:
                            print("检测到重复活动")
                            return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        print(f"JSON解析失败: {e}")
                        print(f"   原始响应: {response.text}")
                        return "UPLOAD_EXCEPTION"
                        
                elif res_code == 409:
                    print("HTTP 409 - 冲突（通常是重复活动）")
                    try:
                        result = response.json()
                        print(f"JSON解析成功: {result}")
                        
                        failures = result.get("detailedImportResult", {}).get("failures", [])
                        print(f"失败信息: {failures}")
                        
                        if failures and len(failures) > 0:
                            messages = failures[0].get('messages', [])
                            if messages and len(messages) > 0:
                                message_content = messages[0].get('content', '')
                                print(f"错误消息: {message_content}")
                                if "Duplicate Activity" in message_content:
                                    print("确认为重复活动")
                                    return "DUPLICATE_ACTIVITY"
                    except Exception as e:
                        print(f"409响应解析失败: {e}")
                        print(f"   原始响应: {response.text}")
                    return "DUPLICATE_ACTIVITY"
                    
                else:
                    print(f"HTTP {res_code} - 上传失败")
                    print(f"   响应内容: {response.text}")
                    return "UPLOAD_EXCEPTION"
                    
        except Exception as e:
            print(f"上传过程异常: {e}")
            print(f"   异常类型: {type(e).__name__}")
            print(f"   异常详情: {str(e)}")
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