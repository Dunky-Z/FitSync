import re
import os
import time
import logging
import json
import uuid
import base64
import oss2
import argparse

from typing import Tuple

import pandas as pd
import questionary
import requests

from tqdm import tqdm
from dotenv import load_dotenv
from defusedxml.minidom import parseString
from tcxreader.tcxreader import TCXReader


load_dotenv()
logger = logging.getLogger()
DEBUG = False  # 全局调试标志

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('logs.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def debug_print(message: str) -> None:
    """只在调试模式下打印信息"""
    if DEBUG:
        print(message)


def main():
    global DEBUG
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Strava到IGPSport文件上传工具')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细信息')
    args = parser.parse_args()
    
    DEBUG = args.debug
    
    if DEBUG:
        print("🐛 调试模式已启用")
    
    file_location = ask_file_location()

    if file_location == "Download":
        activity_id = ask_activity_id()
        logger.info("Selected activity ID: %s", activity_id)
        print("正在从Strava下载文件...")
        existing_file = download_tcx_file(activity_id)

        # 如果返回了现有文件路径，直接使用
        if existing_file:
            file_path = existing_file
            debug_print(f"Using existing file: {file_path}")
        else:
            time.sleep(3)
            file_path = get_latest_download()
            debug_print(f"Automatically detected downloaded file path: {file_path}")
    else:
        file_path = ask_file_path(file_location)

    if file_path:
        print("正在验证文件...")
        validate_file(file_path)
        
        # 上传到IGPSport
        print("正在上传到IGPSport...")
        upload_to_igpsport(file_path)
    else:
        logger.error("No file path provided")
        raise ValueError("No file path provided")

    print("✅ 处理完成！")


def ask_file_location() -> str:
    return questionary.select(
        "Do you want to download the file from Strava or provide the file path?",
        choices=["Download", "Provide path"]
    ).ask()


def ask_activity_id() -> str:
    activity_id = questionary.text(
        "Enter the Strava activity ID you want to upload to IGPSport:"
    ).ask()
    
    if activity_id is None:
        logger.error("Operation cancelled by user.")
        raise SystemExit("Operation cancelled by user.")
    
    return re.sub(r"\D", "", activity_id)


def download_tcx_file(activity_id: str) -> str:
    # 统一使用export_original下载fit文件，不区分运动类型
    url = f"https://www.strava.com/activities/{activity_id}/export_original"
    
    debug_print(f"\n开始下载活动 {activity_id} 的原始文件...")
    debug_print(f"下载URL: {url}")
    
    # 检查是否已存在相同活动ID的文件
    existing_file = check_existing_activity_file(activity_id)
    if existing_file:
        print(f"✅ 发现已存在的活动文件: {os.path.basename(existing_file)}")
        confirm_use = questionary.confirm(
            f"是否使用已存在的文件: {os.path.basename(existing_file)}?",
            default=True
        ).ask()
        
        if confirm_use:
            print("🔄 跳过下载，使用已存在的文件")
            return existing_file
        else:
            print("⏬ 继续下载新文件...")
    
    # 直接使用Cookie认证下载
    download_with_cookie(url, activity_id)
    return ""


def check_existing_activity_file(activity_id: str) -> str:
    """检查Downloads文件夹中是否已存在相同活动ID的文件"""
    download_folder = os.path.expanduser("~/Downloads")
    
    try:
        files = os.listdir(download_folder)
    except FileNotFoundError:
        return ""
    
    # 查找匹配的活动文件，支持更多格式
    for file in files:
        if f"activity_{activity_id}" in file and file.endswith(('.tcx', '.gpx', '.fit')):
            full_path = os.path.join(download_folder, file)
            # 验证文件是否有效
            try:
                if file.endswith('.fit'):
                    # FIT文件是二进制格式，检查文件大小
                    if os.path.getsize(full_path) > 0:
                        debug_print(f"🔍 找到FIT文件: {file}")
                        return full_path
                else:
                    # XML格式文件
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content and '<?xml' in content:
                            debug_print(f"🔍 找到XML文件: {file}")
                            return full_path
            except Exception as e:
                debug_print(f"⚠️ 文件检查失败 {file}: {e}")
                continue
    
    return ""


def get_saved_cookie() -> str:
    """从文件中读取保存的Strava Cookie"""
    cookie_file = ".strava_cookie"
    try:
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
                if cookie:
                    return cookie
    except Exception as e:
        logger.warning(f"读取Cookie文件失败: {e}")
    return ""


