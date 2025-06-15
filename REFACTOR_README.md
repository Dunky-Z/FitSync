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

---

# 双向同步功能（第一阶段）

## 功能概述

第一阶段实现了 **Strava ↔ Garmin Connect** 的双向自动同步功能，包括：

- 智能活动匹配和去重
- 增量同步，只处理新活动
- API限制管理
- 本地缓存优化
- 完整的同步状态跟踪

## 新增模块

### 双向同步核心模块

```
src/
├── main_sync.py              # 双向同步主程序
├── bidirectional_sync.py     # 双向同步核心逻辑
├── sync_manager.py           # 同步状态管理
├── activity_matcher.py       # 活动匹配算法
├── garmin_sync_client.py     # Garmin同步客户端
├── test_sync.py              # 双向同步测试脚本
└── sync_database.json        # 同步数据库（自动生成）
```

### SyncManager (sync_manager.py)
- **活动指纹生成**: 基于时间、运动类型、距离、时长生成唯一标识
- **同步记录管理**: 跟踪所有活动的同步状态
- **API限制监控**: 实时监控Strava API调用次数
- **缓存管理**: 本地文件缓存和清理
- **时间窗口管理**: 支持首次同步和增量同步

### ActivityMatcher (activity_matcher.py)
- **多维度匹配**: 时间、运动类型、距离、时长的智能匹配
- **可配置阈值**: 支持自定义匹配容差
- **置信度评分**: 0.0-1.0的匹配置信度
- **运动类型标准化**: 统一不同平台的运动类型命名

### BidirectionalSync (bidirectional_sync.py)
- **双向同步协调**: 管理Strava ↔ Garmin的双向数据流
- **批量处理**: 支持分批处理大量活动
- **错误恢复**: 完善的错误处理和重试机制
- **进度跟踪**: 实时显示同步进度和结果

## 使用方式

### 交互模式
```bash
cd src
python main_sync.py
```

选择操作：
- **开始双向同步**: 执行完整的双向同步
- **配置同步规则**: 设置启用/禁用特定同步方向
- **查看同步状态**: 显示详细的同步统计信息
- **清理缓存文件**: 清理过期的活动文件缓存

### 自动模式
```bash
# 完整双向同步
python main_sync.py --auto

# 只同步 Strava -> Garmin
python main_sync.py --auto --directions strava_to_garmin

# 只同步 Garmin -> Strava  
python main_sync.py --auto --directions garmin_to_strava

# 指定批处理大小
python main_sync.py --auto --batch-size 20

# 启用调试模式
python main_sync.py --debug
```

## 核心特性

### 1. 智能活动匹配

**匹配算法**:
- 时间匹配（权重40%）：5分钟容差
- 运动类型匹配（权重20%）：支持类型映射
- 距离匹配（权重20%）：5%容差
- 时长匹配（权重20%）：10%容差

**示例**:
```python
# 这两个活动会被识别为同一活动
activity1 = ActivityMetadata(
    name="晨跑",
    sport_type="running", 
    start_time="2024-01-01T06:00:00Z",
    distance=5000.0,
    duration=1800
)

activity2 = ActivityMetadata(
    name="Morning Run",
    sport_type="run",
    start_time="2024-01-01T06:02:00Z",  # 2分钟差异
    distance=5020.0,  # 20米差异 
    duration=1810     # 10秒差异
)
```

### 2. 增量同步策略

**首次同步**: 只同步最近30天的活动
**增量同步**: 从上次同步时间开始，1小时重叠避免遗漏

```python
# 时间窗口示例
if not last_sync:
    start_time = now - timedelta(days=30)  # 首次同步
else:
    start_time = last_sync - timedelta(hours=1)  # 增量同步
```

### 3. API限制管理

**Strava限制**:
- 每日200次调用（保留20次余量）
- 每15分钟100次调用（保留10次余量）

**智能调度**:
- 实时监控API调用次数
- 达到限制时自动停止同步
- 显示剩余调用次数

### 4. 本地缓存系统

**缓存结构**:
```
activity_cache/
├── abc123def456.fit    # 活动文件缓存
├── def789ghi012.tcx
└── ...
```

**缓存策略**:
- 基于活动指纹的文件命名
- 自动检测已缓存文件，避免重复下载
- 定期清理过期缓存（默认30天）

### 5. 同步数据库

**数据结构**:
```json
{
  "sync_records": {
    "activity_fingerprint": {
      "platforms": {
        "strava": "12345678",
        "garmin": "98765432"
      },
      "metadata": {
        "name": "晨跑",
        "sport_type": "running",
        "start_time": "2024-01-01T06:00:00Z",
        "distance": 5000,
        "duration": 1800
      },
      "files": {
        "fit": "activity_cache/abc123def456.fit"
      },
      "sync_status": {
        "strava_to_garmin": "synced",
        "garmin_to_strava": "pending"
      }
    }
  },
  "sync_config": {
    "last_sync": {
      "strava": "2024-01-01T12:00:00Z",
      "garmin": "2024-01-01T11:30:00Z"
    },
    "sync_rules": {
      "strava_to_garmin": true,
      "garmin_to_strava": true
    }
  }
}
```

## 测试功能

### 运行测试
```bash
cd src

# 运行所有测试
python test_sync.py

# 运行特定测试
python test_sync.py --test metadata
python test_sync.py --test sync_manager
python test_sync.py --test matcher
python test_sync.py --test strava
python test_sync.py --test garmin
python test_sync.py --test bidirectional
```

### 测试覆盖
- 活动元数据创建和转换
- 同步管理器功能
- 活动匹配算法
- Strava客户端功能
- Garmin客户端功能
- 双向同步核心逻辑

## 配置要求

### Strava配置
```json
{
  "strava": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "refresh_token": "your_refresh_token",
    "access_token": "",
    "cookie": "your_browser_cookie"
  }
}
```

### Garmin配置
```json
{
  "garmin": {
    "username": "your_username", 
    "password": "your_password",
    "auth_domain": "GLOBAL"
  }
}
```

## 限制和注意事项

### 当前限制
1. **Garmin -> Strava**: 由于Strava API限制，暂不支持上传到Strava
2. **文件格式**: 主要支持FIT格式，TCX和GPX支持有限
3. **活动类型**: 主要支持跑步、骑行、游泳等常见运动

### 使用建议
1. **首次同步**: 建议在API限制较少的时段进行
2. **定期同步**: 建议每日或每周定期运行增量同步
3. **监控限制**: 注意Strava API调用次数，避免超限

## 故障排除

### 常见问题

1. **同步数据库损坏**
   ```bash
   # 删除数据库重新开始
   rm sync_database.json
   ```

2. **缓存文件过多**
   ```bash
   # 清理缓存
   python main_sync.py
   # 选择"清理缓存文件"
   ```

3. **API限制达到**
   ```bash
   # 查看API状态
   python main_sync.py
   # 选择"查看同步状态"
   ```

### 调试模式
```bash
# 启用详细调试信息
python main_sync.py --debug
```

## 第二阶段计划

1. **IGPSport双向同步**: 扩展支持IGPSport平台
2. **Strava上传支持**: 研究Strava上传API或网页端自动化
3. **高级匹配算法**: 基于GPS轨迹的精确匹配
4. **定时同步**: 支持cron任务和后台运行
5. **GUI界面**: 提供图形化用户界面 