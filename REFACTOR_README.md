# 项目重构说明

## 重构概述

本项目已完成重构，采用模块化架构，提高了代码的可维护性和可扩展性。重构后的代码更加清晰，易于添加新的平台支持。

## 新的项目结构

```
src/
├── main_refactored.py      # 重构后的主程序（推荐使用）
├── main.py                 # 原始主程序（保留兼容性）
├── config_manager.py       # 统一配置管理器
├── file_utils.py          # 文件处理工具类
├── ui_utils.py            # 用户界面交互工具类
├── strava_client.py       # Strava客户端
├── igpsport_client.py     # IGPSport客户端
├── garmin_client_wrapper.py # Garmin客户端包装器
├── platform_manager.py    # 平台管理器
├── garmin_client.py       # 原始Garmin客户端（依赖）
├── garmin_url_dict.py     # Garmin API配置（依赖）
└── test_garmin_upload.py  # Garmin功能测试
```

## 模块职责

### ConfigManager (config_manager.py)
- 统一管理所有平台的配置
- 自动迁移旧配置文件
- 提供平台特定的配置读写接口

### FileUtils (file_utils.py)
- 文件验证和格式转换
- 文件名清理和规范化
- 活动文件检测和管理

### UIUtils (ui_utils.py)
- 所有用户交互功能
- 统一的提示和确认界面
- 活动选择和格式化显示

### StravaClient (strava_client.py)
- Strava API交互
- 活动下载和认证
- Token刷新和管理

### IGPSportClient (igpsport_client.py)
- IGPSport登录和认证
- OSS文件上传
- 服务器通知处理

### GarminClientWrapper (garmin_client_wrapper.py)
- 封装现有的Garmin客户端
- 提供统一的上传接口
- 错误处理和重试机制

### PlatformManager (platform_manager.py)
- 统一管理所有平台操作
- 批量上传处理
- 结果汇总和显示

## 使用方式

### 基本使用（推荐）
```bash
cd src
python main_refactored.py
```

### 调试模式
```bash
cd src
python main_refactored.py --debug
```

### 兼容性使用
```bash
cd src
python main.py
```

## 重构优势

### 1. 模块化设计
- 每个模块职责单一，易于理解和维护
- 模块间低耦合，高内聚
- 便于单元测试

### 2. 可扩展性
- 添加新平台只需实现对应的客户端类
- 在PlatformManager中注册即可
- 无需修改主程序逻辑

### 3. 配置管理
- 统一的配置文件格式
- 自动配置迁移
- 平台特定的配置隔离

### 4. 错误处理
- 统一的异常处理机制
- 详细的日志记录
- 用户友好的错误提示

### 5. 代码清洁
- 移除所有emoji字符
- 统一的代码风格
- 清晰的函数命名

## 添加新平台支持

### 步骤 1: 创建平台客户端
```python
# src/new_platform_client.py
class NewPlatformClient:
    def __init__(self, config_manager: ConfigManager, debug: bool = False):
        self.config_manager = config_manager
        self.debug = debug
    
    def upload_file(self, file_path: str) -> None:
        # 实现上传逻辑
        pass
```

### 步骤 2: 更新配置管理器
在`config_manager.py`的默认配置中添加新平台：
```python
"new_platform": {
    "username": "",
    "password": "",
    # 其他配置项
}
```

### 步骤 3: 注册到平台管理器
在`platform_manager.py`中添加：
```python
from new_platform_client import NewPlatformClient

# 在__init__方法中
self.new_platform_client = NewPlatformClient(config_manager, debug)
self.platform_clients["new_platform"] = self.new_platform_client
self.platform_names["new_platform"] = "New Platform"
```

### 步骤 4: 更新UI选项
在`ui_utils.py`的`ask_upload_platforms`方法中添加新选项：
```python
choices=[
    {"name": "IGPSport", "value": "igpsport", "checked": False},
    {"name": "Garmin Connect", "value": "garmin", "checked": False},
    {"name": "New Platform", "value": "new_platform", "checked": False}
]
```

## 配置文件格式

重构后继续使用`.app_config.json`统一配置文件：

```json
{
  "strava": {
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",
    "refresh_token": "your_refresh_token_here",
    "access_token": "",
    "cookie": ""
  },
  "igpsport": {
    "login_token": "",
    "username": "",
    "password": ""
  },
  "garmin": {
    "username": "",
    "password": "",
    "auth_domain": "GLOBAL",
    "session_cookies": "",
    "oauth_token": "",
    "oauth_token_secret": ""
  },
  "general": {
    "debug_mode": false,
    "auto_save_credentials": true
  }
}
```

## 向后兼容性

- 保留原始的`main.py`文件，确保现有用户可以继续使用
- 自动迁移旧配置文件格式
- 保持相同的用户交互流程

## 测试

每个模块都可以独立测试：

```bash
# 测试Garmin功能
cd src
python test_garmin_upload.py

# 测试配置管理
python -c "from config_manager import ConfigManager; cm = ConfigManager(); print(cm.get_config())"
```

## 注意事项

1. **依赖管理**: 确保安装了所有必需的依赖包
2. **配置迁移**: 首次运行会自动迁移旧配置
3. **调试模式**: 使用`--debug`参数获取详细信息
4. **错误处理**: 查看`logs.log`文件获取详细错误信息

## 未来改进

1. 添加配置文件加密
2. 实现插件系统
3. 添加API限速处理
4. 支持批量文件处理
5. 添加GUI界面 