def save_cookie(cookie: str) -> None:
    """将Strava Cookie保存到文件"""
    cookie_file = ".strava_cookie"
    try:
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookie.strip())
        debug_print("✅ Strava Cookie已保存，下次运行时将自动使用")
    except Exception as e:
        logger.warning(f"保存Cookie文件失败: {e}")


def get_saved_igpsport_cookie() -> str:
    """从文件中读取保存的IGPSport Cookie"""
    cookie_file = ".igpsport_cookie"
    try:
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
                if cookie:
                    return cookie
    except Exception as e:
        logger.warning(f"读取IGPSport Cookie文件失败: {e}")
    return ""


def save_igpsport_cookie(cookie: str) -> None:
    """将IGPSport Cookie保存到文件"""
    cookie_file = ".igpsport_cookie"
    try:
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookie.strip())
        debug_print("✅ IGPSport Cookie已保存，下次运行时将自动使用")
    except Exception as e:
        logger.warning(f"保存IGPSport Cookie文件失败: {e}")


def download_with_cookie(url: str, activity_id: str) -> None:
    """使用Cookie进行认证下载"""
    
    # 首先尝试使用保存的Cookie
    saved_cookie = get_saved_cookie()
    
    if saved_cookie:
        debug_print("使用已保存的Cookie进行下载...")
        success = try_download_with_cookie(url, activity_id, saved_cookie)
        if success:
            return
        else:
            debug_print("保存的Cookie可能已过期，需要更新Cookie")
    
    # 如果没有保存的Cookie或Cookie已过期，提示用户输入新的Cookie
    print("\n要获取Strava Cookie，请按以下步骤操作：")
    print("1. 在浏览器中打开 https://www.strava.com 并登录")
    print("2. 按F12打开开发者工具")
    print("3. 转到 Network(网络) 标签")
    print("4. 刷新页面")
    print("5. 找到任意一个请求，在Request Headers中找到Cookie")
    print("6. 复制完整的Cookie值")
    
    cookie_value = questionary.text(
        "\n请粘贴您的Strava Cookie值:",
        multiline=True
    ).ask()
    
    if not cookie_value:
        print("未提供Cookie，无法下载文件")
        raise ValueError("Cookie为空，无法继续")
    
    # 尝试使用新Cookie下载
    success = try_download_with_cookie(url, activity_id, cookie_value)
    
    if success:
        # 保存Cookie供下次使用
        save_cookie(cookie_value)
    else:
        print("❌ Cookie无效或活动不可访问")
        raise ValueError("下载失败")


