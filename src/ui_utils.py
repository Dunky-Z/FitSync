import os
import questionary
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class UIUtils:
    """用户界面交互工具类"""
    
    @staticmethod
    def ask_file_location() -> str:
        """询问文件位置选择"""
        return questionary.select(
            "选择文件来源:",
            choices=["从Strava下载", "提供文件路径"]
        ).ask()
    
    @staticmethod
    def ask_activity_source() -> str:
        """询问活动来源"""
        return questionary.select(
            "选择活动来源:",
            choices=[
                "从Strava API获取最新活动",
                "手动输入活动ID"
            ]
        ).ask()
    
    @staticmethod
    def ask_activity_id() -> str:
        """询问活动ID"""
        activity_id = questionary.text(
            "请输入Strava活动ID:"
        ).ask()
        
        if activity_id is None:
            raise SystemExit("操作被用户取消")
        
        # 提取数字
        import re
        return re.sub(r"\D", "", activity_id)
    
    @staticmethod
    def ask_file_path(prompt: str = "请输入文件路径:") -> str:
        """询问文件路径"""
        return questionary.path(
            prompt,
            validate=UIUtils._validate_file_path,
            only_directories=False
        ).ask()
    
    @staticmethod
    def _validate_file_path(path: str) -> bool:
        """验证文件路径"""
        return os.path.isfile(path)
    
    @staticmethod
    def ask_upload_platforms() -> List[str]:
        """询问用户要上传到哪些平台"""
        print("\n选择上传平台:")
        print("使用方向键移动，空格键选中/取消选中，回车键确认")
        
        platforms = questionary.checkbox(
            "选择要上传到的平台 (可多选):",
            choices=[
                {"name": "IGPSport", "value": "igpsport", "checked": False},
                {"name": "Garmin Connect", "value": "garmin", "checked": False}
            ],
            instruction="(使用空格键选择，回车键确认)"
        ).ask()
        
        if not platforms:
            print("未选择任何平台，将只验证文件")
            confirm_no_upload = questionary.confirm(
                "是否确定不上传到任何平台?",
                default=False
            ).ask()
            
            if not confirm_no_upload:
                print("重新选择平台...")
                return UIUtils.ask_upload_platforms()  # 递归重新选择
        else:
            platform_names = []
            if "igpsport" in platforms:
                platform_names.append("IGPSport")
            if "garmin" in platforms:
                platform_names.append("Garmin Connect")
            print(f"已选择上传到: {', '.join(platform_names)}")
        
        return platforms or []
    
    @staticmethod
    def format_activity_choice(activity: Dict) -> str:
        """格式化活动选择项"""
        activity_id = activity.get("id", "Unknown")
        name = activity.get("name", "未命名活动")
        sport_type = activity.get("sport_type", "Unknown")
        start_date = activity.get("start_date_local", "")
        
        # 格式化日期
        if start_date:
            try:
                date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = start_date[:10]
        else:
            formatted_date = "未知日期"
        
        # 距离信息
        distance = activity.get("distance", 0)
        if distance > 0:
            distance_km = distance / 1000
            distance_str = f"{distance_km:.1f}km"
        else:
            distance_str = "无距离信息"
        
        return f"[{activity_id}] {name} ({sport_type}) - {formatted_date} - {distance_str}"
    
    @staticmethod
    def select_activity_from_list(activities: List[Dict]) -> Tuple[str, Optional[str]]:
        """从活动列表中选择活动"""
        # 格式化选择项
        choices = []
        for activity in activities:
            choices.append(UIUtils.format_activity_choice(activity))
        
        # 添加手动输入选项
        choices.append("手动输入活动ID")
        
        # 让用户选择
        selected = questionary.select(
            f"选择要下载的活动 (显示最新{len(activities)}个):",
            choices=choices
        ).ask()
        
        if selected == "手动输入活动ID":
            return UIUtils.ask_activity_id(), None
        else:
            # 提取活动ID
            import re
            activity_id = re.search(r'\[(\d+)\]', selected).group(1)
            
            # 查找对应的活动信息
            selected_activity = None
            for activity in activities:
                if str(activity.get("id")) == activity_id:
                    selected_activity = activity
                    break
            
            activity_name = selected_activity.get("name", "未命名活动") if selected_activity else None
            return activity_id, activity_name
    
    @staticmethod
    def confirm_use_existing_file(filename: str) -> bool:
        """确认是否使用已存在的文件"""
        return questionary.confirm(
            f"是否使用已存在的文件: {filename}?",
            default=True
        ).ask()
    
    @staticmethod
    def confirm_use_latest_file(filename: str) -> bool:
        """确认是否使用最新文件"""
        return questionary.confirm(
            f"是否使用此文件: {filename}?",
            default=True
        ).ask()
    
    @staticmethod
    def ask_credentials(platform_name: str) -> Tuple[str, str]:
        """询问平台登录凭据"""
        print(f"\n请输入{platform_name}登录信息:")
        username = questionary.text(f"{platform_name}用户名/邮箱:").ask()
        password = questionary.password(f"{platform_name}密码:").ask()
        
        if not username or not password:
            raise ValueError("用户名和密码不能为空")
        
        return username, password
    
    @staticmethod
    def ask_save_credentials() -> bool:
        """询问是否保存凭据"""
        return questionary.confirm(
            "是否保存登录凭据供下次使用?",
            default=True
        ).ask()
    
    @staticmethod
    def ask_use_saved_credentials(username: str) -> bool:
        """询问是否使用已保存的凭据"""
        return questionary.confirm(
            f"是否使用已保存的账户: {username}?",
            default=True
        ).ask()
    
    @staticmethod
    def ask_garmin_server() -> str:
        """询问Garmin服务器选择"""
        return questionary.select(
            "选择Garmin Connect服务器:",
            choices=[
                {"name": "全球版 (garmin.com)", "value": "GLOBAL"},
                {"name": "中国版 (garmin.cn)", "value": "CN"}
            ]
        ).ask()
    
    @staticmethod
    def ask_manual_token(platform_name: str) -> Optional[str]:
        """询问是否手动输入Token"""
        manual_token = questionary.confirm(
            f"自动登录失败，是否要手动输入{platform_name}的Token?",
            default=False
        ).ask()

        if manual_token:
            return questionary.text(f"请输入{platform_name} Token值:").ask()
        
        return None 