import logging
from typing import Tuple, Optional
import questionary

from config_manager import ConfigManager
from ui_utils import UIUtils

logger = logging.getLogger(__name__)

class GarminClientWrapper:
    """Garmin客户端包装器"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        self.garmin_client = None
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(message)
    
    def _check_garth_availability(self) -> bool:
        """检查garth库是否可用"""
        try:
            from garmin_client import GarminClient, GARTH_AVAILABLE
            return GARTH_AVAILABLE
        except ImportError:
            return False
    
    def get_credentials(self) -> Tuple[str, str, str]:
        """获取Garmin Connect登录凭据"""
        config = self.config_manager.get_platform_config("garmin")
        
        # 检查是否已保存凭据
        saved_username = config.get("username", "")
        saved_password = config.get("password", "")
        saved_domain = config.get("auth_domain", "GLOBAL")
        
        if saved_username and saved_password:
            if UIUtils.ask_use_saved_credentials(saved_username):
                return saved_username, saved_password, saved_domain
        
        # 获取新的凭据
        username, password = UIUtils.ask_credentials("Garmin Connect")
        
        # 选择服务器区域
        domain = UIUtils.ask_garmin_server()
        
        # 询问是否保存凭据
        if UIUtils.ask_save_credentials():
            config["username"] = username
            config["password"] = password
            config["auth_domain"] = domain
            self.config_manager.save_platform_config("garmin", config)
            self.debug_print("Garmin Connect登录凭据已保存")
        
        return username, password, domain
    
    def _create_garmin_client(self, username: str, password: str, auth_domain: str):
        """创建Garmin客户端实例"""
        try:
            from garmin_client import GarminClient
            return GarminClient(username, password, auth_domain, self.config_manager)
        except ImportError as e:
            raise ImportError("无法导入garmin_client模块") from e
    
    def clear_session(self, username: str = None, auth_domain: str = None) -> None:
        """清除保存的Garmin会话"""
        try:
            if username and auth_domain:
                # 创建临时客户端实例来清除会话
                temp_client = self._create_garmin_client(username, "dummy", auth_domain)
                temp_client.clear_session()
            else:
                # 如果没有指定用户，尝试从配置中获取
                config = self.config_manager.get_platform_config("garmin")
                saved_username = config.get("username", "")
                saved_domain = config.get("auth_domain", "GLOBAL")
                
                if saved_username:
                    temp_client = self._create_garmin_client(saved_username, "dummy", saved_domain)
                    temp_client.clear_session()
                else:
                    print("未找到保存的用户信息，无法清除会话")
        except Exception as e:
            print(f"清除会话失败: {e}")
    
    def upload_file(self, file_path: str) -> None:
        """上传活动到Garmin Connect"""
        try:
            # 检查是否安装了garth库
            if not self._check_garth_availability():
                print("需要安装garth库才能上传到Garmin Connect")
                print("请运行: pip install garth")
                return
            
            print("正在准备上传到Garmin Connect...")
            
            # 获取登录凭据
            username, password, auth_domain = self.get_credentials()
            
            # 尝试上传，如果失败则提供重试选项
            max_retries = 3  # 增加重试次数
            for attempt in range(max_retries):
                try:
                    # 创建Garmin客户端
                    garmin_client = self._create_garmin_client(username, password, auth_domain)
                    
                    print("正在上传到Garmin Connect...")
                    
                    # 上传活动
                    result = garmin_client.upload_activity(file_path)
                    
                    if result == "SUCCESS":
                        print("活动已成功上传到Garmin Connect！")
                        return
                    elif result == "DUPLICATE_ACTIVITY":
                        print("活动已存在于Garmin Connect中（重复活动）")
                        return
                    else:
                        print(f"Garmin Connect上传失败: {result}")
                        return
                        
                except Exception as e:
                    error_str = str(e)
                    
                    if "Too Many Requests" in error_str or "429" in error_str:
                        print(f"\n检测到登录频率限制（尝试 {attempt + 1}/{max_retries}）")
                        print("这通常是因为短时间内多次登录导致的")
                        
                        if attempt < max_retries - 1:
                            retry_options = questionary.select(
                                "选择下一步操作:",
                                choices=[
                                    {"name": "清除会话并重新登录", "value": "clear_session"},
                                    {"name": "等待并重试", "value": "wait_retry"},
                                    {"name": "放弃上传", "value": "abort"}
                                ]
                            ).ask()
                            
                            if retry_options == "clear_session":
                                print("清除已保存的会话...")
                                garmin_client.clear_session()
                                print("会话已清除，将在下次重试时重新登录")
                                continue
                            elif retry_options == "wait_retry":
                                print("等待30秒后重试...")
                                import time
                                time.sleep(30)
                                continue
                            else:
                                print("用户选择放弃上传")
                                return
                        else:
                            print("\n建议解决方案:")
                            print("1. 等待1小时后重试")
                            print("2. 或者使用以下命令清除所有会话:")
                            print("   python -c \"from src.garmin_client_wrapper import GarminClientWrapper; from src.config_manager import ConfigManager; wrapper = GarminClientWrapper(ConfigManager()); wrapper.clear_session()\"")
                            raise e
                    
                    elif "Update Phone Number" in error_str or "Unexpected title" in error_str:
                        print(f"\n检测到Garmin Connect反自动化验证（尝试 {attempt + 1}/{max_retries}）")
                        
                        if attempt < max_retries - 1:  # 不是最后一次尝试
                            print("\n可能的解决方案:")
                            
                            retry_options = questionary.select(
                                "选择下一步操作:",
                                choices=[
                                    {"name": "清除会话并重新登录", "value": "clear_session"},
                                    {"name": "切换到中国版服务器 (garmin.cn)", "value": "switch_cn"},
                                    {"name": "切换到全球版服务器 (garmin.com)", "value": "switch_global"},
                                    {"name": "重新输入登录信息", "value": "re_login"},
                                    {"name": "放弃上传", "value": "abort"}
                                ]
                            ).ask()
                            
                            if retry_options == "clear_session":
                                print("清除已保存的会话...")
                                garmin_client.clear_session()
                                print("会话已清除，将在下次重试时重新登录")
                                continue
                            elif retry_options == "switch_cn":
                                auth_domain = "CN"
                                print("已切换到中国版服务器，重试中...")
                                continue
                            elif retry_options == "switch_global":
                                auth_domain = "GLOBAL"
                                print("已切换到全球版服务器，重试中...")
                                continue
                            elif retry_options == "re_login":
                                username, password, auth_domain = self.get_credentials()
                                print("使用新的登录信息重试中...")
                                continue
                            else:
                                print("用户选择放弃上传")
                                return
                        else:
                            # 最后一次尝试失败
                            print("\n最终建议解决方案:")
                            print("1. 在浏览器中访问相应的Garmin Connect网站:")
                            if auth_domain == "CN":
                                print("   https://connect.garmin.cn")
                            else:
                                print("   https://connect.garmin.com")
                            print("2. 使用相同的用户名密码登录")
                            print("3. 完成任何必要的验证步骤")
                            print("4. 确保能正常访问主页")
                            print("5. 保持浏览器窗口打开，重新运行此程序")
                            print("6. 或者清除会话文件重新开始")
                            
                            raise e
                    else:
                        raise e
                
        except ImportError as e:
            if "garth" in str(e):
                print("需要安装garth库才能上传到Garmin Connect")
                print("请运行以下命令安装依赖:")
                print("pip install garth")
            else:
                print(f"导入错误: {e}")
        except Exception as e:
            logger.error(f"Garmin Connect上传失败: {e}")
            print(f"Garmin Connect上传失败: {e}")
            
            # 如果是会话相关的错误，提供清除会话的建议
            if "session" in str(e).lower() or "login" in str(e).lower():
                print("\n提示: 如果持续遇到登录问题，可以尝试清除会话:")
                print("1. 删除 .garmin_sessions 文件夹")
                print("2. 重新运行程序") 