def try_download_with_cookie(url: str, activity_id: str, cookie: str) -> bool:
    """尝试使用Cookie下载文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': cookie.strip(),
            'Referer': f'https://www.strava.com/activities/{activity_id}'
        }
        
        debug_print(f"🌐 发送下载请求...")
        response = requests.get(url, headers=headers, timeout=30)
        
        debug_print(f"📡 响应状态码: {response.status_code}")
        debug_print(f"📄 Content-Type: {response.headers.get('content-type', 'Unknown')}")
        debug_print(f"📊 Content-Length: {response.headers.get('content-length', 'Unknown')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            # 判断文件类型
            if 'application/octet-stream' in content_type or 'application/fit' in content_type:
                # FIT文件（二进制）
                filename = f"activity_{activity_id}.fit"
                download_path = os.path.join(os.path.expanduser("~/Downloads"), filename)
                
                with open(download_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ FIT文件已成功下载: {filename}")
                debug_print(f"📁 文件大小: {len(response.content)} bytes")
                return True
                
            elif 'xml' in content_type or '<?xml' in response.text:
                # XML格式文件（TCX/GPX）
                content = response.text
                if 'TrainingCenterDatabase' in content:
                    filename = f"activity_{activity_id}.tcx"
                elif 'gpx' in content.lower():
                    filename = f"activity_{activity_id}.gpx"
                else:
                    filename = f"activity_{activity_id}.xml"
                    
                download_path = os.path.join(os.path.expanduser("~/Downloads"), filename)
                
                with open(download_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ XML文件已成功下载: {filename}")
                debug_print(f"📁 文件大小: {len(content)} characters")
                return True
            else:
                debug_print(f"❌ 未知的文件格式，Content-Type: {content_type}")
                debug_print(f"📄 响应内容开头: {response.text[:200] if response.text else response.content[:200]}")
                return False
        else:
            debug_print(f"❌ 下载失败 (状态码: {response.status_code})")
            return False
            
    except Exception as e:
        debug_print(f"❌ 下载出错: {e}")
        return False


def get_latest_download() -> str:
    download_folder = os.path.expanduser("~/Downloads")
    try:
        files = os.listdir(download_folder)
    except FileNotFoundError:
        logger.warning("未找到Downloads文件夹")
        files = []
    
    # 查找活动文件
    activity_files = [f for f in files if f.endswith(('.tcx', '.gpx', '.fit'))]
    paths = [os.path.join(download_folder, f) for f in activity_files]

    if paths:
        latest_file = max(paths, key=os.path.getmtime)
        print(f"找到最新下载的文件: {latest_file}")
        
        # 确认这是正确的文件
        confirm = questionary.confirm(
            f"是否使用此文件: {os.path.basename(latest_file)}?",
            default=True
        ).ask()
        
        if confirm:
            return latest_file
        else:
            return ask_file_path("Download")
    else:
        logger.warning("在Downloads文件夹中未找到活动文件")
        print("在Downloads文件夹中未找到活动文件")
        return ask_file_path("Download")


def ask_file_path(file_location: str) -> str:
    if file_location == "Provide path":
        question = "Enter the path to the activity file:"
    else:
        question = "Check if the file was downloaded and validate the file:"

    return questionary.path(
        question,
        validate=validation,
        only_directories=False
    ).ask()


def validation(path: str) -> bool:
    return os.path.isfile(path)


def validate_file(file_path: str) -> None:
    """验证文件格式"""
    debug_print(f"🔍 验证文件: {file_path}")
    
    if file_path.endswith('.fit'):
        # FIT文件验证
        try:
            file_size = os.path.getsize(file_path)
            debug_print(f"📁 FIT文件大小: {file_size} bytes")
            
            if file_size == 0:
                logger.error("The FIT file is empty.")
                raise ValueError("The FIT file is empty.")
            
            # 简单的FIT文件头验证
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if len(header) >= 4:
                    debug_print(f"📄 FIT文件头: {header}")
                else:
                    logger.error("Invalid FIT file header.")
                    raise ValueError("Invalid FIT file header.")
            
            logger.info("FIT file validation passed.")
            
        except Exception as e:
            logger.error(f"FIT file validation failed: {e}")
            raise ValueError(f"FIT file validation failed: {e}")
    else:
        # XML文件验证
        with open(file_path, "r", encoding='utf-8') as file:
            content = file.read()
        
        debug_print(f"📁 XML文件大小: {len(content)} characters")
        
        if not content:
            logger.error("The file is empty.")
            raise ValueError("The file is empty.")
        
        if '<?xml' not in content:
            logger.error("Invalid XML file format.")
            raise ValueError("Invalid XML file format.")
        
        logger.info("XML file validation passed.")


def convert_to_gpx(file_path: str) -> str:
    """将TCX文件转换为GPX格式（如果需要）"""
    if file_path.endswith('.gpx'):
        return file_path
    
    # 如果是TCX文件，读取并转换为GPX格式
    if file_path.endswith('.tcx'):
        try:
            tcx_reader = TCXReader()
            data = tcx_reader.read(file_path)
            
            # 创建GPX文件路径
            gpx_path = file_path.replace('.tcx', '.gpx')
            
            # 简单的TCX到GPX转换
            convert_tcx_to_gpx(file_path, gpx_path)
            
            logger.info(f"Converted TCX to GPX: {gpx_path}")
            return gpx_path
        except Exception as e:
            logger.warning(f"TCX conversion failed, using original file: {e}")
            return file_path
    
    return file_path


def convert_tcx_to_gpx(tcx_path: str, gpx_path: str) -> None:
    """简单的TCX到GPX转换"""
    with open(tcx_path, 'r', encoding='utf-8') as f:
        tcx_content = f.read()
    
    # 基本的格式转换（简化版）
    gpx_content = tcx_content.replace(
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">',
        '<gpx version="1.1" creator="Strava-to-IGPSport" xmlns="http://www.topografix.com/GPX/1/1">'
    )
    gpx_content = gpx_content.replace('</TrainingCenterDatabase>', '</gpx>')
    
    with open(gpx_path, 'w', encoding='utf-8') as f:
        f.write(gpx_content)


def get_igpsport_credentials() -> tuple:
    """获取IGPSport登录凭据"""
    print("\n请输入IGPSport登录信息:")
    username = questionary.text("IGPSport用户名/邮箱:").ask()
    password = questionary.password("IGPSport密码:").ask()
    
    if not username or not password:
        raise ValueError("用户名和密码不能为空")
    
    return username, password


def login_igpsport(username: str, password: str) -> str:
    """登录IGPSport并获取token"""
    print("正在登录IGPSport...")
    
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
        
        debug_print(f"登录响应状态码: {response.status_code}")
        
        if response.status_code in [200, 302]:
            # 提取登录token
            for cookie in session.cookies:
                if cookie.name == 'loginToken':
                    print("✅ IGPSport登录成功")
                    # 保存cookie供下次使用
                    save_igpsport_cookie(cookie.value)
                    return cookie.value
            
            # 如果没有找到cookie，尝试从响应中解析
            try:
                if response.text:
                    result = response.json()
                    if 'token' in result:
                        print("✅ IGPSport登录成功")
                        save_igpsport_cookie(result['token'])
                        return result['token']
                    elif 'data' in result and 'token' in result['data']:
                        print("✅ IGPSport登录成功")
                        save_igpsport_cookie(result['data']['token'])
                        return result['data']['token']
            except Exception as e:
                debug_print(f"解析响应失败: {e}")
        
        debug_print(f"登录失败，响应内容: {response.text[:200] if response.text else 'No content'}")
        
    except Exception as e:
        debug_print(f"登录请求异常: {e}")
    
    # 如果还是失败，提供一个选项让用户手动输入token
    manual_token = questionary.confirm(
        "自动登录失败，是否要手动输入IGPSport的loginToken?",
        default=False
    ).ask()

    if manual_token:
        print("\n要获取IGPSport Token，请按以下步骤操作：")
        print("1. 在浏览器中打开 https://my.igpsport.com 并登录")
        print("2. 按F12打开开发者工具")
        print("3. 转到 Application/Storage > Cookies")
        print("4. 找到 loginToken 的值")
        
        token = questionary.text("请输入loginToken值:").ask()
        if token:
            print("✅ 使用手动输入的Token")
            save_igpsport_cookie(token.strip())
            return token.strip()
    
    raise ValueError("IGPSport登录失败，请检查用户名和密码")


def test_igpsport_cookie(cookie: str) -> bool:
    """测试IGPSport cookie是否有效"""
    try:
        url = "https://prod.zh.igpsport.com/service/mobile/api/AliyunService/GetOssTokenForApp"
        headers = {
            'Authorization': f'Bearer {cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False


def get_oss_token(login_token: str) -> dict:
    """获取阿里云OSS临时凭证"""
    debug_print("获取OSS上传凭证...")
    
    url = "https://prod.zh.igpsport.com/service/mobile/api/AliyunService/GetOssTokenForApp"
    headers = {
        'Authorization': f'Bearer {login_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    debug_print(f"🌐 请求URL: {url}")
    debug_print(f"🔑 Authorization: Bearer {login_token[:20]}...")
    
    response = requests.get(url, headers=headers)
    
    debug_print(f"📡 响应状态码: {response.status_code}")
    debug_print(f"📄 响应头: {dict(response.headers)}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            debug_print(f"📊 完整响应数据: {data}")
            
            if 'data' in data:
                oss_data = data['data']
                debug_print("✅ OSS凭证获取成功")
                debug_print(f"🔑 AccessKeyId: {oss_data.get('accessKeyId', 'Not found')}")
                debug_print(f"🔑 SecurityToken前50字符: {oss_data.get('securityToken', 'Not found')[:50]}...")
                return oss_data
            else:
                debug_print("❌ 响应中没有找到data字段")
                debug_print(f"📄 完整响应: {data}")
        except Exception as e:
            debug_print(f"❌ JSON解析失败: {e}")
            debug_print(f"📄 响应文本: {response.text}")
    else:
        debug_print("❌ 获取OSS凭证失败")
        debug_print(f"📄 响应文本: {response.text}")
    
    raise ValueError("获取OSS凭证失败")


def upload_to_oss(file_path: str, oss_credentials: dict) -> str:
    """上传文件到阿里云OSS"""
    debug_print("正在上传文件到OSS...")
    
    # 生成唯一的OSS文件名
    oss_name = f"1456042-{str(uuid.uuid4())}"
    
    debug_print(f"📁 本地文件: {file_path}")
    debug_print(f"☁️ OSS文件名: {oss_name}")
    debug_print(f"📊 文件大小: {os.path.getsize(file_path)} bytes")
    
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
        
        debug_print(f"🌐 OSS Endpoint: {oss_credentials['endpoint']}")
        debug_print(f"🪣 OSS Bucket: {oss_credentials['bucketName']}")
        debug_print(f"🔑 使用AccessKey: {oss_credentials['accessKeyId']}")
        
        # 上传文件
        debug_print("📤 开始真正的OSS上传...")
        result = bucket.put_object_from_file(oss_name, file_path)
        
        debug_print(f"📡 OSS上传结果状态: {result.status}")
        debug_print(f"🆔 请求ID: {result.request_id}")
        debug_print(f"🔗 ETag: {result.etag}")
        
        if result.status == 200:
            print("✅ 文件上传成功")
            
            # 验证文件是否真的上传成功
            if bucket.object_exists(oss_name):
                debug_print("✅ 文件在OSS中确认存在")
                
                # 获取文件信息
                meta = bucket.head_object(oss_name)
                debug_print(f"📊 OSS中文件大小: {meta.content_length} bytes")
                debug_print(f"📅 上传时间: {meta.last_modified}")
            else:
                debug_print("❌ 警告：文件在OSS中不存在")
        else:
            debug_print(f"❌ OSS上传失败，状态码: {result.status}")
            raise Exception(f"OSS上传失败，状态码: {result.status}")
        
        return oss_name
        
    except Exception as e:
        logger.error(f"OSS上传失败: {e}")
        debug_print(f"❌ OSS上传异常: {e}")
        debug_print("📋 错误详情:")
        debug_print(f"  - AccessKeyId: {oss_credentials.get('accessKeyId', 'Missing')}")
        debug_print(f"  - Endpoint: {oss_credentials.get('endpoint', 'Missing')}")
        debug_print(f"  - BucketName: {oss_credentials.get('bucketName', 'Missing')}")
        raise


def notify_igpsport(login_token: str, file_name: str, oss_name: str) -> None:
    """通知IGPSport服务器文件已上传"""
    print("通知IGPSport服务器...")
    
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
    
    print(f"🌐 通知URL: {url}")
    print(f"📄 发送数据: {data}")
    print(f"🔑 使用Token: {login_token[:20]}...")
    
    response = requests.post(url, json=data, headers=headers)
    
    print(f"📡 通知响应状态码: {response.status_code}")
    print(f"📄 响应头: {dict(response.headers)}")
    print(f"📊 响应内容: {response.text}")
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"📊 解析后的响应: {result}")
            print("✅ IGPSport上传通知成功")
        except:
            print("✅ IGPSport上传通知成功（无JSON响应）")
    else:
        print(f"⚠️ IGPSport通知失败 (状态码: {response.status_code})")
        print(f"❌ 可能的错误原因：")
        print(f"   - Token已过期")
        print(f"   - OSS文件名无效")
        print(f"   - 服务器内部错误")


def upload_to_igpsport(file_path: str) -> None:
    """完整的IGPSport上传流程"""
    try:
        # 1. 首先尝试使用保存的cookie
        saved_cookie = get_saved_igpsport_cookie()
        login_token = None
        
        if saved_cookie:
            print("使用已保存的IGPSport Cookie进行认证...")
            if test_igpsport_cookie(saved_cookie):
                print("✅ IGPSport Cookie有效，跳过登录")
                login_token = saved_cookie
            else:
                print("保存的IGPSport Cookie已过期，需要重新登录...")
        
        # 2. 如果没有有效的cookie，进行登录
        if not login_token:
            username, password = get_igpsport_credentials()
            login_token = login_igpsport(username, password)
        
        # 3. 获取OSS凭证
        oss_credentials = get_oss_token(login_token)
        
        # 4. 上传文件到OSS
        file_name = os.path.basename(file_path)
        oss_name = upload_to_oss(file_path, oss_credentials)
        
        # 5. 通知IGPSport
        notify_igpsport(login_token, file_name, oss_name)
        
        print(f"\n🎉 文件 {file_name} 已成功上传到IGPSport！")
        
    except Exception as e:
        logger.error(f"IGPSport上传失败: {e}")
        print(f"❌ 上传失败: {e}")
        raise


def indent_xml_file(file_path: str) -> None:
    try:
        with open(file_path, "r", encoding='utf-8') as xml_file:
            xml_content = xml_file.read()

        xml_dom = parseString(xml_content)

        with open(file_path, "w", encoding='utf-8') as xml_file:
            xml_file.write(xml_dom.toprettyxml(indent="  "))
    except Exception:
        logger.warning(
            "Failed to indent the XML file. The file will be saved without indentation."
        )


if __name__ == "__main__":
    main()
