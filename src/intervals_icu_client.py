#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import requests
from typing import Dict, Optional, Tuple
from pathlib import Path

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
from ui_utils import UIUtils

logger = logging.getLogger(__name__)

class IntervalsIcuClient:
    """Intervals.icu客户端"""
    
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
        self.base_url = "https://intervals.icu/api/v1"
        self.supported_formats = ['.fit', '.tcx', '.gpx']
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[IntervalsICU] {message}")
    
    def get_credentials(self) -> Tuple[str, str]:
        """获取Intervals.icu凭据"""
        config = self.config_manager.get_platform_config("intervals_icu")
        
        # 检查是否已保存凭据
        saved_user_id = config.get("user_id", "")
        saved_api_key = config.get("api_key", "")
        
        if saved_user_id and saved_api_key:
            if UIUtils.ask_use_saved_credentials(f"用户ID: {saved_user_id}"):
                return saved_user_id, saved_api_key
        
        # 获取新的凭据
        print("\n请输入Intervals.icu凭据:")
        user_id = input("用户ID (例如: i244263): ").strip()
        api_key = input("API密钥: ").strip()
        
        if not user_id or not api_key:
            raise ValueError("用户ID和API密钥不能为空")
        
        # 询问是否保存凭据
        if UIUtils.ask_save_credentials():
            config["user_id"] = user_id
            config["api_key"] = api_key
            self.config_manager.save_platform_config("intervals_icu", config)
            self.debug_print("Intervals.icu凭据已保存")
        
        return user_id, api_key
    
    def test_connection(self, user_id: str = None, api_key: str = None) -> bool:
        """测试连接是否有效"""
        try:
            if not user_id or not api_key:
                user_id, api_key = self.get_credentials()
            
            headers = {
                'User-Agent': 'Strava-to-TrainingPeaks Sync Tool'
            }
            
            # 使用athlete ID为0表示当前用户
            url = f"{self.base_url}/athlete/0"
            
            self.debug_print(f"测试连接到: {url}")
            self.debug_print(f"使用Basic认证: API_KEY:{api_key[:10]}...")
            response = requests.get(url, headers=headers, auth=('API_KEY', api_key), timeout=10)
            
            self.debug_print(f"连接测试响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                athlete_data = response.json()
                print(f"Intervals.icu连接成功! 用户: {athlete_data.get('name', 'Unknown')}")
                return True
            else:
                print(f"Intervals.icu连接失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.debug_print(f"连接测试异常: {e}")
            print(f"Intervals.icu连接测试失败: {e}")
            return False
    
    def is_supported_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats
    
    def upload_activity(self, file_path: str, 
                       name: str = None, 
                       description: str = None,
                       external_id: str = None) -> Dict:
        """上传活动文件到Intervals.icu
        
        Args:
            file_path: 文件路径
            name: 活动名称（可选）
            description: 活动描述（可选）
            external_id: 外部ID（可选，用于关联到其他平台）
        
        Returns:
            上传结果字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not self.is_supported_format(file_path):
            raise ValueError(f"不支持的文件格式。支持的格式: {', '.join(self.supported_formats)}")
        
        # 获取凭据
        user_id, api_key = self.get_credentials()
        
        # 准备上传
        print(f"正在上传文件到Intervals.icu: {os.path.basename(file_path)}")
        
        # 构建URL参数
        url = f"{self.base_url}/athlete/0/activities"
        params = {}
        
        if name:
            params['name'] = name
        if description:
            params['description'] = description
        if external_id:
            params['external_id'] = external_id
        
        # 准备请求头 - 使用Basic认证
        headers = {
            'User-Agent': 'Strava-to-TrainingPeaks Sync Tool'
        }
        
        # 准备文件上传
        files = {
            'file': (os.path.basename(file_path), open(file_path, 'rb'))
        }
        
        try:
            self.debug_print(f"上传URL: {url}")
            self.debug_print(f"参数: {params}")
            self.debug_print(f"文件大小: {os.path.getsize(file_path)} bytes")
            
            # 发送上传请求 - 使用Basic认证
            response = requests.post(
                url,
                params=params,
                files=files,
                headers=headers,
                auth=('API_KEY', api_key),  # Basic认证：API_KEY作为用户名，API密钥作为密码
                timeout=60
            )
            
            self.debug_print(f"上传响应状态码: {response.status_code}")
            self.debug_print(f"响应头: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    activity_id = result.get('id', 'Unknown')
                    activity_name = result.get('name', name or os.path.basename(file_path))
                    
                    print(f"文件上传成功!")
                    print(f"活动ID: {activity_id}")
                    print(f"活动名称: {activity_name}")
                    print(f"查看活动: https://intervals.icu/activities/{activity_id}")
                    
                    return {
                        'success': True,
                        'activity_id': activity_id,
                        'name': activity_name,
                        'url': f"https://intervals.icu/activities/{activity_id}",
                        'response': result
                    }
                except Exception as e:
                    self.debug_print(f"解析响应JSON失败: {e}")
                    # 即使JSON解析失败，如果状态码是成功的，仍然认为上传成功
                    print("文件上传成功!")
                    return {
                        'success': True,
                        'activity_id': 'Unknown',
                        'name': name or os.path.basename(file_path),
                        'response': response.text
                    }
            else:
                error_msg = f"上传失败 - 状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f" - 错误: {error_data['error']}"
                    elif 'message' in error_data:
                        error_msg += f" - 消息: {error_data['message']}"
                except:
                    error_msg += f" - 响应: {response.text[:200]}"
                
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'response': response.text
                }
        
        except requests.exceptions.Timeout:
            error_msg = "上传超时，请检查网络连接"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"上传异常: {e}"
            print(error_msg)
            self.debug_print(f"详细异常信息: {e}")
            return {
                'success': False,
                'error': error_msg
            }
        finally:
            # 确保文件被关闭
            if 'files' in locals():
                for file_obj in files.values():
                    if hasattr(file_obj[1], 'close'):
                        file_obj[1].close()
    
    def upload_file(self, file_path: str) -> bool:
        """简化的上传接口，用于兼容其他客户端"""
        try:
            # 从文件名推断活动名称
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            result = self.upload_activity(
                file_path=file_path,
                name=base_name,
                description=f"通过同步工具上传于 {os.path.basename(file_path)}"
            )
            
            if result['success']:
                self.debug_print("Intervals.icu上传成功")
                return True
            else:
                self.debug_print(f"Intervals.icu上传失败: {result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"上传文件到Intervals.icu失败: {e}")
            self.debug_print(f"Intervals.icu上传异常: {e}")
            return False
    
    def get_activities(self, limit: int = 30, 
                      oldest: str = None, 
                      newest: str = None) -> list:
        """获取活动列表
        
        Args:
            limit: 返回活动数量限制
            oldest: 最早日期 (YYYY-MM-DD)
            newest: 最晚日期 (YYYY-MM-DD)
        
        Returns:
            活动列表
        """
        try:
            user_id, api_key = self.get_credentials()
            
            headers = {
                'User-Agent': 'Strava-to-TrainingPeaks Sync Tool'
            }
            
            # 如果没有指定oldest，默认为30天前
            if not oldest:
                from datetime import datetime, timedelta
                oldest_date = datetime.now() - timedelta(days=30)
                oldest = oldest_date.strftime('%Y-%m-%d')
            
            params = {
                'limit': limit,
                'oldest': oldest
            }
            
            if newest:
                params['newest'] = newest
            
            url = f"{self.base_url}/athlete/0/activities"
            
            self.debug_print(f"获取活动列表: {url}")
            self.debug_print(f"参数: {params}")
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                auth=('API_KEY', api_key),
                timeout=30
            )
            
            self.debug_print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                activities = response.json()
                print(f"成功获取{len(activities)}个活动")
                return activities
            else:
                print(f"获取活动列表失败: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.debug_print(f"获取活动列表异常: {e}")
            print(f"获取活动列表失败: {e}")
            return []
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        config = self.config_manager.get_platform_config("intervals_icu")
        return bool(config.get("user_id") and config.get("api_key")) 